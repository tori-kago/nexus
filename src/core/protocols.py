from typing import Protocol, List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel

class MessageType(str, Enum):
    """
    系統通訊訊息類型 (System Communication Message Types)。
    定義了 Gateway 與核心調度器、以及前端 WebSocket 之間傳遞的標準訊息分類。
    """
    INPUT = "input"       # 來自用戶的原生輸入 (文字或語音辨識後的文字)
    THOUGHT = "thought"   # 大腦內部的推理狀態 (State) 與推理內容 (Reasoning)
    TEXT = "text"         # 大腦決定的最終文字回覆內容
    AUDIO = "audio"       # 語音合成後的音訊路徑或流 (由 MediaAdapter 產生)
    COMMAND = "command"   # 系統指令，通常指 [ACTION] EXECUTE 觸發的動作
    OBSERVATION = "observation" # 外部工具 (Tool/Memory) 執行後的反饋觀察結果

class ThoughtResponse(BaseModel):
    """
    大腦推理循環的單輪決策結果 (Reasoning Step Output)。
    包含了大腦目前的思考細節與它決定採取的下一個動作。
    """
    thought: str      # 具體的思考內容與推理路徑
    action_type: str  # 動作類型 (如 REPLY, SEARCH, EXECUTE, REFLECT)
    action_param: str # 動作所需的參數內容 (可能是 JSON 字串)

class IBrainAdapter(Protocol):
    """
    大腦推理適配器介面 (Brain Reasoning Provider Protocol)。
    負責對接不同的大語言模型 (LLM)，將 Context 轉換為思考與動作。
    """
    async def generate_thought(self, context: List[Any], system_prompt: str) -> ThoughtResponse:
        """接收上下文與系統提示詞，回傳模型的推理結果"""
        ...

class IMemoryAdapter(Protocol):
    """
    記憶與資料庫適配器介面 (Memory & Storage Provider Protocol)。
    負責持久化存儲身分資訊、事實與對話日誌，並提供語意或關鍵字檢索。
    """
    async def search(self, query: str) -> str:
        """根據關鍵字或向量檢索相關的記憶章節或上下文片段"""
        ...
        
    async def save_fact(self, fact: str, category: str) -> bool:
        """儲存新的事實 (memory) 或用戶偏好 (user) 到持久化存儲中"""
        ...
        
    async def log_interaction(self, messages: List[Any]):
        """將完整的對話上下文紀錄到日誌系統中"""
        ...

class IToolAdapter(Protocol):
    """
    外部工具/技能執行適配器介面 (External Tool/Skill Provider Protocol)。
    負責執行具體的 Python 函數、API 呼叫或系統操作，並回報執行結果。
    """
    async def execute(self, tool_name: str, params: Dict[str, Any]) -> str:
        """執行指定的工具名稱與參數，並回傳執行結果的文字描述"""
        ...
        
    def get_system_prompt_fragment(self) -> str:
        """生成一份詳細的工具說明書 (Capabilities)，用於注入到大腦的 System Prompt 中"""
        ...

class IMediaAdapter(Protocol):
    """
    多媒體 (STT/TTS) 適配器介面 (Media Processing Protocol)。
    負責處理音訊與文字之間的雙向轉換，確保系統具備聽力與說話的能力。
    """
    async def text_to_speech(self, text: str) -> str:
        """將文字轉換為語音音訊，回傳音訊檔案路徑或 URL"""
        ...
        
    async def speech_to_text(self, audio_data: Any) -> str:
        """將原始音訊數據轉換為文字內容"""
        ...
