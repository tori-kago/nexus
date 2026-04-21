import os
import glob
from typing import List, Optional
from src.adapters.tool.resilience_utils import create_vault_snapshot, rollback_vault

# 安全路徑限制：僅限 Nexus 專案目錄
ALLOWED_BASE = "/home/m2root/henry/nexus/"

def _is_safe_path(path: str) -> bool:
    abs_path = os.path.abspath(os.path.join(ALLOWED_BASE, path))
    if not abs_path.startswith(ALLOWED_BASE): return False
    sensitive_parts = [".git", "__pycache__", "node_modules"]
    if any(part in abs_path for part in sensitive_parts): return False
    return True

def list_nexus_files(directory: str = ".") -> str:
    if not _is_safe_path(directory): return "Error: Access Denied."
    try:
        target = os.path.join(ALLOWED_BASE, directory)
        if not os.path.isdir(target): return f"Error: '{directory}' is not a directory."
        items = os.listdir(target)
        return "\n".join([i for i in items if not i.startswith(".")])
    except Exception as e: return str(e)

def read_nexus_file(file_path: str) -> str:
    if not _is_safe_path(file_path): return "Error: Access Denied."
    try:
        target = os.path.join(ALLOWED_BASE, file_path)
        if not os.path.isfile(target): return f"Error: '{file_path}' is not a file."
        with open(target, "r", encoding="utf-8") as f:
            return f.read(5000)
    except Exception as e: return str(e)

def get_recent_logs(lines: int = 50) -> str:
    log_dir = os.path.join(ALLOWED_BASE, "src/brain/vault/logs")
    if not os.path.exists(log_dir): return "錯誤：找不到日誌目錄。"
    log_files = glob.glob(os.path.join(log_dir, "*.md"))
    if not log_files: return "目前沒有可用的日誌檔案。"
    latest_log = max(log_files, key=os.path.getmtime)
    try:
        with open(latest_log, "r", encoding="utf-8") as f:
            content = f.readlines()
            tail = content[-lines:] if len(content) > lines else content
            return "".join(tail)
    except Exception as e: return str(e)

def update_env_config(key: str, value: str) -> str:
    """
    自動更新 .env 檔案中的 API 金鑰或配置。執行前會建立備份快照。
    """
    env_path = os.path.join(ALLOWED_BASE, ".env")
    allowed_keys = [
        "AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION", "AZURE_TTS_VOICE",
        "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID",
        "EDGE_TTS_VOICE", "GOOGLE_API_KEY"
    ]
    
    if key not in allowed_keys:
        return f"錯誤：不允許修改 '{key}'。"

    # --- 關鍵防護：執行前建立快照 ---
    create_vault_snapshot(f"Before updating env config: {key}")

    try:
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        
        found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            if new_lines and not new_lines[-1].endswith("\n"): new_lines[-1] += "\n"
            new_lines.append(f"{key}={value}\n")
            
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
        return f"成功：已將 {key} 更新至 .env。快照已建立。"
    except Exception as e:
        return f"更新失敗: {str(e)}"

# 將回滾邏輯也包裝成技能
def restore_nexus_snapshot() -> str:
    """
    將系統的記憶、日誌與配置回滾到上一個自動快照狀態。
    當你發現最近的修改或設定有誤時，可以使用此技能。
    """
    return rollback_vault()
