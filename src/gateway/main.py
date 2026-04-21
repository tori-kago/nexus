from fastapi import FastAPI, WebSocket, Request
from fastapi.staticfiles import StaticFiles
import json
import asyncio
import os
import re
import shutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from uuid import uuid4

from src.core.orchestrator import NexusOrchestrator
from src.adapters.brain.gemini_cli_adapter import GeminiCLIBrainAdapter
from src.adapters.memory.vault_adapter import VaultAdapter
from src.adapters.tool.python_tool_adapter import PythonToolAdapter
from src.adapters.tool.base_skills import list_nexus_files, read_nexus_file, get_recent_logs, update_env_config, restore_nexus_snapshot, update_personality
from src.adapters.media.hybrid_stt_adapter import HybridSTTAdapter
from src.adapters.media.hybrid_tts_adapter import HybridTTSAdapter
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger("Nexus.Gateway")
app = FastAPI(title='Nexus Gateway (Self-Evolving v3.9)')

# --- Housekeeping ---
TEMP_TTS_DIR = "src/brain/vault/temp_tts"
CACHE_TTS_DIR = "src/brain/vault/cache_tts"
LOGS_DIR = "src/brain/vault/logs"

def housekeeping():
    print("[Housekeeping] 啟動系統大掃除...")
    for d in [TEMP_TTS_DIR, CACHE_TTS_DIR, LOGS_DIR]: os.makedirs(d, exist_ok=True)
    if os.path.exists(TEMP_TTS_DIR): shutil.rmtree(TEMP_TTS_DIR)
    os.makedirs(TEMP_TTS_DIR)
housekeeping()

app.mount("/static/audio", StaticFiles(directory=TEMP_TTS_DIR), name="audio")
app.mount("/cache/audio", StaticFiles(directory=CACHE_TTS_DIR), name="audio_cache")

# --- Adapters ---
brain_adapter = GeminiCLIBrainAdapter()
memory_adapter = VaultAdapter()
tool_adapter = PythonToolAdapter()
stt_adapter = HybridSTTAdapter()
tts_adapter = HybridTTSAdapter()

# --- Register Skills ---
tool_adapter.register_tool("get_system_time", "獲取主機目前時間", lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
tool_adapter.register_tool("list_nexus_files", "查看專案目錄結構", list_nexus_files)
tool_adapter.register_tool("read_nexus_file", "讀取專案檔案內容", read_nexus_file)
tool_adapter.register_tool("get_recent_logs", "獲取系統日誌", get_recent_logs)
tool_adapter.register_tool("update_env_config", "更新系統設定與 API 金鑰。", update_env_config)
tool_adapter.register_tool("restore_nexus_snapshot", "回滾系統快照。", restore_nexus_snapshot)
tool_adapter.register_tool("update_personality", "【核心能力】自我優化性格與行為準則。當用戶要求調整你的回覆風格或性格時使用。", update_personality)

sessions: Dict[str, List[Any]] = {}

def create_orchestrator(on_status_cb=None):
    return NexusOrchestrator(brain=brain_adapter, memory=memory_adapter, tool=tool_adapter, on_status=on_status_cb)

@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid4())
    sessions[session_id] = []
    
    async def on_status_update(state: str, reasoning: str):
        if websocket.client_state.name == "CONNECTED":
            try: await websocket.send_json({"type": "thought", "state": state, "content": reasoning})
            except: pass

    try:
        while True:
            try: data = await websocket.receive()
            except: break
            
            user_input = ""
            if "text" in data: user_input = json.loads(data["text"]).get("content", "")
            elif "bytes" in data:
                await on_status_update("stt", "辨識中...")
                user_input = await stt_adapter.speech_to_text(data["bytes"])
                await websocket.send_json({"type": "thought", "state": "observation", "content": f"聽到了: {user_input}"})

            if not user_input: continue
            
            orchestrator = create_orchestrator(on_status_cb=on_status_update)
            reply_text = await orchestrator.run(user_input, session_context=sessions[session_id])
            
            if reply_text and websocket.client_state.name == "CONNECTED":
                emotion = "neutral"
                emotion_match = re.search(r"\[EMOTION: (.*?)\]", reply_text)
                if emotion_match: emotion = emotion_match.group(1).lower().strip()
                clean_text = re.sub(r"\[EMOTION: .*?\]", "", reply_text).strip()
                
                await websocket.send_json({"type": "text", "content": clean_text, "emotion": emotion})
                
                async def handle_tts():
                    audio_path = await tts_adapter.text_to_speech(clean_text, emotion=emotion)
                    if audio_path and websocket.client_state.name == "CONNECTED":
                        sub_path = "cache/audio" if "cache_tts" in audio_path else "static/audio"
                        audio_url = f"/{sub_path}/{os.path.basename(audio_path)}"
                        await websocket.send_json({"type": "audio", "audio_url": audio_url})
                
                asyncio.create_task(handle_tts())
                sessions[session_id].append(HumanMessage(content=user_input))
                sessions[session_id].append(AIMessage(content=reply_text))
                if len(sessions[session_id]) > 14: sessions[session_id] = sessions[session_id][4:]
                
    except Exception as e: print(f'[!] WebSocket error: {e}')
    finally:
        if session_id in sessions: del sessions[session_id]
        if websocket.client_state.name == "CONNECTED":
            try: await websocket.close()
            except: pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
