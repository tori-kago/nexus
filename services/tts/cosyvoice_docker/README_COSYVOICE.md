# 🎙️ CosyVoice 300M 部署指南 (穩定版)

我們切換到了目前 Docker Hub 上最受歡迎的社群鏡像 **neosun/cosyvoice**。這個鏡像包含了完整的 WebUI 與 API，且通常是公開訪問的，不需要 `docker login`。

## 🛠️ 快速啟動

### 1. 進入部署目錄
```bash
cd services/tts/cosyvoice_docker
```

### 2. 啟動容器
```bash
docker-compose up -d
```
*註：如果拉取依然顯示 denied，可能是您的 Docker Client 快取了錯誤的憑證。請嘗試執行 `docker logout` 後再拉取。*

## 🧪 測試流程

1. **開啟 WebUI**: 瀏覽器訪問 `http://localhost:50000` (對應容器內的 8188 埠)。
2. **API 測試**: 
   此鏡像支援 OpenAI 相容接口，您可以使用以下指令測試：
   ```bash
   curl -X POST http://localhost:50000/v1/audio/speech \
        -H "Content-Type: application/json" \
        -d '{"model": "cosyvoice", "input": "你好，我是 Nexus。", "voice": "default"}' \
        --output test.mp3
   ```

## 📊 效能與限制
- **Mac 支援**: 此鏡像在 Mac 上會以 CPU 運行。
- **記憶體**: 已設定 8GB 限制。

---
Nexus 語音引擎切換至 neosun 穩定版。🚀


