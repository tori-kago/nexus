# Nexus 系統維護與相容性指南 (Maintenance & Compatibility Guide)

當您未來需要對 Nexus 系統進行功能擴充、修改或架構調整時，請務必遵循此指南進行相容性檢查，以確保系統的「多平台」、「多感官」與「自主學習」能力不被破壞。

---

## 1. 核心修改的相容性檢查矩陣

當您修改了以下模塊時，請連帶檢查對應的受影響組件：

### A. 修改了 `src/core/orchestrator.py` (大腦調度器)
*   **受影響模塊**：`GeminiCLIBrainAdapter` (JSON 解析), `gateway/main.py` (心跳循環與參數注入), 所有的 `src/skills/`。
*   **檢查清單**：
    1.  **JSON 輸出相容性**：確保 System Prompt 依然強制大腦輸出 `{"thought": "...", "action_type": "...", "action_param": "..."}` 格式。
    2.  **Context 獨立性 (防護 C)**：確保沒有移除 `safe_history = copy.deepcopy(history)` 邏輯，否則會導致並發時的記憶錯亂。
    3.  **Trace 日誌 (透明度)**：確認 `await self.memory.log_trace(...)` 是否正確捕獲了每一步，這是 Debug 的唯一真理。
    4.  **日誌鎖 (防護 B)**：確認 `trace_lock` 機制依然存在，防止多任務並行導致日誌 Step 交錯。

### B. 修改了 `src/gateway/main.py` (網路與事件中心)
*   **受影響模塊**：`tg_bot.py`, `discord_bot.py`, `cli_interactive.py`, `session_store.py`。
*   **檢查清單**：
    1.  **WebSocket 狀態防護**：確保發送任何訊息前，都有檢查 `client_state == "CONNECTED"`。
    2.  **錯誤隔離 (Sandbox)**：確保 `orchestrator.run()` 位於子 try-except 塊中，發生錯誤不應殺死主連線。
    3.  **心跳與主動推播**：確認 `heartbeat_loop` 是否在 `lifespan` 啟動時正確開啟。

### C. 修改了 `src/adapters/brain/gemini_cli_adapter.py` (解析層)
*   **檢查清單**：
    1.  **JSON 寬容解析 (防護 A)**：確保使用正則 `re.search(r'(\{.*\})', ...)` 提取 JSON，這能抵抗大腦在大括號外加廢話的干擾。

---

## 2. 關於 Identity 的動態更新 (自主學習)

Nexus 的「進化」發生在兩個關鍵時機，修改時需確保其連貫性：

1.  **工作時間 (09:00 - 11:00)**：心跳任務會發送 `[SYSTEM WORK]` 指令。
    *   **檢查**：大腦是否真的去 `ls src/skills/` 並將心得寫入 `growth.md`。
2.  **記憶消化 (Session Compaction)**：當 SQLite 中的歷史超過 14 條時觸發。
    *   **檢查**：大腦是否將琐事提煉成關鍵事實寫入 `memory.md`。

---

## 3. 日誌查閱與 Debug 指南

當系統行為異常（例如大腦不聽話）時：
1.  **優先看 Trace Log**：`src/brain/vault/logs/trace_YYYY-MM-DD.log`。
2.  **看 Observation**：觀察大腦是否因為 `run_shell` 報錯而陷入無限重試，或是參數格式損毀。
3.  **重置會話**：若歷史數據已損毀，對 Nexus 說 `「重置對話上下文」` 即可清空 SQLite 記憶並重新開始。
