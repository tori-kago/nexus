# Nexus: Distributed AI Agent System

Nexus 是一個基於 Redis Pub/Sub 匯流排架構的 AI 代理系統，目前已完成 **Phase 0 (核心骨架)**、**Phase 1 (終端 Console)** 與 **Phase 2 (文件驅動大腦)**。

## 🚀 全系統啟動流程 (P0 + P1 + P2)

本系統目前採用 **Nexus Unified Protocol (NUP) v1.0** 進行組件間溝通。該協定確保了全鏈路追蹤 (Traceability) 與無靜默回覆 (No Silent Reply)。

### 1. 基礎設施 (Redis Bus)
```bash
docker-compose -f infra/docker-compose.yml up -d
```

### 2. 核心網關 (Gateway)
```bash
python -m src.gateway.main
```

### 3. 大腦後端 (Brain Worker)
```bash
python -m src.brain.worker
```

### 4. 表達引擎 (Expression Engine)
```bash
python -m src.exp.worker
```

### 5. 語音轉譯 (STT Worker - New)
```bash
python -m src.stt.worker
```

### 6. 終端與監控 (Optional)
- **交談終端 (PC Agent)**: `python -m src.agent.cli_console`
- **Telegram Bot (New)**: 
  1. 在根目錄建立 `.env` 並填入 `TELEGRAM_TOKEN` 與 `TELEGRAM_CHAT_ID`。
  2. 執行 `python -m src.agent.tg_bot`
- **全域監控 (Monitor)**: `python -m src.monitor.cli_monitor` (現支援 NUP 瀑布流視覺化)

---

## 🧪 協定與功能測試 (NUP v1.0)
...
#### 3. 語音輸入聯動 (STT Worker)
- **測試動作**: 對 Telegram Bot 發送一段語音訊息。
- **驗收點**: 
    - 觀察 `Monitor`: 應先出現 `nexus.audio_in` (包含檔案路徑)，隨後轉譯出 `nexus.input` 文字。
    - 大腦應根據轉譯出的文字內容進行回覆。

我們提供了一個自動化測試指令碼來驗證通訊協定的合規性：
```bash
python -m tests.test_nup_flow
```

### ✅ 測試驗收點

#### 1. 全鏈路追蹤 (Traceability)
- **驗收點**: 測試輸出應顯示 `input`, `thought`, `text` 訊息均攜帶相同的 `trace_id`。

#### 2. 無靜默回覆 (No Silent Reply)
- **驗收點**: 在大腦產生最終回覆前，應至少收到一條 `type: thought` 且 `state: thinking` 的訊息，確保處理進度可視化。

#### 3. 自動金庫反射 (Vault Reflection)
- **測試動作**: 在對話中使用 `[REFLECT:USER] 喜歡測試。`
- **驗收點**: 
    - 觀察 `Monitor`: 應出現 `nexus.thought` 頻道訊息，顯示 `state: reflecting`。
    - 檢查檔案: 開啟 `src/brain/vault/identity/user.md`，確認「溝通偏好」區塊是否自動新增了紀錄。

#### 2. 表達引擎 (Expression Engine)
- **測試動作**: 要求 Nexus 展示情緒（例如：(微笑) 或是 [思考]）。
- **驗收點**: 
    - 觀察 `Monitor`: 當回覆包含標籤時，`nexus.command` 頻道應同步發出 `{"type": "expression", "value": "..."}`。

---

## 🚀 已實作：Phase 4 (多端肉體) - Telegram Bot
目前已完成 `src/agent/tg_bot.py` 實作。
- **測試方式**: 啟動 Bot 後，從手機發送訊息，觀察 `Monitor` 是否出現 `platform: telegram` 標籤。
- **多端同步**: 確保在 Telegram 的對話內容能同步出現在已啟動的 `cli_console` 中（基於 `session_id` 廣播）。


