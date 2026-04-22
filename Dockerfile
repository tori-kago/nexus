# 使用 Python 3.11 官方輕量鏡像
FROM python:3.11-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴 (音訊處理、編譯基礎工具、以及 Git 快照支援)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件並安裝 Python 庫
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案代碼
COPY . .

# 預先創建必要的資料夾
RUN mkdir -p src/brain/vault/temp_tts src/brain/vault/cache_tts src/brain/vault/logs

# 暴露 FastAPI 端口
EXPOSE 8000

# 設置環境變數，確保 Python 能找到 src 模組
ENV PYTHONPATH=/app

# 使用模組化方式啟動，這能確保內部的相對/絕對匯入正確
CMD ["python", "-m", "src.gateway.main"]
