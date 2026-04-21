import os
import glob
from typing import List, Optional

# 安全路徑限制：僅限 Nexus 專案目錄
ALLOWED_BASE = "/home/m2root/henry/nexus/"

def _is_safe_path(path: str) -> bool:
    abs_path = os.path.abspath(os.path.join(ALLOWED_BASE, path))
    if not abs_path.startswith(ALLOWED_BASE):
        return False
    sensitive_parts = [".git", ".env", "__pycache__", "node_modules"]
    if any(part in abs_path for part in sensitive_parts):
        return False
    return True

def list_nexus_files(directory: str = ".") -> str:
    if not _is_safe_path(directory):
        return "Error: Access Denied."
    try:
        target = os.path.join(ALLOWED_BASE, directory)
        if not os.path.isdir(target): return f"Error: '{directory}' is not a directory."
        items = os.listdir(target)
        return "\n".join([i for i in items if not i.startswith(".")])
    except Exception as e: return str(e)

def read_nexus_file(file_path: str) -> str:
    if not _is_safe_path(file_path):
        return "Error: Access Denied."
    try:
        target = os.path.join(ALLOWED_BASE, file_path)
        if not os.path.isfile(target): return f"Error: '{file_path}' is not a file."
        with open(target, "r", encoding="utf-8") as f:
            return f.read(5000)
    except Exception as e: return str(e)

def get_recent_logs(lines: int = 50) -> str:
    """
    獲取 Nexus 系統最新的執行日誌與對話紀錄。
    這能幫助你了解最近發生的錯誤或對話脈絡。
    :param lines: 要讀取的最後幾行行數
    """
    log_dir = os.path.join(ALLOWED_BASE, "src/brain/vault/logs")
    if not os.path.exists(log_dir):
        return "錯誤：找不到日誌目錄。"
        
    # 找到最新的 .md 日誌檔
    log_files = glob.glob(os.path.join(log_dir, "*.md"))
    if not log_files:
        return "目前沒有可用的日誌檔案。"
        
    latest_log = max(log_files, key=os.path.getmtime)
    filename = os.path.basename(latest_log)
    
    try:
        with open(latest_log, "r", encoding="utf-8") as f:
            content = f.readlines()
            # 取得最後 N 行
            tail = content[-lines:] if len(content) > lines else content
            return f"--- 來自日誌 {filename} 的最後 {len(tail)} 行 ---\n" + "".join(tail)
    except Exception as e:
        return f"讀取日誌失敗: {str(e)}"
