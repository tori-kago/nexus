import os
import re
import json
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from src.brain.factory import get_brain_model
from src.shared.bus import MessageBus
from src.shared.schemas import NexusEnvelope, MessageType

# --- 1. Vault Manager (Search & Compression) ---
class VaultManager:
    def __init__(self, base_path: str = "src/brain/vault"):
        self.base_path = base_path
        self.paths = {
            "soul": os.path.join(base_path, "identity/soul.md"),
            "user": os.path.join(base_path, "identity/user.md"),
            "memory": os.path.join(base_path, "context/memory.md"),
            "logs": os.path.join(base_path, "logs")
        }

    def read_file(self, key: str) -> str:
        path = self.paths.get(key)
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def search_keyword(self, keyword: str) -> str:
        """跨檔案搜尋包含關鍵字的章節"""
        files_to_search = ["user", "memory"]
        results = []
        
        for key in files_to_search:
            content = self.read_file(key)
            if not content: continue
            
            # 按章節 (##) 分割
            sections = re.split(r"(?=## )", content)
            for sec in sections:
                if keyword.lower() in sec.lower():
                    # 提取檔名作為來源標記
                    results.append(f"來自 {key}.md:\n{sec.strip()}")
        
        return "\n\n---\n\n".join(results) if results else ""

    def append_to_file(self, key: str, section: str, line: str):
        path = self.paths.get(key)
        if not path or not os.path.exists(path):
            return
            
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        new_lines = []
        found_section = False
        inserted = False
        
        for i, l in enumerate(lines):
            new_lines.append(l)
            if section in l:
                found_section = True
            elif found_section and (l.startswith("#") or i == len(lines) - 1):
                if not inserted:
                    if not l.startswith("#") and i == len(lines) - 1:
                        if not l.endswith("\n"):
                            new_lines[-1] += "\n"
                        new_lines.append(f"- {line}\n")
                    else:
                        new_lines.insert(-1, f"- {line}\n")
                    inserted = True
                    found_section = False

        with open(path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    def write_log(self, messages: List[BaseMessage]):
        today = datetime.now().strftime("%Y-%m-%d")
        log_dir = self.paths["logs"]
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        log_path = os.path.join(log_dir, f"{today}.md")
        
        with open(log_path, "a", encoding="utf-8") as f:
            for m in messages:
                prefix = "User" if isinstance(m, HumanMessage) else "Nexus"
                f.write(f"### {prefix} ({datetime.now().strftime('%H:%M:%S')})\n")
                content = m.content if isinstance(m.content, str) else str(m.content)
                f.write(f"{content}\n\n")

    def compress_logs(self, model):
        """日誌壓縮邏輯"""
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = os.path.join(self.paths["logs"], f"{today}.md")
        
        if not os.path.exists(log_path):
            return
            
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        if len(content) > 1000:
            print(f"[Vault] Log reached {len(content)} chars, triggering smart compression...")
            prompt = f"請摘要以下日誌為 3 條關鍵記憶條目：\n\n{content}"
            summary = model.invoke([HumanMessage(content=prompt)]).content
            
            for line in summary.split("\n"):
                if line.strip().startswith("-"):
                    self.append_to_file("memory", "項目歷史摘要", line.strip()[2:])
            
            archive_path = log_path + f".{int(datetime.now().timestamp())}.bak"
            os.rename(log_path, archive_path)
            print(f"[Vault] Compression complete.")

# --- 2. Context Assembler (Agentic Prompting) ---
class ContextAssembler:
    def __init__(self, vault: VaultManager):
        self.vault = vault

    def assemble(self, is_proactive: bool = False) -> str:
        soul = self.vault.read_file("soul")
        
        prompt = f"""
{soul}

## 核心運作規約 (Reasoning Protocol)
1. 你現在處於「自主思考循環」中。
2. 你對用戶背景與項目事實的記憶是有限的，如果用戶提到的事情你不確定，**請務必先使用 SEARCH 動作**。
3. **每一輪回覆中，你必須且只能輸出一個 [THOUGHT] 與一個 [ACTION]。**

4. 可用 Action 類型:
   - REPLY: (回覆用戶，結束循環。必須包含情緒標籤)
   - SEARCH: (檢索記憶庫。參數為關鍵字，例如 SEARCH: 爬山。這是獲取背景資訊的首選方式)
   - REFLECT_USER: (紀錄用戶偏好)
   - REFLECT_MEMORY: (紀錄項目事實)
   - THINK: (純推理)
   - IGNORE: (僅在背景檢查時，若無須主動開口則使用)

5. 範例:
   [THOUGHT] 用戶提到了「明天的事情」，我需要查一下記憶庫裡關於明天的計畫。
   [ACTION] SEARCH: 明天
"""
        return prompt

# --- 3. Brain Engine (Agentic Reasoning Loop) ---
class BrainEngine:
    def __init__(self):
        self.model = get_brain_model()
        self.vault = VaultManager()
        self.assembler = ContextAssembler(self.vault)
        self.bus = MessageBus()
        self.max_steps = 6 # 增加步數以容納檢索過程

    def _notify(self, trace_id: str, session_id: Optional[str], state: str, reasoning: str):
        envelope = NexusEnvelope(
            source="brain:engine",
            type=MessageType.THOUGHT,
            trace_id=trace_id,
            session_id=session_id,
            payload={"state": state, "reasoning": reasoning}
        )
        self.bus.publish_envelope(envelope)

    async def run(self, trace_id: str, session_id: str, user_input: str, is_proactive: bool = False):
        if is_proactive:
            time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            input_msg = HumanMessage(content=f"[SYSTEM] 當前時間為 {time_str}。請進行背景反思：先 SEARCH 近期計畫，再決定是否需要主動提醒 maocao。")
        else:
            input_msg = HumanMessage(content=user_input)

        context = [
            SystemMessage(content=self.assembler.assemble(is_proactive)),
            input_msg
        ]
        
        self._notify(trace_id, session_id, "starting", "大腦啟動並準備檢索...")
        
        final_reply = None
        
        for step in range(self.max_steps):
            try:
                await asyncio.sleep(0.5)
                response = self.model.invoke(context)
                content = response.content.strip()
                
                # 清理
                content = re.sub(r"```(markdown|text)?\n", "", content)
                content = content.replace("```", "").strip()
                
                context.append(response)
                
                thought_match = re.search(r"\[THOUGHT\]\s*(.*?)\s*(?=\[ACTION\]|$)", content, re.DOTALL)
                action_match = re.search(r"\[ACTION\]\s*(.*?):\s*(.*)", content, re.DOTALL)
                
                thought = thought_match.group(1).strip() if thought_match else "分析中..."
                self._notify(trace_id, session_id, "thinking", thought[:100])
                
                if not action_match:
                    obs = "Error: 請使用 [ACTION] 標籤指定下一步動作。"
                else:
                    a_type = action_match.group(1).strip()
                    a_param = action_match.group(2).strip()
                    
                    if a_type == "REPLY":
                        final_reply = a_param
                        break
                    elif a_type == "IGNORE":
                        final_reply = "__IGNORE__"
                        break
                    elif a_type == "SEARCH":
                        found_info = self.vault.search_keyword(a_param)
                        if found_info:
                            obs = f"Observation: 在記憶庫中找到相關資訊如下：\n{found_info}"
                        else:
                            obs = f"Observation: 記憶庫中找不到關於 '{a_param}' 的具體紀錄。"
                    elif a_type == "REFLECT_USER":
                        self.vault.append_to_file("user", "溝通偏好", a_param)
                        obs = "Observation: 偏好已紀錄。"
                    elif a_type == "REFLECT_MEMORY":
                        self.vault.append_to_file("memory", "當前階段", a_param)
                        obs = "Observation: 事實已紀錄。"
                    else:
                        obs = f"Observation: 思考已確認。"
                
                context.append(AIMessage(content=obs))
                self._notify(trace_id, session_id, "observation", obs)
                
            except Exception as e:
                err_obs = f"Error: {str(e)}"
                context.append(AIMessage(content=err_obs))
                self._notify(trace_id, session_id, "error", err_obs)

        if final_reply and final_reply != "__IGNORE__":
            self.vault.write_log([input_msg, AIMessage(content=final_reply)])
            self.vault.compress_logs(self.model)
            return final_reply
        
        return None
