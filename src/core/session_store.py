import sqlite3
import json
import os
import logging
from typing import List, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger("Nexus.SessionStore")
# 動態獲取專案根目錄，避免硬編碼路徑
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(PROJECT_ROOT, "src/brain/vault/sessions.db")

class SessionStore:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(DB_PATH) as conn:
            # 升級資料表：加入平台資訊
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    platform TEXT,           -- tg, discord, cli
                    platform_user_id TEXT,    -- chat_id, user_id
                    messages_json TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def register_platform(self, session_id: str, platform: str, user_id: str):
        """將會話與具體平台帳號綁定"""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                UPDATE sessions SET platform = ?, platform_user_id = ?
                WHERE session_id = ?
            """, (platform, user_id, session_id))
            conn.commit()

    def get_messages(self, session_id: str) -> List[Any]:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.execute("SELECT messages_json FROM sessions WHERE session_id = ?", (session_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    raw_messages = json.loads(row[0])
                    return [HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"]) for m in raw_messages]
                return []
        except Exception as e:
            logger.error(f"Error fetching: {e}")
            return []

    def save_messages(self, session_id: str, messages: List[Any], platform: str = None, platform_user_id: str = None):
        """保存訊息並同步更新平台資訊"""
        try:
            serializable = [{"role": "user" if isinstance(m, HumanMessage) else "nexus", "content": getattr(m, "content", str(m))} for m in messages]
            if len(serializable) > 14: serializable = serializable[-14:]

            with sqlite3.connect(DB_PATH) as conn:
                # 使用 INSERT OR REPLACE 配合平台資訊
                conn.execute("""
                    INSERT INTO sessions (session_id, messages_json, platform, platform_user_id, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(session_id) DO UPDATE SET 
                        messages_json = excluded.messages_json,
                        platform = COALESCE(excluded.platform, sessions.platform),
                        platform_user_id = COALESCE(excluded.platform_user_id, sessions.platform_user_id),
                        updated_at = CURRENT_TIMESTAMP
                """, (session_id, json.dumps(serializable), platform, platform_user_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving: {e}")

    def get_active_sessions(self, hours: int = 24) -> List[dict]:
        """獲取最近活躍的會話及其平台資訊"""
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(f"SELECT * FROM sessions WHERE updated_at > datetime('now', '-{hours} hours')")
            return [dict(row) for row in cursor.fetchall()]

    def clear_session(self, session_id: str):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
