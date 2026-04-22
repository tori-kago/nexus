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
1. 你是一個具備「高度自主權」的工程師助理。
2. 你的每一輪回覆必須嚴格包含 [THOUGHT] 與 [ACTION] 標籤。
3. 嚴禁使用內建知識回答關於時事或網頁內容。你必須先使用 `run_shell` 進行 ls, cat 或執行技能。
4. 解決問題流程：先 discover_skills 察看可用技能，再讀取對應目錄下的 SKILL.md，最後執行。

可用工具:
- run_shell(command): 執行終端指令。
- read_nexus_file(file_path): 讀取檔案內容。
- update_env_config: 更新配置。
- REPLY: (僅在任務完成後使用，包含情緒標籤)。
"""

    async def run(self, user_input, is_proactive=False, session_context=None, session_id="default"):
        input_msg = HumanMessage(content=user_input)
        system_prompt = await self._assemble_system_prompt(is_proactive, session_id)
        
        # 1. 用於此次推理的上下文 (包含完整的思考過程)
        reasoning_context = [SystemMessage(content=system_prompt)]
        if session_context: reasoning_context.extend(session_context)
        reasoning_context.append(input_msg)
        
        # 2. 開始記錄追蹤日誌 (Trace)
        await self.memory.log_trace(f"--- [NEW TASK] platform_id: {session_id} ---\nInput: {user_input}")
        
        await self._notify("starting", "啟動自主工程師模式...")
        
        final_reply = None
        last_action = ""
        
        for step in range(1, self.safety_limit + 1):
            try:
                await asyncio.sleep(0.1)
                thought_res = await self.brain.generate_thought(reasoning_context, system_prompt)
                
                act_type = thought_res.action_type.strip()
                act_param = thought_res.action_param.strip()
                
                # --- 紀錄 Trace ---
                await self.memory.log_trace(f"Step {step}:\n[THOUGHT] {thought_res.thought}\n[ACTION] {act_type}: {act_param}")
                
                # --- 格式校驗引導 ---
                if act_type == "INVALID_FORMAT":
                    obs = "Error: 你未遵循 [THOUGHT] 與 [ACTION] 格式。請重新輸出，必須包含具體的行動指令。"
                elif f"{act_type}:{act_param}" == last_action and act_type != "REPLY":
                    obs = "Error: 你正在重複相同的無效動作。請嘗試先 ls 或 cat 檔案來診斷。"
                else:
                    last_action = f"{act_type}:{act_param}"
                    await self._notify(f"step_{step}", thought_res.thought)
                    
                    if act_type == "REPLY":
                        final_reply = act_param
                        break
                    
                    # 執行動作
                    if act_type == "run_shell":
                        obs = await self.tool.execute("run_shell", {"command": act_param})
                    elif act_type == "read_nexus_file":
                        obs = await self.tool.execute("read_nexus_file", {"file_path": act_param})
                    elif act_type == "update_env_config":
                        try: obs = await self.tool.execute("update_env_config", json.loads(act_param.replace("'", '"')))
                        except: obs = "Error: JSON 格式錯誤。"
                    elif act_type == "restore_nexus_snapshot":
                        obs = await self.tool.execute("restore_nexus_snapshot", {})
                    else:
                        obs = f"Observation: 動作 '{act_type}' 已確認。請繼續下一步。"

                # 餵回推理上下文
                reasoning_context.append(AIMessage(content=f"[THOUGHT] {thought_res.thought}\n[ACTION] {act_type}: {act_param}"))
                reasoning_context.append(AIMessage(content=f"Observation: {obs}"))
                
                await self.memory.log_trace(f"[OBSERVATION] {obs[:500]}...") # 紀錄部分 Observation 避免 Log 過長
                await self._notify("observation", obs[:150])

            except Exception as e:
                err_trace = traceback.format_exc()
                error_msg = f"系統異常: {str(e)}\n{err_trace[-300:]}"
                await self.memory.log_trace(f"FATAL ERROR:\n{err_trace}")
                await self._notify("error", error_msg)
                reasoning_context.append(AIMessage(content=f"Observation: {error_msg}"))

        if final_reply:
            # --- 最終紀錄：乾淨的對話 Log 寫入 MD ---
            await self.memory.log_interaction([input_msg, AIMessage(content=final_reply)])
            return final_reply
        
        return "任務執行失敗，已達到推理上限。"
