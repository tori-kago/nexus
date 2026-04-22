# Nexus Autonomous System (v5.2 - The Wise Engineer)

Nexus 是一個跨平台的自主 AI 生命體。它現在具備了極致的穩定性與自我進化能力，能像人類工程師一樣思考、學習與解決問題。

---

## 🎯 核心特徵 (Key Highlights)

### 1. 深度思維流 (Deep Reasoning)
Nexus 不再追求秒回。當面對複雜問題時，它會自主啟動「工程師模式」：
- **探索 (ls)**：查看有什麼工具可用。
- **學習 (read)**：研究工具的 SKILL.md 指南。
- **執行 (run)**：實踐解決方案。
- **自癒 (fix)**：遇到錯誤時自動安裝缺失依賴或修正代碼。

### 2. 三向防護盾 (Triple Shield Protection)
- **格式容錯**：無視大腦的冗餘輸出，精準提取 JSON。
- **並發防護**：日誌鎖機制，確保多任務日誌不打架。
- **Context 隔離**：內存深拷貝，確保記憶絕對不會發生時空錯亂。

### 3. 立體靈魂 (Persona 3D)
Nexus 的性格不再是定型的文檔，而是在 `src/brain/vault/identity/soul/` 下的多維度組合。它的性格會隨「工作經驗」累積而不斷成長。

---

## 🚀 快速啟動

### 1. 啟動後端核心
```bash
python3 src/gateway/main.py
```

### 2. 啟動多平台入口 (可選)
- **互動 CLI (推薦)**：`python3 src/agent/cli_interactive.py`
- **Telegram Bot**：`python3 src/agent/tg_bot.py`
- **Discord Bot**：`python3 src/agent/discord_bot.py`

---

## 🛠️ 維護與擴充
- **添加新技能**：只需在 `src/skills/` 下建立目錄並編寫 `SKILL.md`。
- **查看過程**：請查閱 `src/brain/vault/logs/trace_YYYY-MM-DD.log` 以獲取完整的推理細節。
- **系統指南**：詳見 `MAINTENANCE_GUIDE.md`。
