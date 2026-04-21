import re
from typing import List, Any
from src.core.protocols import IBrainAdapter, ThoughtResponse
from src.brain.factory import get_brain_model

class LangchainBrainAdapter(IBrainAdapter):
    def __init__(self):
        self.model = get_brain_model()

    async def generate_thought(self, context: List[Any], system_prompt: str) -> ThoughtResponse:
        # 在此進行模型調用
        # 這裡簡化實作，假設 context 已經是正確的格式 (Langchain Messages)
        response = self.model.invoke(context)
        content = response.content.strip()
        
        # 解析結構化輸出 [THOUGHT] 與 [ACTION]
        content = re.sub(r"```(markdown|text)?\n", "", content)
        content = content.replace("```", "").strip()
        
        thought_match = re.search(r"\[THOUGHT\]\s*(.*?)\s*(?=\[ACTION\]|$)", content, re.DOTALL)
        action_match = re.search(r"\[ACTION\]\s*(.*?):\s*(.*)", content, re.DOTALL)
        
        thought = thought_match.group(1).strip() if thought_match else "分析中..."
        
        if not action_match:
            return ThoughtResponse(
                thought=thought,
                action_type="ERROR",
                action_param="模型未提供 [ACTION] 標籤"
            )
            
        return ThoughtResponse(
            thought=thought,
            action_type=action_match.group(1).strip(),
            action_param=action_match.group(2).strip()
        )
