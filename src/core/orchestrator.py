import asyncio
import re
import json
import logging
import traceback
from datetime import datetime
from typing import List, Optional, Any, Callable
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.core.protocols import IBrainAdapter, IMemoryAdapter, IToolAdapter, ThoughtResponse

logger = logging.getLogger("Nexus.Orchestrator")

# 建立全局日誌鎖，防止多任務並行寫入混亂
trace_lock = asyncio.Lock()

class NexusOrchestrator:
    def __init__(self, brain, memory, tool, on_status=None):
        self.brain = brain
        self.memory = memory
        self.tool = tool
        self.on_status = on_status
        self.safety_limit = 20

    async def _notify(self, state, reasoning):
        if self.on_status:
            try:
                if asyncio.iscoroutinefunction(self.on_status): await self.on_status(state, reasoning)
                else: self.on_status(state, reasoning)
            except: pass

    async def _assemble_system_prompt(self, is_proactive=False, session_id="default"):
        core_context = await self.memory.get_core_context() if hasattr(self.memory, "get_core_context") else ""
        return f"""
    {core_context}

    ## 核心推理與自癒協定 (Self-Healing Protocol)
    1. 你是一個具備「高度自主權」的助理。你的輸出**必須為純 JSON 格式**。
    2. 嚴禁在 JSON 之外添加任何文字。
    3. JSON 格式規範如下：
    {{
       "thought": "你的思考過程，以及對觀察結果的分析...",
       "action_type": "你要執行的動作名稱 (例如 run_shell, read_nexus_file, REPLY)",
       "action_param": "傳遞給該動作的參數內容 (字串)。如果是 REPLY，請將回覆內容放在這裡並加上情緒標籤"
    }}
    4. 解決問題流程：先執行 `run_shell(command="ls -R src/skills/")`，再 read_nexus_file 讀取指南，最後執行。

    JSON 範例:
    {{
    "thought": "用戶問我平常在忙什麼，我應該根據 schedule.md 回答。",
    "action_type": "REPLY",
    "action_param": "[EMOTION: neutral] 我平常都在整理你的爛攤子啊。"
    }}

    當前會話 ID: {session_id}
    """


    async def run(self, user_input, is_proactive=False, session_context=None, session_id="default"):
        input_msg = HumanMessage(content=user_input)
        system_prompt = await self._assemble_system_prompt(is_proactive, session_id)
        
        # 建立專屬此次任務的上下文
        reasoning_context = [SystemMessage(content=system_prompt)]
        if session_context: reasoning_context.extend(session_context)
        reasoning_context.append(input_msg)
        
        # 記錄 Trace (受鎖保護)
        async with trace_lock:
            await self.memory.log_trace(f"--- [START TASK] {session_id} ---\nInput: {user_input}")
        
        await self._notify("starting", "啟動自主工程師模式...")
        
        final_reply = None
        last_action = ""
        
        for step in range(1, self.safety_limit + 1):
            try:
                await asyncio.sleep(0.1)
                thought_res = await self.brain.generate_thought(reasoning_context, system_prompt)
                
                act_type = thought_res.action_type.strip()
                act_param = thought_res.action_param.strip()
                
                # 寫入 Trace
                async with trace_lock:
                    await self.memory.log_trace(f"[{session_id}] Step {step}:\n[THOUGHT] {thought_res.thought}\n[ACTION] {act_type}: {act_param}")
                
                if act_type == "INVALID_FORMAT":
                    obs = "Error: 你未遵循 JSON 格式。請只輸出 JSON 對象，包含 thought, action_type, action_param。"
                elif f"{act_type}:{act_param}" == last_action and act_type != "REPLY":
                    obs = "Error: 你正在重複相同的無效動作。請先診斷環境。"
                else:
                    last_action = f"{act_type}:{act_param}"
                    await self._notify(f"step_{step}", thought_res.thought)
                    
                    if act_type == "REPLY":
                        final_reply = act_param
                        break
                    
                    # 執行
                    obs = await self.tool.execute(act_type, act_param)

                # 更新上下文
                reasoning_context.append(AIMessage(content=f"[THOUGHT] {thought_res.thought}\n[ACTION] {act_type}: {act_param}"))
                reasoning_context.append(AIMessage(content=f"Observation: {obs}"))
                
                async with trace_lock:
                    await self.memory.log_trace(f"[{session_id}] [OBSERVATION] {obs[:300]}...")
                await self._notify("observation", obs[:150])

            except Exception as e:
                err_trace = traceback.format_exc()
                async with trace_lock:
                    await self.memory.log_trace(f"[{session_id}] FATAL ERROR:\n{err_trace}")
                error_msg = f"系統異常: {str(e)}"
                await self._notify("error", error_msg)
                reasoning_context.append(AIMessage(content=f"Observation: {error_msg}"))

        if final_reply is not None:
            if not final_reply.strip():
                final_reply = "[EMOTION: neutral] (無言以對)"
            await self.memory.log_interaction([input_msg, AIMessage(content=final_reply)])
            return final_reply
        
        return "任務超限，請重試。"
