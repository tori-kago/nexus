from fastapi import FastAPI, WebSocket, Request
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any
from uuid import uuid4

from src.core.orchestrator import NexusOrchestrator
from src.adapters.brain.gemini_cli_adapter import GeminiCLIBrainAdapter
from src.adapters.memory.vault_adapter import VaultAdapter
from src.adapters.tool.python_tool_adapter import PythonToolAdapter
from src.adapters.tool.base_skills import list_nexus_files, read_nexus_file, get_recent_logs
from langchain_core.messages import HumanMessage, AIMessage

app = FastAPI(title='Nexus Gateway (Autonomous v3.2)')

# 1. 初始化適配器 (單例)
brain_adapter = GeminiCLIBrainAdapter()
memory_adapter = VaultAdapter()
tool_adapter = PythonToolAdapter()

# 2. 註冊基礎技能
tool_adapter.register_tool(
    "get_system_time", 
    "獲取主機目前時間", 
    lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S')
)

tool_adapter.register_tool(
    "list_nexus_files",
    "查看 Nexus 專案中的目錄結構與檔案清單。",
    list_nexus_files
)

tool_adapter.register_tool(
    "read_nexus_file",
    "讀取 Nexus 專案中特定檔案的內容。",
    read_nexus_file
)

tool_adapter.register_tool(
    "get_recent_logs",
    "獲取 Nexus 系統最新的執行日誌與對話紀錄。這能幫助你了解最近發生的錯誤或對話脈絡。",
    get_recent_logs
)

# 會話存儲
sessions: Dict[str, List[Any]] = {}

def create_orchestrator(on_status_cb=None):
    return NexusOrchestrator(
        brain=brain_adapter,
        memory=memory_adapter,
        tool=tool_adapter,
        on_status=on_status_cb
    )

@app.get('/')
def index():
    return {'status': 'Nexus Gateway is running (Ultra-Stable Mode)'}

@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid4())
    sessions[session_id] = []
    
    async def on_status_update(state: str, reasoning: str):
        if websocket.client_state.name == "CONNECTED":
            try:
                await websocket.send_json({"type": "thought", "state": state, "content": reasoning})
            except: pass

    try:
        while True:
            try:
                data = await websocket.receive_text()
            except: break
            
            user_input = json.loads(data).get("content", "")
            orchestrator = create_orchestrator(on_status_cb=on_status_update)
            
            reply = await orchestrator.run(user_input, session_context=sessions[session_id])
            
            if reply and websocket.client_state.name == "CONNECTED":
                sessions[session_id].append(HumanMessage(content=user_input))
                sessions[session_id].append(AIMessage(content=reply))
                if len(sessions[session_id]) > 14:
                    sessions[session_id] = sessions[session_id][4:]
                await websocket.send_json({"type": "text", "content": reply})
                
    except Exception as e:
        print(f'[!] WebSocket internal error: {e}')
    finally:
        if session_id in sessions: del sessions[session_id]
        if websocket.client_state.name == "CONNECTED":
            try: await websocket.close()
            except: pass
        print(f'[*] WebSocket connection {session_id} cleaned up.')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
