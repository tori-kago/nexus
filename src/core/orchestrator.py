import asyncio
import re
import json
import logging
from typing import List, Optional, Any, Callable
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.core.protocols import IBrainAdapter, IMemoryAdapter, IToolAdapter, ThoughtResponse

logger = logging.getLogger("Nexus.Orchestrator")

class NexusOrchestrator:
    def __init__(
        self, 
        brain: IBrainAdapter, 
        memory: IMemoryAdapter,
        tool: Optional[IToolAdapter] = None,
        on_status: Optional[Callable[[str, str], Any]] = None
    ):
        self.brain = brain
        self.memory = memory
        self.tool = tool
        self.on_status = on_status
        self.max_steps = 6
        self.compaction_threshold = 10

    async def _notify(self, state: str, reasoning: str):
        if self.on_status:
            try:
                if asyncio.iscoroutinefunction(self.on_status):
                    await self.on_status(state, reasoning)
                else: self.on_status(state, reasoning)
            except: pass

    async def _assemble_system_prompt(self, is_proactive: bool = False) -> str:
        if hasattr(self.memory, "get_core_context"):
            core_context = await self.memory.get_core_context()
        else:
            core_context = getattr(self.memory, "get_identity", lambda: "")()
            
        tools_info = self.tool.get_system_prompt_fragment() if self.tool else "目前沒有可用的外部工具。"
        
        prompt = f"""
{core_context}

## 核心運作規約 (Reasoning Protocol)
1. 你現在處於「自主思考循環」中。
2. 每一輪回覆中，你必須且只能輸出一個 [THOUGHT] 與一個 [ACTION]。
3. 動作格式嚴格遵循: [ACTION] 類型: 內容

可用 Action 類型:
   - REPLY: (回覆用戶)
   - SEARCH: (檢索記憶庫)
   - EXECUTE: (執行具體技能。格式: tool_name({{"param": "val"}}) )
   - REFLECT_USER: (紀錄用戶偏好)
   - THINK: (純推理)

{tools_info}
"""
        return prompt

    async def run(self, user_input: str, is_proactive: bool = False, session_context: List[Any] = None) -> Optional[str]:
        input_msg = HumanMessage(content=user_input)
        system_prompt = await self._assemble_system_prompt(is_proactive)
        
        context = [SystemMessage(content=system_prompt)]
        if session_context: context.extend(session_context)
        context.append(input_msg)
        
        await self._notify("starting", "核心調度器啟動...")
        
        final_reply = None
        last_action = "" # 用於偵測死循環
        
        for step in range(self.max_steps):
            await asyncio.sleep(0.1)
            thought_res: ThoughtResponse = await self.brain.generate_thought(context, system_prompt)
            
            # 偵測死循環：如果連續兩次動作一模一樣
            current_action = f"{thought_res.action_type}:{thought_res.action_param}"
            if current_action == last_action:
                obs = "Error: 你正在重複相同的動作。請嘗試更換參數或改用 REPLY 結束。"
            else:
                last_action = current_action
                await self._notify("thinking", thought_res.thought)
                
                # 動作執行邏輯
                if thought_res.action_type == "REPLY":
                    final_reply = thought_res.action_param
                    break
                elif thought_res.action_type == "SEARCH":
                    obs = await self.memory.search(thought_res.action_param)
                elif thought_res.action_type == "EXECUTE" and self.tool:
                    # 強化正則解析
                    match = re.search(r"(\w+)\s*\((.*)\)", thought_res.action_param, re.DOTALL)
                    if match:
                        t_name, t_params_str = match.group(1), match.group(2).strip()
                        try:
                            # 嘗試處理可能的 JSON 引號問題
                            t_params_str = t_params_str.replace("'", '"')
                            t_params = json.loads(t_params_str) if t_params_str else {}
                            obs = await self.tool.execute(t_name, t_params)
                        except Exception as e:
                            obs = f"Error parsing JSON: {str(e)}。請確保參數是正確的 JSON 格式。"
                    else:
                        obs = "Error: 無法解析 EXECUTE 格式。請使用 tool_name({\"param\": \"val\"})"
                else:
                    obs = f"Observation: 動作 '{thought_res.action_type}' 已確認。"
            
            # 更新上下文
            context.append(AIMessage(content=f"[THOUGHT] {thought_res.thought}\n[ACTION] {thought_res.action_type}: {thought_res.action_param}"))
            context.append(AIMessage(content=f"Observation: {obs}"))
            await self._notify("observation", obs[:100])

        if final_reply:
            await self.memory.log_interaction([input_msg, AIMessage(content=final_reply)])
            if session_context and len(session_context) >= self.compaction_threshold:
                asyncio.create_task(self.memory.digest_conversation(session_context, self.brain))
            return final_reply
        
        return "對不起，我現在思考得有點混亂，請再試一次。"
