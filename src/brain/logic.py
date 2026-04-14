import os
from datetime import datetime
from typing import TypedDict, Annotated, List, Optional
import operator

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from src.brain.factory import get_brain_model
from src.shared.bus import MessageBus
from src.shared.schemas import NexusEnvelope, MessageType

# --- 1. Vault Manager (保持原樣) ---
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
        """完全覆蓋檔案內容"""
        path = self.paths.get(key)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    def append_to_file(self, key: str, section: str, line: str):
        """在特定標題下追加一行"""
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
                # 如果遇到下一個標題或文件結尾，插入新行
                if not inserted:
                    if not l.startswith("#") and i == len(lines) - 1:
                        # 文件末尾
                        if not l.endswith("\n"):
                            new_lines[-1] += "\n"
                        new_lines.append(f"- {line}\n")
                    else:
                        # 下一個標題前
                        new_lines.insert(-1, f"- {line}\n")
                    inserted = True
                    found_section = False

        with open(path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    def write_log(self, messages: List[BaseMessage]):
        """將對話寫入當日日誌"""
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

# --- 2. Context Assembler (保持原樣) ---
class ContextAssembler:
    def __init__(self, vault: VaultManager):
        self.vault = vault

    def assemble(self) -> str:
        soul = self.vault.read_file("soul")
        user = self.vault.read_file("user")
        memory = self.vault.read_file("memory")

        prompt = f"""
{soul}

## 當前用戶背景 (User Context)
{user}

## 項目記憶與事實 (Project Memory)
{memory}

## 運作指令 (Operational Instructions)
1. 始終保持 Nexus 的性格與說話風格。
2. 優先參考上述記憶與事實進行回覆。
3. **反思機制**: 
   如果你發現新的「用戶偏好」或「項目事實」，請在回覆最後一行加上以下標記：
   [REFLECT:USER] (描述新的用戶偏好)
   或
   [REFLECT:MEMORY] (描述新的項目事實)
   範例 (僅供參考格式)：
   [REFLECT:USER] (在此處描述新的用戶偏好)
   [REFLECT:MEMORY] (在此處描述新的項目事實)
"""
        return prompt

# --- 3. 定義狀態與邏輯節點 ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    trace_id: str  # 新增：追蹤 ID

class BrainLogic:
    def __init__(self):
        self.model = get_brain_model()
        self.vault = VaultManager()
        self.assembler = ContextAssembler(self.vault)
        self.bus = MessageBus() # 注入 Bus 用於發送狀態

    def _notify(self, trace_id: str, state: str, reasoning: str):
        """發送 Thought 訊號 (無靜默回覆)"""
        envelope = NexusEnvelope(
            source="brain:logic",
            type=MessageType.THOUGHT,
            trace_id=trace_id,
            payload={"state": state, "reasoning": reasoning}
        )
        self.bus.publish_envelope(envelope)

    def call_model(self, state: AgentState):
        # 1. 發送正在思考的訊號
        self._notify(state['trace_id'], "thinking", "正在檢索記憶並組裝 Prompt...")
        
        # 2. 組裝動態 System Prompt
        system_prompt = self.assembler.assemble()
        
        # 3. 準備完整的訊息列表 (System + History)
        full_messages = [SystemMessage(content=system_prompt)] + state['messages']
        
        # 4. 呼叫模型
        response = self.model.invoke(full_messages)
        
        # 5. 記錄對話 (僅記錄最後一輪)
        self.vault.write_log([state['messages'][-1], response])
        
        return {"messages": [response]}

    def reflect(self, state: AgentState):
        """解析模型回覆中的 [REFLECT] 標記並更新 Vault"""
        last_message = state['messages'][-1]
        content = last_message.content
        
        import re
        user_matches = re.findall(r"\[REFLECT:USER\] (.*)", content)
        memory_matches = re.findall(r"\[REFLECT:MEMORY\] (.*)", content)
        
        if user_matches or memory_matches:
            self._notify(state['trace_id'], "reflecting", f"發現了 {len(user_matches)} 個用戶事實與 {len(memory_matches)} 個項目記憶，正在更新 Vault...")
        
        for fact in user_matches:
            self.vault.append_to_file("user", "溝通偏好", fact)
            
        for fact in memory_matches:
            self.vault.append_to_file("memory", "當前階段", fact)
            
        return state

# --- 4. 建立 LangGraph 圖表 ---
def create_brain_graph():
    brain = BrainLogic()
    workflow = StateGraph(AgentState)
    
    workflow.add_node("think", brain.call_model)
    workflow.add_node("reflect", brain.reflect)
    
    workflow.add_edge(START, "think")
    workflow.add_edge("think", "reflect")
    workflow.add_edge("reflect", END)
    
    return workflow.compile()
