import subprocess
import json
import re
import asyncio
from typing import List, Any
from src.core.protocols import IBrainAdapter, ThoughtResponse

class GeminiCLIBrainAdapter(IBrainAdapter):
    """
    直接使用 gemini cli 進行推理的適配器。
    不需要 langchain。
    """
    def __init__(self, model_name: str = 'gemini-cli'):
        self.model_name = model_name

    async def generate_thought(self, context: List[Any], system_prompt: str) -> ThoughtResponse:
        """
        將上下文轉為 prompt 並透過 subprocess 呼叫 gemini cli
        """
        # 1. 建立 Prompt
        prompt_parts = [system_prompt]
        for msg in context:
            # 支援 langchain 訊息對象或純字串
            content = getattr(msg, "content", str(msg))
            prompt_parts.append(content)
        
        full_prompt = '\n'.join(prompt_parts)

        # 2. 非同步呼叫 CLI
        try:
            # 使用 asyncio.create_subprocess_exec 以免阻塞主執行緒
            cmd = ['gemini', '--prompt', full_prompt, '--output-format', 'json']
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return ThoughtResponse(
                    thought="CLI 執行錯誤",
                    action_type="ERROR",
                    action_param=f"Exit {process.returncode}: {stderr.decode()}"
                )

            # 3. 解析 CLI 的 JSON 輸出
            data = json.loads(stdout.decode())
            # 根據您的 cli_adapter.py，回覆在 'response' 欄位
            # 但如果 CLI 直接回傳內容，我們也支援
            content = data.get('response', stdout.decode()).strip()

        except Exception as e:
            return ThoughtResponse(
                thought="例外發生",
                action_type="ERROR",
                action_param=str(e)
            )

        # 4. 解析 [THOUGHT] 與 [ACTION]
        thought_match = re.search(r"\[THOUGHT\]\s*(.*?)\s*(?=\[ACTION\]|$)", content, re.DOTALL)
        action_match = re.search(r"\[ACTION\]\s*(.*?):\s*(.*)", content, re.DOTALL)
        
        thought = thought_match.group(1).strip() if thought_match else "Gemini CLI 正在分析..."
        
        if not action_match:
            # 如果模型沒給 ACTION，預設為 REPLY 並清理情緒標籤
            return ThoughtResponse(
                thought=thought,
                action_type="REPLY",
                action_param=content
            )
            
        return ThoughtResponse(
            thought=thought,
            action_type=action_match.group(1).strip(),
            action_param=action_match.group(2).strip()
        )
