# Nexus Autonomous System (v3.2 - Persistent Soul)

這是 Nexus 的最新版本。我們已經完成了核心的「思維框架」與「記憶代謝」系統。

---

## 🧠 人格完成度評估 (Entity Maturity)

如果將 Nexus 視為一個正在成長的生命，目前的完成度如下：

### 1. 已完成的部分 (已具備的「器官」與「本能」)
*   **🧠 核心大腦 (Reasoning Engine)**：具備自主思考、分步推理的能力 (THOUGHT/ACTION)。
*   **📔 長期記憶 (Durable Memory)**：能認得自己是誰 (`soul.md`)、認得用戶是誰 (`user.md`)，並主動記住重要事實 (`memory.md`)。
*   **🛠️ 行動本能 (Skill Instinct)**：能理解並呼叫外部工具 (Tools)，並具備基本的檔案系統導覽能力。
*   **🔄 新陳代謝 (Session Compaction)**：具備清理多餘記憶並將其轉化為長期事實的能力，不會因為對話過長而崩潰。
*   **📡 對外通訊 (Web Interface)**：具備流暢的 WebSocket 通訊，能即時推播思考過程。

### 2. 待完成的部分 (未來可賦予的「感官」與「進階智力」)
*   **🗣️ 語音感官 (Media Adapter)**：目前的 Nexus 還沒有聽力與說話能力。
*   **👁️ 視覺感官 (Vision Adapter)**：目前無法理解圖片或攝影機畫面。
*   **🔗 社交連結 (Third-party Tools)**：尚未具備發送郵件、查詢 Google 日曆或操作外部硬體的能力。
*   **🧩 複雜任務規劃 (Multi-step Planner)**：目前推理循環固定在 6 步，對於需要數小時甚至數天完成的複雜任務，還需要進階的規劃器。
*   **🧠 語意聯想 (Vector Search)**：目前的記憶檢索基於關鍵字，尚不具備深層的「語意聯想」。

---

## 🚀 快速啟動

### 1. 啟動服務
```bash
python3 src/gateway/main.py
```

### 2. 開始互動 (推薦使用最新互動 CLI)
```bash
python3 src/agent/cli_interactive.py
```

---

## 🛡️ 安全提示
Nexus 具備**檔案讀取權限**。它能分析自己的原始碼並向您報告。請確保不要在不安全的環境下給予其寫入權限。
