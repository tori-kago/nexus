# Nexus Voice Service (Fish Speech)

這是 Nexus 的發聲器官，採用 [Fish Speech](https://github.com/fishaudio/fish-speech) 技術。Fish Speech 提供了更現代的架構，能以極短的音訊樣本實現高品質的聲音克隆。

## 📂 目錄結構
- `fish-speech/`: Fish Speech 的官方核心程式碼。
- `reference_audio/`: 存放 Nexus 的參考音訊 (WAV 格式)。
- `fish_client.py`: 呼叫 Fish Speech API 的客戶端。

## 🚀 快速測試流程

### 1. 準備環境與模型
請確保已安裝 `hf` 工具並且有足夠空間（約 15GB）。
```bash
# 下載 S2-Pro 模型權重
hf download fishaudio/s2-pro --local-dir services/tts/fish-speech/checkpoints/s2-pro
```
hf download fishaudio/fish-speech-1.4 --local-dir services/tts/fish-speech/checkpoints/v1.4

```
brew install portaudio
```

### 2. 處理 3 分 44 秒長音檔 (重要)
**不建議直接將 3m44s 的完整音檔作為參考音訊。** 推論速度會非常慢。
- **建議做法**：從 3m44s 的音檔中，挑選一段 **15-30 秒**、語調自然、背景乾淨的人聲片段，命名為 `nexus_ref.wav`。
- **放置位置**：`services/tts/reference_audio/nexus_ref.wav`

### 3. 啟動 Fish Speech API Server
在 `services/tts/fish-speech/` 目錄下執行：
```bash
# 使用 MPS (Mac M1/M2/M3) - 建議加入 --half 節省記憶體
python tools/api_server.py \
    --llama-checkpoint-path checkpoints/s2-pro \
    --decoder-checkpoint-path checkpoints/s2-pro/codec.pth \
    --device mps \
    --half \
    --listen 127.0.0.1:9880
```

```
python tools/api_server.py \
    --llama-checkpoint-path checkpoints/v1.5 \
    --decoder-checkpoint-path checkpoints/v1.5/firefly-gan-vq-fsq-8x1024-21hz-generator.pth \
    --decoder-config-name v1.5_dac \
    --device mps \
    --listen 127.0.0.1:9880
```

### 4. 執行快速測試
啟動 Server 後，在另一個終端機執行 `fish_client.py` 進行測試：
```bash
# 修改 fish_client.py 內的文字或路徑後執行
python services/tts/fish_client.py
```

## 🎙️ Nexus 靈魂克隆流程
1. **音頻切片**：從長音檔中切出 20 秒精華。
2. **啟動 API**：按照上述步驟啟動 Fish Speech Server。
3. **測試合成**：使用 `fish_client.py` 驗證聲音是否滿意。
4. **正式部署**：將 API 位址與參考音檔路徑更新至 `src/exp/worker.py`。

---
Nexus 的聲音會比以前更動聽唷~ (｡･ω･｡)ﾉ♡
