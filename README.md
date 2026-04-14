# Nexus: Distributed AI Agent System

Nexus 是一個基於 Redis Pub/Sub 匯流排架構的 AI 代理系統，目前已完成 **Phase 0 (核心骨架)**、**Phase 1 (終端 Console)** 與 **Phase 2 (文件驅動大腦)**。

## 🚀 全系統啟動流程 (P0 + P1 + P2)

為了讓 Nexus 正常運作，請依序在不同的終端視窗啟動以下服務：

### 1. 基礎設施 (Redis Bus)
```bash
docker-compose -f infra/docker-compose.yml up -d
```

### 2. 核心網關 (Gateway) - 提供 WebSocket 連線
```bash
python -m src.gateway.main
```

### 3. 大腦後端 (Brain Worker) - 處理思考邏輯
```bash
python -m src.brain.worker
```

### 4. 交談終端 (PC Agent) - 使用者介面
```bash
python -m src.agent.cli_console
```

> **提示**：您可以額外啟動 `python -m src.monitor.cli_monitor` 來觀察所有底層訊息流。

### 3. 驗證重點
- **性格 (Soul)**: 觀察 Nexus 是否符合 `src/brain/vault/identity/soul.md` 中設定的冷靜且精煉的語調。
- **記憶 (Memory)**: 詢問 Nexus 關於專案目前的狀態，看它是否能正確讀取 `src/brain/vault/context/memory.md`。
- **自動日誌 (Logs)**: 檢查 `src/brain/vault/logs/` 目錄，確認當前的對話是否已自動同步寫入 Markdown 日誌。
- **反思 (Reflection)**: 嘗試告訴 Nexus 一些關於你的新偏好，觀察回覆中是否出現 `[REFLECT]` 標籤。

## 🛠️ Phase 2 & 3 功能驗收 (最新更新)

除了原有的啟動步驟，請額外啟動 **表達引擎 (Expression Engine)** 以支援情緒指令提取：
```bash
python -m src.exp.worker
```

### ✅ 最新驗收點

#### 1. 自動金庫反射 (Vault Reflection)
- **測試動作**: 在 Console 對 Nexus 說：「我最近開始學習 Rust 語言，以後請多用 Rust 的例子說明。」
- **驗收點**: 
    - 觀察 `Monitor`: 應出現 `nexus.thought` 頻道訊息，顯示 `[Brain] Reflecting User Fact...`。
    - 檢查檔案: 開啟 `src/brain/vault/identity/user.md`，確認「溝通偏好」區塊是否自動新增了關於 Rust 的紀錄。

#### 2. 表達引擎 (Expression Engine)
- **測試動作**: 要求 Nexus 展示情緒（例如：(微笑) 或是 [思考]）。
- **驗收點**: 
    - 觀察 `Monitor`: 當回覆包含標籤時，`nexus.command` 頻道應同步發出 `{"type": "expression", "value": "..."}`。

---

## 🚀 未來展望：Phase 4 (多端肉體)
目前的開發重點在於實作 `src/agent/tg_bot.py` 與整合 Telegram。


