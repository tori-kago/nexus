graph TD
    subgraph "接入層 (Client Interface)"
        API_Gateway["API Gateway<br/>(REST/WebSocket)"]
    end

    subgraph "核心層 (Nexus Orchestrator)"
        Flow_Manager["Flow Manager<br/>(狀態與流程控制)"]
        Context_Engine["Context Engine<br/>(語境與記憶拼裝)"]
        Tool_Picker["Tool Picker<br/>(技能選取與分發)"]
    end

    subgraph "服務層 (External Services)"
        Brain_Adapter["Brain Adapter<br/>(LLM 接口)"]
        Memory_Service["Memory Service<br/>(SQLite/Vector DB)"]
        Skill_Runtime["Skill Runtime<br/>(Python Skills 執行)"]
        Media_Processor["Media Processor<br/>(Azure TTS/影像)"]
    end

    %% 資料流
    API_Gateway <-->|標準化 JSON| Flow_Manager
    Flow_Manager <--> Context_Engine
    Flow_Manager <--> Tool_Picker
    
    Context_Engine --- Memory_Service
    Tool_Picker --- Skill_Runtime
    Flow_Manager <--> Brain_Adapter
    Flow_Manager --> Media_Processor