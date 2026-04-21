# Nexus 系統架構報告 (v3.5 - Full Sensory SOA)

本文件描述了 Nexus 最新 (v3.5) 的實作架構。目前系統已達成「全感官整合」與「自主配置」的完整閉環。

## 📊 當前系統架構圖 (2026-04-21)

```mermaid
graph TD
    subgraph "接入層 (Client Interface)"
        Gateway["Gateway<br/>(src/gateway/main.py)"]
        Interactive_CLI["Interactive Voice CLI<br/>(src/agent/cli_interactive.py)"]
    end

    subgraph "核心控制層 (Nexus Orchestrator)"
        Flow_Manager["NexusOrchestrator<br/>(src/core/orchestrator.py)"]
        Session_Manager["Session & Context Window<br/>(History Management)"]
        Protocols["Protocols & Contracts<br/>(src/core/protocols.py)"]
    end

    subgraph "適配器層 (Adapter Layer - Resilient)"
        Brain_Adapter["GeminiCLIBrainAdapter<br/>(Native CLI Wrapper)"]
        Memory_Adapter["VaultAdapter 2.1<br/>(Resilient Markdown DB)"]
        Tool_Adapter["PythonToolAdapter 2.2<br/>(Type-safe & Schema-driven)"]
        STT_Adapter["HybridSTTAdapter<br/>(Azure SDK -> Whisper)"]
        TTS_Adapter["HybridTTSAdapter<br/>(ElevenLabs -> Azure -> Edge)"]
    end

    subgraph "外部服務層 (External Services)"
        LLM_Provider[("Gemini 1.5 Pro/Flash")]
        Vault_Storage[("Local Markdown Files")]
        Cloud_APIs[("Azure / ElevenLabs / Edge")]
        Base_Skills["Base Skills<br/>(FS / Logs / Self-Config)"]
    end

    %% 請求流向 (WebSocket/REST)
    Interactive_CLI <-->|Text & Audio Stream| Gateway
    Gateway -- "Injection" --> Flow_Manager
    
    %% 核心呼叫 Adapters
    Flow_Manager <--> Protocols
    Flow_Manager -- "Action" --> Tool_Adapter
    Flow_Manager -- "Sense" --> STT_Adapter
    Flow_Manager -- "Voice" --> TTS_Adapter
    Flow_Manager -- "History" --> Memory_Adapter

    %% 關鍵流程
    Tool_Adapter -- "Auto-Config" --> Vault_Storage
    Memory_Adapter -- "LCM Digestion" --> Vault_Storage
```

## 🔍 架構關鍵特徵

### 1. 多層降級感官 (Hybrid Sensory Tiers)
*   **STT (聽力)**: Azure SDK (雲端) 優先 -> Whisper (本地) 保底。
*   **TTS (說話)**: ElevenLabs -> Azure -> Edge-TTS (免費高品質)。
*   這確保了系統在無網路或無預算的情況下，依然能維持基礎的互動能力。

### 2. 工業級工具鏈 (Toolbox 2.2)
*   **強型別校驗**: 使用 Pydantic 在執行前驗證 LLM 傳入的參數。
*   **自我修正**: 當參數錯誤時，適配器會提供清晰的錯誤說明，引導大腦自動修正指令。

### 3. 自我配置能力 (Self-Configuring)
*   Nexus 具備受控的 `.env` 寫入權限。用戶可以直接對話設定 API KEY，由 Nexus 完成持久化。

### 4. 記憶消化 (Memory Metabolism)
*   具備自動摘要長對話並寫入 `memory.md` 的能力，防止會話過載並實現長期學習。
