graph TD
    subgraph "【接入層】(Sensory Input)"
        API_Gateway["Notification Hub<br/>(Gateway v4.3)"]
        CLI["Interactive CLI"]
        TG["Telegram Bot"]
        DC["Discord Bot"]
    end

    subgraph "【核心層】(Nexus Core)"
        Flow_Manager["Orchestrator<br/>(Reasoning Loop)"]
        Session_DB[("SQLite Session Store<br/>(Cross-platform)")]
    end

    subgraph "【適配層】(Adapters)"
        Brain_Adapter["Brain Adapter<br/>(Gemini CLI)"]
        Memory_Adapter["Vault Adapter<br/>(Markdown Storage)"]
        Media_Adapter["Media Adapter<br/>(Hybrid Audio)"]
        Tool_Adapter["Tool Adapter<br/>(Resilient Skills)"]
    end

    %% 資料流
    CLI <--> API_Gateway
    TG <--> API_Gateway
    DC <--> API_Gateway
    
    API_Gateway <--> Flow_Manager
    API_Gateway -- "Persist History" --> Session_DB
    
    Flow_Manager <--> Brain_Adapter
    Flow_Manager <--> Memory_Adapter
    Flow_Manager <--> Media_Adapter
    Flow_Manager <--> Tool_Adapter

    %% 衛生與安全
    Flow_Manager -- "Auto Snapshot" --> Git[("Git Resilience")]
