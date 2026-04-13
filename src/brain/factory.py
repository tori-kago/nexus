from src.brain.llm.cli_adapter import GeminiCLIModel
import os

def get_brain_model():
    """根據環境變數傳回對應的 LLM 模型物件"""
    provider = os.getenv('BRAIN_MODEL_PROVIDER', 'gemini-cli')
    
    if provider == 'gemini-cli':
        return GeminiCLIModel()
    # 未來可以在這裡擴充其他模型 (如 OpenAI, Vertex AI 等)
    return GeminiCLIModel()
