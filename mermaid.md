graph TD
    subgraph "接入層 (Client Interface)"
        Gateway["API Gateway<br/>(REST/WebSocket/Redis Bus)"]
    end

    subgraph "核心控制層 (Nexus Orchestrator)"
        Flow_Manager["Flow Manager<br/>(工作流與狀態引擎)"]
    end

    subgraph "適配器層 (Adapter Layer - API 轉換與隔離)"
        Brain_Adapter["Brain Adapter<br/>(LLM 介面實作)"]
        Memory_Adapter["Memory Adapter<br/>(Context/DB 介面實作)"]
        Tool_Adapter["Tool Adapter<br/>(技能/工具介面實作)"]
        Media_Adapter["Media Adapter<br/>(STT/TTS 介面實作)"]
    end

    subgraph "外部服務層 (External Services / APIs)"
        LLM_Services[("LLM Providers<br/>(OpenAI/Claude/Local)")]
        DB_Services[("Databases<br/>(SQLite/VectorDB)")]
        Skill_Workers["Skill Workers<br/>(獨立工具執行環境)"]
        Media_Services["Media Services<br/>(Azure/Local STT & TTS)"]
    end

    %% 請求流向
    Gateway -->|標準化事件/請求| Flow_Manager
    
    %% 核心呼叫 Adapters
    Flow_Manager <-->|統一內部介面| Brain_Adapter
    Flow_Manager <-->|統一內部介面| Memory_Adapter
    Flow_Manager <-->|統一內部介面| Tool_Adapter
    Flow_Manager <-->|統一內部介面| Media_Adapter

    %% Adapters 呼叫外部 API
    Brain_Adapter <-->|REST/gRPC/SDK| LLM_Services
    Memory_Adapter <-->|SQL/REST| DB_Services
    Tool_Adapter <-->|REST/Message Queue| Skill_Workers
    Media_Adapter <-->|REST/WebSocket| Media_Services