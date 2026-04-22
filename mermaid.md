graph TD
    subgraph "【接入層】(Sensory Input)"
        API_Gateway["Notification Hub<br/>(Gateway v5.2)"]
        CLI["Interactive CLI"]
        TG["Telegram Bot"]
        DC["Discord Bot"]
    end

    subgraph "【控制與防護層】(Nexus Core)"
        Flow_Manager["Orchestrator<br/>(Deep Thought Flow)"]
        Shields["Triple Shield<br/>(Lock/Copy/Parser)"]
        Session_DB[("SQLite Session DB")]
    end

    subgraph "【適配層】(Adapters)"
        Brain_Adapter["Brain Adapter<br/>(JSON Parser)"]
        Memory_Adapter["Vault Adapter<br/>(Multi-MD soul)"]
        Media_Adapter["Media Adapter<br/>(Hybrid Audio)"]
        Tool_Adapter["Tool Adapter<br/>(Shell/Skill)"]
    end

    subgraph "【數據與日誌】(Persistent Data)"
        Trace_Log[("Trace Logs<br/>(.log)")]
        Knowledge_Log[("Knowledge Logs<br/>(.md)")]
        Vault_Soul["Identity Files<br/>(soul/*.md)"]
    end

    %% 資料流
    CLI <--> API_Gateway
    TG <--> API_Gateway
    DC <--> API_Gateway
    
    API_Gateway <--> Shields
    Shields <--> Flow_Manager
    API_Gateway -- "Persist" --> Session_DB
    
    Flow_Manager <--> Brain_Adapter
    Flow_Manager <--> Memory_Adapter
    Flow_Manager <--> Media_Adapter
    Flow_Manager <--> Tool_Adapter

    %% 日誌分離
    Flow_Manager -- "Technics" --> Trace_Log
    Flow_Manager -- "Knowledge" --> Knowledge_Log
    Memory_Adapter --- Vault_Soul
    
    %% 安全
    Flow_Manager -- "Auto Snapshot" --> Git[("Git Resilience")]
