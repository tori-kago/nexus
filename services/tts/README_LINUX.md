# Nexus LLaSA TTS Service (macOS Optimized)

本服務是基於 [HKUSTAudio/LLaSA-3B](https://github.com/HKUSTAudio/LLaSA) 構建的 TTS 伺服器，針對 Apple Silicon (M1/M2/M3) 晶片的 **MPS (Metal Performance Shaders)** 進行了優化。

## 🌟 特色
- **輕量化**：顯存佔用 < 7GB，適合 16GB 以上記憶體的 Mac。
- **人性化**：中英雙語自然流暢，支援 Zero-shot 音色克隆。
- **快速整合**：符合 Nexus Unified Protocol 規範，可直接由 Expression Worker 調用。

## 🛠 安裝步驟

### 1. 建立虛擬環境
建議在 `services/tts` 目錄下建立專屬環境：
python>=3.9 <3.13
```bash
cd services/tts
python -m venv venv_llasa
source venv_llasa/bin/activate
```

### 2. 安裝依賴
```bash
pip install -r requirements_llasa.txt
```

### 3. 啟動伺服器
首次啟動會自動從 Hugging Face 下載 LLaSA-3B 模型與 XCodec2 編碼器（總計約 6.5GB）。
```bash
python llasa_server.py
```
伺服器將運行在 `http://0.0.0.0:9001`。

## 📡 API 使用說明

### TTS 生成
- **Endpoint**: `POST /tts`
- **Payload**:
```json
{
  "text": "你好 Nexus，這是 LLaSA 的聲音。",
  "prompt_text": "這裡放參考音檔的文字內容 (選填)",
  "prompt_wav_path": "這裡放參考音檔的本地路徑 (選填)"
}
```

## 🔗 Nexus 整合
若要讓 Nexus 大腦的回覆使用此語音，請確保 `src/exp/worker.py` 中的 `LLASA_API_URL` 指向 `http://localhost:9001/tts`。
