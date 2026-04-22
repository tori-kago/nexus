import subprocess
import json
import re
import asyncio
import logging
from typing import List, Any
from src.core.protocols import IBrainAdapter, ThoughtResponse

logger = logging.getLogger("Nexus.Brain")

class GeminiCLIBrainAdapter(IBrainAdapter):
    def __init__(self, model_name: str = 'gemini-cli'):
        self.model_name = model_name

    async def generate_thought(self, context: List[Any], system_prompt: str) -> ThoughtResponse:
        prompt_parts = [system_prompt]
        for msg in context:
            content = getattr(msg, "content", str(msg))
            prompt_parts.append(content)
        full_prompt = '\n'.join(prompt_parts)

        try:
            cmd = ['gemini', '--prompt', full_prompt, '--output-format', 'json']
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return ThoughtResponse(thought="系統錯誤", action_type="ERROR", action_param=stderr.decode())

            data = json.loads(stdout.decode())
            raw_content = data.get('response', stdout.decode()).strip()

            # --- 強化版 JSON 提取邏輯 ---
            # 1. 尋找第一對平衡的大括號 { ... }
            # 這是為了解決大腦在 JSON 外面加廢話或 Markdown 標籤的問題
            json_match = re.search(r'(\{.*\})', raw_content, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
                try:
                    # 嘗試解析
                    parsed = json.loads(json_str)
                    
                    # 獲取 action_type
                    act_type = str(parsed.get("action_type", "REPLY"))
                    
                    # 獲取 action_param，並支援多種可能的欄位名（容錯 LLM 的幻覺）
                    act_param = parsed.get("action_param")
                    if act_param is None or (act_type == "REPLY" and not str(act_param).strip()):
                        # 如果是 REPLY 且 param 為空，嘗試尋找其他可能的回覆欄位
                        act_param = parsed.get("reply") or parsed.get("content") or parsed.get("message") or act_param or ""

                    return ThoughtResponse(
                        thought=str(parsed.get("thought", "分析中...")),
                        action_type=act_type,
                        action_param=str(act_param)
                    )
                except json.JSONDecodeError:
                    pass # 失敗則走下方的 INVALID_FORMAT

            # 若找不到或解析失敗，回報格式錯誤
            return ThoughtResponse(
                thought="模型輸出非有效 JSON 或格式損毀",
                action_type="INVALID_FORMAT",
                action_param=raw_content
            )

        except Exception as e:
            return ThoughtResponse(thought="系統崩潰", action_type="ERROR", action_param=str(e))
