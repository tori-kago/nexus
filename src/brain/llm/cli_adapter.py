import subprocess
import json
from typing import List, Optional, Any
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

class GeminiCLIModel(BaseChatModel):
    model_name: str = 'gemini-cli'

    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs: Any) -> ChatResult:
        # 確保 prompt 組合正確
        prompt_parts = []
        for m in messages:
            content = m.content if isinstance(m.content, str) else str(m.content)
            prompt_parts.append(content)
        prompt = '\n'.join(prompt_parts)
        
        try:
            cmd = ['gemini', '--prompt', prompt, '--output-format', 'json']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            response_text = data.get('response', '')
            
            message = AIMessage(content=response_text)
            return ChatResult(generations=[ChatGeneration(message=message)])
        except subprocess.CalledProcessError as e:
            err_msg = f'Error calling gemini-cli (exit {e.returncode}): {e.stderr or e.stdout}'
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=err_msg))])
        except Exception as e:
            err_msg = f'Unexpected error: {e}'
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=err_msg))])

    @property
    def _llm_type(self) -> str:
        return 'gemini-cli'
