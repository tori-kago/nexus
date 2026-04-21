# Nexus 系統架構報告 (v3.2 - Persistent & Resilient Memory)

本文件描述了 Nexus 最新 (v3.2) 的實作架構，特別強調了「長期記憶的新陳代謝」機制。

## 📊 當前系統架構圖 (2026-04-21)

```mermaid
graph TD
    subgraph "接入層 (Client Interface)"
        Gateway["Gateway<br/>(src/gateway/main.py)"]
        Interactive_CLI["Interactive CLI<br/>(src/agent/cli_interactive.py)"]
    end

    subgraph "核心控制層 (Nexus Orchestrator)"
        Flow_Manager["NexusOrchestrator<br/>(src/core/orchestrator.py)"]
        Session_Manager["Session Manager<br/>(Rolling Context Window)"]
        Protocols["Protocols & Enums<br/>(src/core/protocols.py)"]
    end

    subgraph "適配器層 (Adapter Layer - Schema-driven)"
        Brain_Adapter["GeminiCLIBrainAdapter<br/>(src/adapters/brain/gemini_cli_adapter.py)"]
        Memory_Adapter["VaultAdapter 2.1<br/>(src/adapters/memory/vault_adapter.py)"]
        Tool_Adapter["PythonToolAdapter 2.1<br/>(src/adapters/tool/python_tool_adapter.py)"]
    end

    subgraph "外部服務層 (External Services & Skills)"
        Gemini_CLI[("Gemini CLI Tool<br/>(Native Command)")]
        Vault_Storage[("Local Markdown Files<br/>(src/brain/vault/)")]
        Base_Skills["Base Skills<br/>(File System / Time / System)"]
    end

    %% 請求流向 (WebSocket/REST)
    Interactive_CLI <-->|WebSocket| Gateway
    Gateway -- "Manage History" --> Session_Manager
    Session_Manager -- "Context Assembly" --> Flow_Manager
    
    %% 核心呼叫 Adapters
    Flow_Manager <--> Protocols
    Flow_Manager -- "Auto-Context" --> Memory_Adapter
    Flow_Manager -- "Action Trigger" --> Tool_Adapter
    Flow_Manager -- "Thought" --> Brain_Adapter

    %% 記憶消化流程 (LCM)
    Session_Manager -- "Trigger Digestion (Background)" --> Memory_Adapter
    Memory_Adapter -- "Write Digest" --> Vault_Storage

    %% Adapters 呼叫外部
    Brain_Adapter <-->|Subprocess| Gemini_CLI
    Memory_Adapter <-->|FS API| Vault_Storage
    Tool_Adapter <-->|Function Register| Base_Skills
```

## 🔍 架構關鍵特徵

### 1. 記憶新陳代謝 (Memory Metabolism)
*   **會話滾動 (Rolling Window)**：Gateway 自動管理 Context 長度，防止 Token 爆炸。
*   **非同步消化 (Async Digestion)**：當對話累積到一定程度時，Orchestrator 會在背景發起「摘要任務」，將即時對話轉化為長期記憶條目 (`memory.md`)。

### 2. 主動上下文拼裝 (Auto-Context)
*   大腦在開口前就已經預載了 `soul.md`、`user.md` 與近期 `memory.md` 片段。
*   具備 **降級機制 (Graceful Degradation)**，當檔案讀取失敗時會自動提供「預設性格」。

### 3. 工具適配 2.1
*   具備自動推導 Schema 的能力，讓大腦能在 Prompt 中看到每個工具的用途與參數規範。
