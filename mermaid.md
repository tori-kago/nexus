graph TD
    subgraph "接入層 (Interface)"
        API_Gateway["Gateway<br/>(FastAPI/WebSocket)"]
        Interactive_CLI["Interactive CLI<br/>(Voice/Text Client)"]
    end

    subgraph "核心控制層 (Nexus Orchestrator)"
        Flow_Manager["Orchestrator<br/>(Reasoning Loop)"]
        Session_Manager["Session Manager<br/>(Context Compaction)"]
    end

    subgraph "適配器層 (Hybrid Adapters)"
        Brain_Adapter["Brain Adapter<br/>(Gemini CLI)"]
        Memory_Adapter["Vault Adapter<br/>(Markdown DB)"]
        Tool_Adapter["Tool Adapter<br/>(Schema-driven)"]
        Media_Adapter["Media Adapter<br/>(Hybrid STT/TTS)"]
    end

    subgraph "外部服務 (External APIs & Files)"
        LLM_Services[("Gemini API")]
        Vault_Files[("Soul/User/Memory/Logs")]
        Speech_Services[("Azure/ElevenLabs/Whisper")]
        Base_Skills["Core Python Skills"]
    end

    %% 資料流
    Interactive_CLI <--> API_Gateway
    API_Gateway <--> Flow_Manager
    
    Flow_Manager <--> Session_Manager
    Flow_Manager <--> Brain_Adapter
    Flow_Manager <--> Memory_Adapter
    Flow_Manager <--> Tool_Adapter
    Flow_Manager <--> Media_Adapter

    Memory_Adapter --- Vault_Files
    Tool_Adapter --- Base_Skills
    Media_Adapter --- Speech_Services
