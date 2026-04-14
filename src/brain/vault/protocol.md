# Nexus 統一通訊協定 (Nexus Unified Protocol, NUP) v1.0

## 1. 核心設計理念
- **全鏈路追蹤 (Traceability)**：每一條輸入訊息都必須產生一個唯一的 `trace_id`，所有後續產生的思考、文字與指令都必須攜帶此 ID。
- **無靜默回覆 (No Silent Reply)**：系統處理過程中的每一個關鍵節點（如：開始思考、反思中、完成處理）都必須發布訊息至對應頻道，確保 Monitor 能即時掌握進度。
- **異步解耦 (Asynchronous)**：組件間透過 Redis Pub/Sub 進行非阻塞通訊。

---

## 2. 訊息封包結構 (Envelope)
所有透過 `MessageBus` 傳遞的 JSON 訊息必須符合以下基礎結構：

```json
{
  "id": "uuid-v4",               // 訊息本身的唯一標籤
  "timestamp": "ISO-8601",      // 發生時間 (例如: 2026-04-14T10:00:00Z)
  "source": "string",            // 發送源 (例如: gateway:tg, brain:langgraph, exp:tts)
  "type": "string",              // 訊息類型 (input | thought | text | command | system)
  "trace_id": "uuid-v4",         // 原始輸入引發的追蹤 ID (關鍵！)
  "session_id": "string",        // 會話 ID (用於 LangGraph 記憶檢索)
  "payload": {},                 // 具體內容
  "metadata": {                  // 選項元數據
    "silent": false,             // 是否為隱藏訊息 (僅 Monitor 可見)
    "user_id": "string"          // 用戶識別碼
  }
}
```

---

## 3. 頻道規範與 Payload 格式

### 3.1 `nexus.input` (外部輸入)
由 Gateway 或 Client 發出，代表系統接收到新指令。
- **Payload 結構**:
  ```json
  {
    "content": "妳好，Nexus",      // 純文字輸入
    "platform": "telegram",       // 來源平台 (telegram | agent | web)
    "raw_data": {}                // 原始平台資料 (選填)
  }
  ```

### 3.2 `nexus.thought` (內部思考)
由 Brain 發出，展示推理過程。落實「無靜默回覆」的核心頻道。
- **Payload 結構**:
  ```json
  {
    "state": "thinking",          // 當前狀態 (thinking | reflecting | searching)
    "reasoning": "用戶詢問天氣，我正在檢索記憶...", // 推理描述
    "context_refs": ["memory.md"] // 引用到的 Vault 檔案
  }
  ```

### 3.3 `nexus.text` (對話回覆)
由 Brain 或 Expression Engine 發出，最終呈現給用戶的文字與情緒。
- **Payload 結構**:
  ```json
  {
    "content": "你好，我是 Nexus。", 
    "emotion": "happy",           // 情緒標籤 (neutral | happy | sad | angry | focused)
    "tts_url": "http://..."       // (選填) 語音檔案連結
  }
  ```

### 3.4 `nexus.command` (系統指令)
由 Brain 發出，驅動終端（如 Godot 或 PC Agent）執行特定動作。
- **Payload 結構**:
  ```json
  {
    "action": "play_animation",   // 動作名稱
    "params": {                   // 動作參數
      "name": "wave",
      "speed": 1.2
    }
  }
  ```

---

## 4. 處理流程規範 (Sequence Requirement)
1. **Input Stage**: Gateway 接收請求 -> 產生 `trace_id` -> 發布至 `nexus.input`。
2. **Thought Stage**: Brain 監聽到 Input -> 立即發布一條 `thought` (state=thinking) -> 開始計算。
3. **Action Stage**: Brain 計算完成 -> 若有 Reflection 則發布 `thought` (state=reflecting) -> 同時發布 `nexus.text` 與 `nexus.command`。
4. **Sync Stage**: Gateway 監聽到 Text -> 透過 WebSocket/Webhook 回傳給終端。

---

## 5. 異常處理
- **Timeout**: 若 30 秒內未完成處理，Brain 應發布 `type: "system"` 訊息標註 `trace_id` 已超時。
- **Filter**: 若觸發內容審查，Brain 必須發布 `silent: true` 的 `thought` 訊息說明過濾原因，而不僅僅是保持沉默。
