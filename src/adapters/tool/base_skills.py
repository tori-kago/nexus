import os
import subprocess
import glob
from typing import List, Optional
from src.adapters.tool.resilience_utils import create_vault_snapshot, rollback_vault

ALLOWED_BASE = "/home/m2root/henry/nexus/"

def run_shell(command: str) -> str:
    """執行終端機指令。用於診斷環境、安裝依賴或執行技能。"""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, 
            cwd=ALLOWED_BASE, timeout=120
        )
        if result.returncode != 0:
            return f"Error (Code {result.returncode}):\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        return result.stdout if result.stdout else "Success (no output)."
    except Exception as e: return f"System Error: {str(e)}"

def read_nexus_file(file_path: str) -> str:
    """讀取專案內特定檔案的內容。"""
    target = os.path.abspath(os.path.join(ALLOWED_BASE, file_path))
    if not target.startswith(ALLOWED_BASE): return "Access Denied."
    try:
        with open(target, "r", encoding="utf-8") as f: return f.read(8000)
    except Exception as e: return str(e)

def update_env_config(key: str, value: str) -> str:
    """更新 .env 中的 API 配置。"""
    env_path = os.path.join(ALLOWED_BASE, ".env")
    allowed = ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION", "AZURE_TTS_VOICE", "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID", "EDGE_TTS_VOICE", "GOOGLE_API_KEY", "TELEGRAM_BOT_TOKEN", "DISCORD_BOT_TOKEN"]
    if key not in allowed: return "Config denied."
    create_vault_snapshot(f"Update config: {key}")
    try:
        lines = open(env_path).readlines() if os.path.exists(env_path) else []
        new_lines = [l if not l.startswith(f"{key}=") else f"{key}={value}\n" for l in lines]
        if not any(l.startswith(f"{key}=") for l in lines): new_lines.append(f"{key}={value}\n")
        with open(env_path, "w", encoding="utf-8") as f: f.writelines(new_lines)
        return f"Success: {key} updated."
    except: return "Update failed."

def restore_nexus_snapshot() -> str:
    """回滾到上一個系統快照。"""
    return rollback_vault()

def update_personality(new_soul: str) -> str:
    """優化性格描述文件 (soul.md)。"""
    path = os.path.join(ALLOWED_BASE, "src/brain/vault/identity/soul/traits.md")
    create_vault_snapshot("Soul evolution")
    try:
        with open(path, "w", encoding="utf-8") as f: f.write(new_soul)
        return "Evolved successfully."
    except Exception as e: return str(e)

def reset_session_context(session_id: str) -> str:
    """清除當前對話歷史。"""
    try:
        from src.core.session_store import SessionStore
        SessionStore().clear_session(session_id)
        return "Memory cleared."
    except Exception as e: return str(e)

def record_work_insight(insight: str) -> str:
    """紀錄研究心得。"""
    path = os.path.join(ALLOWED_BASE, "src/brain/vault/identity/soul/growth.md")
    from datetime import datetime
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"- **{datetime.now().strftime('%Y-%m-%d')}**: {insight}\n")
        return "Recorded."
    except Exception as e: return str(e)
