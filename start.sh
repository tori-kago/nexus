#!/bin/bash

# --- Nexus 一鍵啟動腳本 (非 Docker 版) ---

# 設置環境變數 (確保 Python 能找到 src 模組)
export PYTHONPATH=$PYTHONPATH:$(pwd)

# 獲取腳本所在目錄的 PID，以便稍後一起關閉
trap "kill 0" EXIT

echo "[1/3] 正在啟動 Gateway (大腦)..."
python -m src.gateway.main &

echo "[2/3] 正在啟動 Telegram Bot..."
python -m src.agent.tg_bot &

echo "[3/3] 正在啟動 Discord Bot..."
python -m src.agent.discord_bot &

echo "---------------------------------------"
echo "Nexus 系統已全部啟動！按 Ctrl+C 可同時關閉所有服務。"
echo "---------------------------------------"

# 持續等待，直到使用者按下 Ctrl+C
wait
