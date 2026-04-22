import subprocess
import json
import re
import asyncio
from typing import List, Any
from src.core.protocols import IBrainAdapter, ThoughtResponse

class GeminiCLIBrainAdapter(IBrainAdapter):
    def __init__(self, model_name: str = 'gemini-cli'):
        self.model_name = model_name

    async def generate_thought(self, context: List[Any], system_prompt: str) -> ThoughtResponse:
        """
        對標 OpenClaw 穩定性：強制執行標籤解析。
        """
        # 1. 建立完整 Prompt
        prompt_parts = [system_prompt]
        for msg in context:
            content = getattr(msg, "content", str(msg))
            prompt_parts.append(content)
        full_prompt = '\n'.join(prompt_parts)

        # 2. 呼叫 Gemini CLI
        try:
            cmd = ['gemini', '--prompt', full_prompt, '--output-format', 'json']
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return ThoughtResponse(
                    thought="系統錯誤",
                    action_type="ERROR",
                    action_param=f"CLI Exit {process.returncode}: {stderr.decode()}"
                )

            data = json.loads(stdout.decode())
            raw_content = data.get('response', stdout.decode()).strip()

            # --- OpenClaw 風格之嚴格解析 ---
            # 尋找標籤位置
            thought_idx = raw_content.find("[THOUGHT]")
            action_idx = raw_content.find("[ACTION]")

            if thought_idx != -1 and action_idx != -1:
                # 正常情況：兩者皆具
                thought = raw_content[thought_idx + 9 : action_idx].strip()
                action_part = raw_content[action_idx + 8 :].strip()
                
                if ":" in action_part:
                    a_type, a_param = action_part.split(":", 1)
                    return ThoughtResponse(
                        thought=thought,
                        action_type=a_type.strip(),
                        action_param=a_param.strip()
                    )
                else:
                    return ThoughtResponse(thought=thought, action_type="THINK", action_param=action_part)
            
            # 異常情況：格式不符
            # 我們不再預設為 REPLY，而是回報給 Orchestrator 進行 Observation 引導
            return ThoughtResponse(
                thought="模型輸出格式未遵循規範",
                action_type="INVALID_FORMAT",
                action_param=raw_content
            )

        except Exception as e:
            return ThoughtResponse(thought="系統崩潰", action_type="ERROR", action_param=str(e))
