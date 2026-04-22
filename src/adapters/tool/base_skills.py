import os
import glob
import logging
from typing import List, Optional
from src.adapters.tool.resilience_utils import create_vault_snapshot, rollback_vault

ALLOWED_BASE = "/home/m2root/henry/nexus/"

# --- (既有技能: list, read, logs, update_config, restore, update_personality 略) ---
def list_nexus_files(directory: str = ".") -> str:
    abs_path = os.path.abspath(os.path.join(ALLOWED_BASE, directory))
    if not abs_path.startswith(ALLOWED_BASE): return "Error: Access Denied."
    try:
        items = os.listdir(abs_path)
        return "\n".join([i for i in items if not i.startswith(".")])
    except Exception as e: return str(e)

def read_nexus_file(file_path: str) -> str:
    abs_path = os.path.abspath(os.path.join(ALLOWED_BASE, file_path))
    if not abs_path.startswith(ALLOWED_BASE): return "Error: Access Denied."
    try:
        with open(abs_path, "r", encoding="utf-8") as f: return f.read(5000)
    except Exception as e: return str(e)

def get_recent_logs(lines: int = 50) -> str:
    log_dir = os.path.join(ALLOWED_BASE, "src/brain/vault/logs")
    log_files = glob.glob(os.path.join(log_dir, "*.md"))
    if not log_files: return "No logs."
    latest_log = max(log_files, key=os.path.getmtime)
    with open(latest_log, "r", encoding="utf-8") as f:
        return "".join(f.readlines()[-lines:])

def update_env_config(key: str, value: str) -> str:
    env_path = os.path.join(ALLOWED_BASE, ".env")
    allowed = ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION", "AZURE_TTS_VOICE", "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID", "EDGE_TTS_VOICE", "GOOGLE_API_KEY", "TELEGRAM_BOT_TOKEN", "DISCORD_BOT_TOKEN"]
    if key not in allowed: return "Denied."
    create_vault_snapshot(f"Update config: {key}")
    lines = open(env_path).readlines() if os.path.exists(env_path) else []
    new_lines = [l if not l.startswith(f"{key}=") else f"{key}={value}\n" for l in lines]
    if not any(l.startswith(f"{key}=") for l in lines): new_lines.append(f"{key}={value}\n")
    open(env_path, "w").writelines(new_lines)
    return f"Success: {key} updated."

def restore_nexus_snapshot() -> str:
    return rollback_vault()

def update_personality(new_soul_description: str) -> str:
    soul_path = os.path.join(ALLOWED_BASE, "src/brain/vault/identity/soul.md")
    try:
        create_vault_snapshot("Personality evolution")
        with open(soul_path, "w", encoding="utf-8") as f: f.write(new_soul_description)
        return "Success: Personality evolved."
    except Exception as e: return str(e)

# --- 新增：重置會話上下文 ---
def reset_session_context(session_id: str) -> str:
    """
    重置當前的對話上下文，清除短期記憶。
    這不會影響你的長期記憶 (Vault)。當用戶要求你「重新開始」或「忘記剛才的話」時使用。
    :param session_id: 目前的會話 ID (大腦應能自動獲取此上下文)
    """
    try:
        from src.core.session_store import SessionStore
        store = SessionStore()
        store.clear_session(session_id)
        return "成功：已重置對話上下文。我現在已經清空了剛才的對話紀錄，但依然記得關於用戶與自己的長期設定。"
    except Exception as e:
        return f"重置失敗: {str(e)}"
