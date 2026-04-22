#!/bin/bash

# --- Nexus 一鍵啟動腳本 (增強版) ---

export PYTHONPATH=$PYTHONPATH:$(pwd)
trap "kill 0" EXIT

echo "---------------------------------------"
echo "[1/3] 正在啟動 Gateway (大腦)..."
echo "提示: 首次啟動可能需要幾秒鐘來加載語音模型。"
python -m src.gateway.main &

# 檢查 Gateway 是否已啟動 (檢測 8000 端口)
MAX_RETRIES=30
COUNT=0
while ! nc -z localhost 8000; do   
  sleep 1
  COUNT=$((COUNT+1))
  if [ $COUNT -ge $MAX_RETRIES ]; then
    echo "錯誤: Gateway 啟動超時，請檢查日誌是否有報錯。"
    exit 1
  fi
done

echo "OK! Gateway 已就緒。"
echo "---------------------------------------"

echo "[2/3] 正在啟動 Telegram Bot..."
python -m src.agent.tg_bot &

echo "[3/3] 正在啟動 Discord Bot..."
# 檢查是否有設置 Discord Token，避免崩潰
if grep -q "your_discord_token_here" .env; then
    echo "跳過 Discord Bot (Token 尚未設置)。"
else
    python -m src.agent.discord_bot &
fi

echo "---------------------------------------"
echo "Nexus 系統已全部啟動！"
echo "- Web 入口: http://localhost:8000"
echo "- 按 Ctrl+C 可同時關閉所有服務。"
echo "---------------------------------------"

wait
