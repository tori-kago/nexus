# Nexus LLaSA TTS Service (Windows / CUDA 版)

本服務專為擁有 NVIDIA GPU (如 RTX 4060 Ti) 的 Windows 設備設計，利用 CUDA 加速提供極速且高品質的中英雙語語音合成。

## 🚀 為什麼選擇 Windows 部署？
- **穩定性**：CUDA 生態系對 `transformers` 與 `xcodec2` 的支援遠比 macOS MPS 穩定。
- **效能**：RTX 40 系顯卡的 FP16 推理速度極快，首包延遲（Latency）極低。
- **顯存優勢**：3B 模型在 Windows CUDA 下約佔用 7GB 顯存，完美契合 8GB/16GB 顯卡。

---

## 🛠 安裝步驟 (Windows)

### 1. 準備環境
建議安裝 [Anaconda](https://www.anaconda.com/) 或 [Miniconda](https://docs.conda.io/projects/miniconda/en/latest/)。

```powershell
# 建立環境
conda create -n llasa python=3.10 -y
conda activate llasa
```

### 2. 安裝 CUDA 版 PyTorch
請確保你的 NVIDIA 驅動程式已更新。執行以下指令安裝支援 CUDA 12.1 的 PyTorch：
```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 3. 安裝核心依賴
```powershell
pip install fastapi uvicorn transformers accelerate librosa soundfile xcodec2 pydantic
```

### 4. 啟動伺服器
```powershell
python services/tts/llasa_win.py
```
伺服器將預設運行在 `http://0.0.0.0:9001`。

---

## 🔗 跨機連動 (Mac 呼叫 Windows)

為了讓你在 Mac 上的 Nexus 大腦能使用 Windows 的運算力，請按照以下步驟設定：

### 1. 獲取 Windows IP
在 Windows 終端機輸入 `ipconfig`，找到 `IPv4 地址` (例如 `192.168.1.100`)。

### 2. 修改 Mac 端設定
在 Mac 專案根目錄的 `.env` 檔案中，將 TTS URL 指向 Windows：
```bash
# Mac 端的 .env
LLASA_API_URL=http://192.168.1.100:9001/tts
```

### 3. 測試連線
在 Mac 終端機執行：
```bash
curl -X POST http://192.168.1.100:9001/tts -H "Content-Type: application/json" -d '{"text": "連線測試成功，這是來自 Windows 的語音。"}'
```

---

## 📂 檔案說明
- **`services/tts/llasa_win.py`**: 針對 Windows 優化的推理腳本，使用 `device_map="auto"` 自動管理顯存。
- **`services/tts/temp_outputs/`**: 生成的 `.wav` 音檔存放處。

## ⚠️ 注意事項
- **防火牆設定**：若 Mac 無法連線至 Windows，請檢查 Windows 防火牆是否允許 9001 端口的連入請求。
- **初次啟動**：首次執行會從 Hugging Face 下載約 6.5GB 的模型權重，請確保網路暢通。
