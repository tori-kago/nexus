import os
import re
import asyncio
from typing import List, Any
from src.core.protocols import IBrainAdapter, ThoughtResponse

# 假設這裡使用 Google 官方 SDK (google-generativeai)
# 若是純指令行工具，可以改用 subprocess
try:
    import google.generativeai as genai
except ImportError:
    genai = None

class GeminiBrainAdapter(IBrainAdapter):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if genai and self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-pro')
        else:
            self.model = None
            print("[Warning] Gemini SDK not installed or API Key missing.")

    async def generate_thought(self, context: List[Any], system_prompt: str) -> ThoughtResponse:
        """
        將上下文轉換為 Gemini 格式並取得回覆
        """
        if not self.model:
            return ThoughtResponse(thought="錯誤", action_type="ERROR", action_param="Gemini 未配置")

        # 1. 轉換 Context 格式 (將 Langchain 訊息或自定義訊息轉為 Gemini 格式)
        # 這裡簡化處理：提取最後一條 user input 與 system prompt
        # 實作時應考慮歷史對話 (History)
        prompt_parts = [system_prompt]
        for msg in context:
            # 根據不同消息類型提取內容 (支援 Langchain 消息或純字串)
            content = getattr(msg, "content", str(msg))
            prompt_parts.append(content)
            
        full_prompt = "\n\n".join(prompt_parts)

        # 2. 呼叫 Gemini (使用非同步方式)
        # 注意：genai 預設是同步的，建議放在 run_in_executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: self.model.generate_content(full_prompt))
        content = response.text.strip()

        # 3. 解析 [THOUGHT] 與 [ACTION] (維持與協定一致)
        thought_match = re.search(r"\[THOUGHT\]\s*(.*?)\s*(?=\[ACTION\]|$)", content, re.DOTALL)
        action_match = re.search(r"\[ACTION\]\s*(.*?):\s*(.*)", content, re.DOTALL)
        
        thought = thought_match.group(1).strip() if thought_match else "Gemini 正在分析..."
        
        if not action_match:
            return ThoughtResponse(
                thought=thought,
                action_type="REPLY", # 預設若解析失敗則直接回覆
                action_param=f"[EMOTION: neutral] {content}"
            )
            
        return ThoughtResponse(
            thought=thought,
            action_type=action_match.group(1).strip(),
            action_param=action_match.group(2).strip()
        )
