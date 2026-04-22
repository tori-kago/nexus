import os
import re
import logging
import glob
from datetime import datetime
from typing import List, Any, Dict, Optional
from src.core.protocols import IMemoryAdapter

logger = logging.getLogger("Nexus.Vault")

class VaultAdapter(IMemoryAdapter):
    def __init__(self, base_path: str = "src/brain/vault"):
        self.base_path = base_path
        self.paths = {
            "soul_dir": os.path.join(base_path, "identity/soul"),
            "user": os.path.join(base_path, "identity/user.md"),
            "memory": os.path.join(base_path, "context/memory.md"),
            "logs": os.path.join(base_path, "logs"),
            "db": os.path.join(base_path, "sessions.db")
        }

    def _read_file_safe(self, path: str, max_chars: int = 3000) -> str:
        if not os.path.exists(path): return ""
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read(max_chars + 1)
                return content[:max_chars] if len(content) <= max_chars else content[:max_chars] + "..."
        except Exception: return ""

    async def get_core_context(self) -> str:
        # 1. 聚合立體人格 (Soul)
        soul_parts = []
        soul_files = glob.glob(os.path.join(self.paths["soul_dir"], "*.md"))
        for f in sorted(soul_files): # 排序確保穩定的順序
            content = self._read_file_safe(f)
            if content:
                soul_parts.append(content)
        
        soul_full = "\n\n---\n\n".join(soul_parts)
        if not soul_full: soul_full = "你是 Nexus，一個具備自主思考能力的 AI 助手。"

        # 2. 獲取用戶偏好
        user = self._read_file_safe(self.paths["user"])
        
        # 3. 獲取近期事實 (從 memory.md 提取最後 10 條)
        facts_content = self._read_file_safe(self.paths["memory"])
        fact_lines = [l for l in facts_content.split("\n") if l.strip().startswith("-")]
        recent_facts = "\n".join(fact_lines[-10:])
        
        # 4. 拼裝
        context_parts = [
            f"# 你的靈魂與性格 (Soul Definition)\n{soul_full}",
        ]
        if user: context_parts.append(f"# 用戶背景 (User)\n{user}")
        if recent_facts: context_parts.append(f"# 長期記憶 (Memory)\n{recent_facts}")
            
        return "\n\n".join(context_parts)

    async def save_fact(self, fact: str, category: str) -> bool:
        target_path = self.paths["user"] if category == "user" else self.paths["memory"]
        section = "溝通偏好" if category == "user" else "項目事實"
        try:
            lines = open(target_path).readlines() if os.path.exists(target_path) else []
            found = False
            new_lines = []
            for i, l in enumerate(lines):
                new_lines.append(l)
                if section in l: found = True
                elif found and (l.startswith("#") or i == len(lines)-1):
                    new_lines.insert(-1 if l.startswith("#") else len(new_lines), f"- {fact}\n")
                    found = False
            if not any(section in l for l in lines):
                new_lines.extend([f"## {section}\n", f"- {fact}\n"])
            with open(target_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            return True
        except: return False

    async def digest_conversation(self, messages: List[Any], brain: Any):
        # 建立快照並呼叫摘要 (略，維持原邏輯)
        from src.adapters.tool.resilience_utils import create_vault_snapshot
        create_vault_snapshot("Memory digestion")
        # 這裡實作略過...
        pass

    async def search(self, query: str) -> str:
        # 在 user 和 memory 中檢索
        results = []
        for key in ["user", "memory"]:
            content = self._read_file_safe(self.paths[key])
            for sec in re.split(r"(?=## )", content):
                if query.lower() in sec.lower(): results.append(sec.strip())
        return "\n\n".join(results) if results else "找不到記憶。"

    async def log_interaction(self, messages: List[Any]):
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = os.path.join(self.paths["logs"], f"{today}.md")
        if not os.path.exists(self.paths["logs"]): os.makedirs(self.paths["logs"])
        with open(log_path, "a", encoding="utf-8") as f:
            for m in messages:
                role = "User" if "HumanMessage" in str(type(m)) else "Nexus"
                f.write(f"### {role} ({datetime.now().strftime('%H:%M')})\n{getattr(m, 'content', str(m))}\n\n")

    async def log_trace(self, content: str):
        today = datetime.now().strftime("%Y-%m-%d")
        trace_path = os.path.join(self.paths["logs"], f"trace_{today}.log")
        if not os.path.exists(self.paths["logs"]): os.makedirs(self.paths["logs"])
        with open(trace_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {content}\n")

    def get_identity(self) -> str:
        # 回退方法 (傳統相容)
        return "Nexus, 立體人格實施中"

    @property
    def DB_PATH(self): return self.paths["db"]
