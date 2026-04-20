import os
import re
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from src.brain.factory import get_brain_model
from src.shared.bus import MessageBus
from src.shared.schemas import NexusEnvelope, MessageType

# --- 1. Vault Manager (Enhanced with Compression) ---
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

    def update_file(self, key: str, content: str):
        path = self.paths.get(key)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

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
                f.write(f"{m.content}\n\n")

    def compress_logs(self, model):
        """檢查當日日誌是否過長，若過長則進行壓縮並存入 memory.md"""
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = os.path.join(self.paths["logs"], f"{today}.md")
        
        if not os.path.exists(log_path):
            return
            
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        if len(content) > 3000: # 假設超過 3000 字元即觸發壓縮
            print(f"[Vault] Log too long ({len(content)} chars), compressing...")
            prompt = f"以下是今天的對話日誌，請將其總結為 3-5 條關鍵事實或項目進展，僅輸出以 '- ' 開頭的列表內容：\n\n{content}"
            summary = model.invoke([HumanMessage(content=prompt)]).content
            
            # 存入 memory.md 的「歷史摘要」章節
            for line in summary.split("\n"):
                if line.strip().startswith("-"):
                    self.append_to_file("memory", "項目歷史摘要", line.strip()[2:])
            
            # 存檔舊日誌並清空
            archive_path = log_path + ".bak"
            os.rename(log_path, archive_path)
            print(f"[Vault] Compressed and archived to {archive_path}")

# --- 2. Context Assembler (Enhanced with Dynamic Injection) ---
class ContextAssembler:
    def __init__(self, vault: VaultManager):
        self.vault = vault

    def assemble(self, needs: List[str] = None) -> str:
        soul = self.vault.read_file("soul")
        
        # 動態注入逻辑
        user_content = self.vault.read_file("user")
        memory_content = self.vault.read_file("memory")
        
        # 如果有特定需求，可以進一步過濾 (目前簡化為全量，但預留接口)
        if needs:
            # 這裡未來可以實作更複雜的 RAG 或標籤過濾
            pass

        prompt = f"""
{soul}

## 當前用戶背景 (User Context)
{user_content}

## 項目記憶與事實 (Project Memory)
{memory_content}

## 運作指令 (Reasoning Loop)
1. 你現在處於一個「思考循環」中。
2. 每一輪你必須選擇一個 Action 執行。
3. 格式必須為:
   [THOUGHT] (你的內心獨白，解釋為什麼選擇這個 Action)
   [ACTION] 類型: 參數
4. 可用 Action 類型:
   - REPLY: (最終回覆給用戶，結束循環)
   - REFLECT:USER: (紀錄用戶偏好)
   - REFLECT:MEMORY: (紀錄項目事實)
   - SEARCH: (目前的簡化版，你可以要求檢索更多 Vault 內容)
5. 範例:
   [THOUGHT] 用戶說他喜歡貓，我應該記下來。
   [ACTION] REFLECT:USER: 用戶喜歡貓。
   
   (系統會回傳 Observation: 已紀錄)
   
   [THOUGHT] 紀錄完了，現在可以回覆他。
   [ACTION] REPLY: 喵！我也很喜歡貓呢 (๑•̀ㅁ•́๑)✧ [EMOTION: happy]

6. **情緒標記**: 在最終 REPLY 的結尾加上 [EMOTION: 類型]。
"""
        return prompt

# --- 3. Brain Engine (Autonomous Reasoning Loop) ---
class BrainEngine:
    def __init__(self):
        self.model = get_brain_model()
        self.vault = VaultManager()
        self.assembler = ContextAssembler(self.vault)
        self.bus = MessageBus()
        self.max_steps = 5

    def _notify(self, trace_id: str, session_id: Optional[str], state: str, reasoning: str):
        envelope = NexusEnvelope(
            source="brain:engine",
            type=MessageType.THOUGHT,
            trace_id=trace_id,
            session_id=session_id,
            payload={"state": state, "reasoning": reasoning}
        )
        self.bus.publish_envelope(envelope)

    async def run(self, trace_id: str, session_id: str, user_input: str):
        """核心推理循環"""
        context = [
            SystemMessage(content=self.assembler.assemble()),
            HumanMessage(content=user_input)
        ]
        
        self._notify(trace_id, session_id, "starting", f"開始處理用戶輸入: {user_input[:20]}...")
        
        final_reply = None
        
        for step in range(self.max_steps):
            # 1. 呼叫模型
            try:
                response = self.model.invoke(context)
                content = response.content
                context.append(response)
                
                # 2. 解析 Thought & Action
                thought_match = re.search(r"\[THOUGHT\] (.*)", content)
                action_match = re.search(r"\[ACTION\] (.*?): (.*)", content)
                
                thought = thought_match.group(1) if thought_match else "思考中..."
                self._notify(trace_id, session_id, "thinking", thought)
                
                if not action_match:
                    # 如果 AI 沒按格式出牌，強行回饋
                    obs = "Error: Invalid format. Please use [THOUGHT] and [ACTION] labels."
                else:
                    action_type = action_match.group(1).strip()
                    action_param = action_match.group(2).strip()
                    
                    # 3. 執行 Action
                    if action_type == "REPLY":
                        final_reply = action_param
                        break
                    elif action_type == "REFLECT:USER":
                        self.vault.append_to_file("user", "溝通偏好", action_param)
                        obs = "Observation: 用戶事實已成功更新至 Vault。"
                    elif action_type == "REFLECT:MEMORY":
                        self.vault.append_to_file("memory", "當前階段", action_param)
                        obs = "Observation: 項目記憶已成功更新至 Vault。"
                    else:
                        obs = f"Observation: 未知 Action '{action_type}'，請嘗試 REPLY 或 REFLECT。"
                
                # 4. 加入 Observation 並進入下一輪
                context.append(AIMessage(content=f"Observation: {obs}"))
                self._notify(trace_id, session_id, "observation", obs)
                
            except Exception as e:
                # 5. 錯誤容忍 (環境回饋)
                err_obs = f"Observation Error: 執行過程中發生錯誤 {str(e)}。請嘗試修正策略或直接 REPLY。"
                context.append(AIMessage(content=err_obs))
                self._notify(trace_id, session_id, "error", err_obs)

        if not final_reply:
            final_reply = "對不起，我思考得太久了，暫時沒辦法給你完整的答案 (´;ω;`) [EMOTION: sad]"
            
        # 6. 記錄日誌 & 檢查壓縮
        self.vault.write_log([HumanMessage(content=user_input), AIMessage(content=final_reply)])
        self.vault.compress_logs(self.model)
        
        return final_reply
