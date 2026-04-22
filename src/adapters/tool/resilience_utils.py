import subprocess
import os
import logging

logger = logging.getLogger("Nexus.Resilience")

# 動態獲取專案根目錄
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def create_vault_snapshot(reason: str) -> bool:
    """
    為當前系統狀態建立 Git 快照。
    這通常在執行寫入操作 (如 update_config, digest_memory) 之前呼叫。
    """
    try:
        # 1. 檢查是否在 Git 儲存庫中
        if not os.path.exists(os.path.join(PROJECT_ROOT, ".git")):
            logger.warning("Not a git repository. Skipping snapshot.")
            return False

        # 2. Add 關鍵目錄 (vault 與 .env)
        # 我們只追蹤數據與配置的變動
        files_to_track = [
            os.path.join(PROJECT_ROOT, "src/brain/vault/"),
            os.path.join(PROJECT_ROOT, ".env")
        ]
        
        for path in files_to_track:
            if os.path.exists(path):
                subprocess.run(["git", "add", path], cwd=PROJECT_ROOT, capture_output=True)

        # 3. 檢查是否有變動需要提交
        status = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=PROJECT_ROOT)
        if status.returncode == 0:
            logger.info("No changes detected. Snapshot skipped.")
            return True # 沒有變動也算成功

        # 4. 提交快照
        commit_msg = f"[Nexus Auto-Snapshot] {reason}"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg], 
            cwd=PROJECT_ROOT, 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"Snapshot created: {commit_msg}")
            return True
        else:
            logger.error(f"Snapshot failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Snapshot internal error: {e}")
        return False

def rollback_vault() -> str:
    """
    將記憶與配置回滾到上一個快照狀態。
    """
    try:
        # 執行 git checkout
        result = subprocess.run(
            ["git", "checkout", "HEAD^", "--", "src/brain/vault/", ".env"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return "成功：已將記憶與配置回滾到上一個快照版本。請重啟服務以加載舊配置。"
        else:
            return f"回滾失敗：{result.stderr}"
    except Exception as e:
        return f"回滾發生錯誤：{str(e)}"
