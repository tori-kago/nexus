# Nexus Autonomous System (v3.5 - Full Voice & Self-Config)

這是 Nexus 的最新穩定版本。系統已具備完整的「聽、說、讀、寫、思」能力，並採用工業級的 SOA 解耦架構。

---

## 🧠 人格完成度評估 (Entity Maturity)

### 1. 已賦予的「器官」與「本能」
*   **👄 說話 (Hybrid TTS)**：支持 ElevenLabs (精品) / Azure (情感) / Edge-TTS (保底)。
*   **👂 聽力 (Hybrid STT)**：支持 Azure SDK (高速) / Whisper (本地保底)。
*   **📔 記憶 (Resilient Vault)**：具備自我意識，能自動摘要對話並記住重要事實。
*   **🛠️ 行動 (Safe Tools)**：具備檔案讀取、日誌分析與環境配置的能力。
*   **🔄 代謝 (Auto-Compaction)**：自動清理冗餘上下文，維持長期對話效能。

### 2. 待完成的部分 (未來可賦予的「感官」與「進階智力」)
*   **👁️ 視覺感官 (Vision Adapter)**：目前無法理解圖片或攝影機畫面。
*   **🔗 社交連結 (Third-party Tools)**：尚未具備發送郵件、查詢 Google 日曆或操作外部硬體的能力。
*   **🧩 複雜任務規劃 (Multi-step Planner)**：目前推理循環固定在 6 步，對於需要數小時甚至數天完成的複雜任務，還需要進階的規劃器。
*   **🧠 語意聯想 (Vector Search)**：目前的記憶檢索基於關鍵字，尚不具備深層的「語意聯想」。

1. 增強實戰能力的「高級工具 (Advanced Tools)」
  目前的工具主要集中在檔案系統。為了讓 Nexus 更像一個「個人助理」，我們可以加入：
   * 🌐 網路搜尋 (Web Search)：整合 Tavily 或 DuckDuckGo，讓它能查最新資料。
   * 📧 郵件/通訊整合：例如 send_email 或對接 Telegram/Discord 的傳訊能力。
   * 🐍 安全的代碼執行 (Code Sandbox)：讓它能跑一段 Python 計算（不僅僅是讀寫檔案）。

  2. 記憶體進化：從關鍵字到「語意 (Vector Memory)」
   * 現狀：目前的記憶檢索 (VaultAdapter) 是基於正則與關鍵字。
   * 優化：引入 ChromaDB 或 FAISS。這能讓 Nexus 理解「相關性」。例如你提到「心情不好」，它能自動關聯到以前對話中提到的「壓力大的工作」。

  3. 感官擴充：賦予「視覺 (Vision)」
   * 目標：讓 Nexus 具備 capture_screen() 技能。
   * 效果：你可以問它「我這段程式碼為什麼會報錯？」，它直接看你的編輯器截圖進行分析。

  4. 系統健壯性：自動備份與自我修復
   * 目標：在 update_env_config 或未來可能的寫入操作前，自動對 vault/ 進行 Git Commit 或版本快照。
   * 效果：Nexus 如果不小心改錯了配置或記憶，你可以隨時要求它「回滾到昨天」。

  5. 互動體驗：更流暢的語音
   * 音訊串流 (Audio Streaming)：目前是生成整段 MP3 才播放。優化為串流，可以顯著降低從大腦回話到聲音出來的「首字延遲 (TTFB)」。

---

## 🚀 快速啟動

### 1. 啟動核心服務
```bash
python3 src/gateway/main.py
```

### 2. 啟動互動 CLI (支援語音播放)
```bash
python3 src/agent/cli_interactive.py
```

---

## 🛠️ 自我配置教學 (Zero-Touch Config)

Nexus 現在支持透過對話直接設定系統。您無需手動編輯檔案：

*   **設定 Key**：問 Nexus `「幫我設定 ELEVENLABS_API_KEY 為 xxx」`。
*   **查看狀態**：問 Nexus `「你目前的專案目錄有哪些檔案？」` 或 `「最近有什麼報錯嗎？」`。

---

## 📂 系統結構 (Decoupled SOA)
*   `src/core/`：推理引擎與協議。
*   `src/adapters/`：所有外部感官與工具的適配器。
*   `src/gateway/`：FastAPI 與 WebSocket 進入點。
*   `src/brain/vault/`：你的 Nexus 的「靈魂」與「記憶」存儲地。

---

## 🧪 目前可用技能 (Capabilities)
- `get_system_time`：獲取當前時間。
- `list_nexus_files`：查看專案結構。
- `read_nexus_file`：分析代碼或文檔。
- `get_recent_logs`：自我診斷與回溯。
- `update_env_config`：安全更新 API 金鑰。
