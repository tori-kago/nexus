import os
import glob
from typing import List, Optional
from src.adapters.tool.resilience_utils import create_vault_snapshot, rollback_vault

# 安全路徑限制
ALLOWED_BASE = "/home/m2root/henry/nexus/"

# --- (既有技能略: list, read, logs, update_config, restore) ---

def list_nexus_files(directory: str = ".") -> str:
    abs_path = os.path.abspath(os.path.join(ALLOWED_BASE, directory))
    if not abs_path.startswith(ALLOWED_BASE): return "Error: Access Denied."
    try:
        target = os.path.join(ALLOWED_BASE, directory)
        items = os.listdir(target)
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
    allowed = ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION", "AZURE_TTS_VOICE", "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID", "EDGE_TTS_VOICE", "GOOGLE_API_KEY"]
    if key not in allowed: return "Denied."
    create_vault_snapshot(f"Update config: {key}")
    lines = open(env_path).readlines() if os.path.exists(env_path) else []
    new_lines = [l if not l.startswith(f"{key}=") else f"{key}={value}\n" for l in lines]
    if not any(l.startswith(f"{key}=") for l in lines): new_lines.append(f"{key}={value}\n")
    open(env_path, "w").writelines(new_lines)
    return "Success."

def restore_nexus_snapshot() -> str:
    return rollback_vault()

# --- 新增核心技能：性格進化 ---
def update_personality(new_soul_description: str) -> str:
    """
    修改 Nexus 的靈魂核心 (soul.md)。
    當用戶要求你調整性格、語氣、回覆風格或增加新的行為準則時使用。
    :param new_soul_description: 完整的、優化後的性格描述 Markdown 文本。
    """
    soul_path = os.path.join(ALLOWED_BASE, "src/brain/vault/identity/soul.md")
    
    try:
        # 1. 建立進化前快照
        create_vault_snapshot("Before personality evolution (Soul update)")
        
        # 2. 寫入新的性格描述
        with open(soul_path, "w", encoding="utf-8") as f:
            f.write(new_soul_description)
            
        return "進化成功：我的靈魂核心已更新。下一次對話開始時，我將展現新的性格面貌。"
    except Exception as e:
        return f"進化失敗: {str(e)}"
