# Nexus Autonomous System (v4.3 - Unified Presence)

Nexus 是一個跨平台的自主 AI 生命體。它現在能同時存在於您的終端機、Telegram 與 Discord 中，並共享同一個靈魂與記憶。

---

## 🎭 多平台能力矩陣 (Feature Matrix)

| 功能 | CLI (終端機) | Telegram Bot | Discord Bot |
| :--- | :---: | :---: | :---: |
| **文字交流** | ✅ | ✅ | ✅ |
| **語音聽力 (STT)** | ❌ (待開發) | ✅ (語音訊息) | ✅ (附件) |
| **語音說話 (TTS)** | ✅ (自動播放) | ✅ (語音訊息) | ✅ (音訊附件) |
| **主動通知 (Push)** | ✅ (連線時) | ✅ (全時) | ✅ (全時) |
| **會話持久化** | ✅ | ✅ | ✅ |

---

## 🚀 快速啟動指南

### 1. 啟動後端核心 (必須)
```bash
python3 src/gateway/main.py
```

### 2. 選擇您的入口 (可多選)
*   **終端機互動**：`python3 src/agent/cli_interactive.py`
*   **Telegram 機器人**：`python3 src/agent/tg_bot.py`
*   **Discord 機器人**：`python3 src/agent/discord_bot.py`

---

## 🛠️ 自我配置與控制 (Zero-Touch)

您現在可以透過任何平台對 Nexus 下達「系統指令」：
*   **設定 API Key**：`「幫我設定 TELEGRAM_BOT_TOKEN 為 xxx」`。
*   **重置大腦**：`「Nexus，重置對話上下文」`（這會清空短期記憶但保留性格與長期事實）。
*   **回滾快照**：`「回滾到上一個系統快照」`（防範誤操作）。
*   **日誌省察**：`「看看最近 30 行日誌，有異常嗎？」`。

---

## 📂 專案結構
*   `src/core/`：推理引擎、持久化會話與協議。
*   `src/adapters/`：感官與工具箱。
*   `src/gateway/`：全時通知中心。
*   `src/agent/`：各平台客戶端 (CLI, TG, Discord)。
*   `src/brain/vault/`：存儲 soul.md, memory.md, logs 與 sessions.db。
