import os
import re
import logging
from datetime import datetime
from typing import List, Any, Dict, Optional
from src.core.protocols import IMemoryAdapter

# 設置日誌紀錄
logger = logging.getLogger("Nexus.Vault")

class VaultAdapter(IMemoryAdapter):
    """
    Nexus Memory 2.1 (Resilient & Digesting Vault)。
    支援主動上下文拼裝、分層提取、對話摘要與會話壓縮。
    """
    
    DEFAULT_SOUL = "你是 Nexus，一個溫馨、專業且具備自主思考能力的 AI 助手。"

    def __init__(self, base_path: str = "src/brain/vault"):
        self.base_path = base_path
        self.paths = {
            "soul": os.path.join(base_path, "identity/soul.md"),
            "user": os.path.join(base_path, "identity/user.md"),
            "memory": os.path.join(base_path, "context/memory.md"),
            "logs": os.path.join(base_path, "logs")
        }

    def _read_file_safe(self, key: str, max_chars: int = 2000) -> str:
        path = self.paths.get(key)
        if not path or not os.path.exists(path):
            return ""
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read(max_chars + 1)
                return content[:max_chars] if len(content) <= max_chars else content[:max_chars] + "..."
        except Exception:
            return ""

    async def get_core_context(self) -> str:
        soul = self._read_file_safe("soul") or self.DEFAULT_SOUL
        user = self._read_file_safe("user")
        # 只抓取最新的 5 條記憶摘要，防止 Context 爆炸
        facts_content = self._read_file_safe("memory", max_chars=1500)
        
        # 簡單提取最新的幾條事實 (假設以 - 開頭)
        fact_lines = [l for l in facts_content.split("\n") if l.strip().startswith("-")]
        recent_facts = "\n".join(fact_lines[-8:]) # 取得最後 8 條
        
        context_parts = [f"## 你的身分與性格\n{soul}"]
        if user: context_parts.append(f"## 關於用戶\n{user}")
        if recent_facts: context_parts.append(f"## 近期重要記憶\n{recent_facts}")
            
        return "\n\n".join(context_parts)

    async def save_fact(self, fact: str, category: str) -> bool:
        """儲存事實 (memory) 或偏好 (user)"""
        target_file = "user" if category == "user" else "memory"
        section_name = "溝通偏好" if category == "user" else "項目事實"
        path = self.paths.get(target_file)
        if not path or not os.path.exists(path): return False
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            new_lines = []
            found_section = False
            inserted = False
            for i, l in enumerate(lines):
                new_lines.append(l)
                if section_name in l: found_section = True
                elif found_section and (l.startswith("#") or i == len(lines) - 1):
                    if not inserted:
                        if not l.startswith("#") and i == len(lines) - 1:
                            if not l.endswith("\n"): new_lines[-1] += "\n"
                            new_lines.append(f"- {fact}\n")
                        else:
                            new_lines.insert(-1, f"- {fact}\n")
                        inserted = True
                        found_section = False
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            return True
        except Exception:
            return False

    async def digest_conversation(self, messages: List[Any], brain: Any):
        """
        記憶消化 (LCM-style Compaction)。執行前建立快照保護。
        """
        if len(messages) < 4: return
        
        # --- 健壯性防護：建立消化前快照 ---
        from src.adapters.tool.resilience_utils import create_vault_snapshot
        create_vault_snapshot("Before memory digestion")
        
        # 1. 準備摘要 Prompt
        history_text = ""
        for m in messages:
            role = "User" if "HumanMessage" in str(type(m)) else "Nexus"
            content = getattr(m, "content", str(m))
            history_text += f"{role}: {content[:200]}\n"
            
        summary_prompt = f"請將以下對話摘要為 1-2 條關鍵事實（以 '-' 開頭）：\n\n{history_text}"
        
        try:
            # 2. 呼叫大腦進行摘要 (注意：這裡需要傳入 brain adapter)
            from src.core.protocols import ThoughtResponse
            # 我們這裡簡化，直接呼叫 generate_thought 並期望它能處理摘要 (或是獨立的摘要介面)
            # 為了不改動太多，我們先假設 brain adapter 有一個 invoke 類方法
            res = await brain.generate_thought([{"role": "user", "content": summary_prompt}], "你是一個記憶摘要助手。")
            
            # 3. 提取事實並存入 memory.md
            summary = res.thought if res.action_type == "REPLY" else res.action_param
            for line in summary.split("\n"):
                if line.strip().startswith("-"):
                    await self.save_fact(line.strip()[2:], "memory")
            
            logger.info(f"[Memory] Digested {len(messages)} messages into long-term memory.")
        except Exception as e:
            logger.error(f"[Memory] Digestion failed: {e}")

    async def search(self, query: str) -> str:
        results = []
        for key in ["user", "memory"]:
            content = self._read_file_safe(key, max_chars=3000)
            sections = re.split(r"(?=## )", content)
            for sec in sections:
                if query.lower() in sec.lower():
                    results.append(f"來自 {key}.md:\n{sec.strip()}")
        return "\n\n---\n\n".join(results) if results else "找不到相關記憶。"

    async def log_interaction(self, messages: List[Any]):
        today = datetime.now().strftime("%Y-%m-%d")
        log_dir = self.paths["logs"]
        if not os.path.exists(log_dir): os.makedirs(log_dir)
        log_path = os.path.join(log_dir, f"{today}.md")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                for m in messages:
                    prefix = "User" if "HumanMessage" in str(type(m)) else "Nexus"
                    content = getattr(m, "content", str(m))
                    f.write(f"### {prefix} ({datetime.now().strftime('%H:%M:%S')})\n{content}\n\n")
        except Exception: pass

    def get_identity(self) -> str:
        return self._read_file_safe("soul") or self.DEFAULT_SOUL
