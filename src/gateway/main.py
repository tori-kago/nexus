from fastapi import FastAPI, WebSocket, Request, Query, BackgroundTasks
from fastapi.staticfiles import StaticFiles
import json
import asyncio
import os
import re
import shutil
import logging
from datetime import datetime
from typing import Dict, List, Any
from uuid import uuid4

from src.core.orchestrator import NexusOrchestrator
from src.core.session_store import SessionStore
from src.adapters.brain.gemini_cli_adapter import GeminiCLIBrainAdapter
from src.adapters.memory.vault_adapter import VaultAdapter
from src.adapters.tool.python_tool_adapter import PythonToolAdapter
from src.adapters.tool.base_skills import list_nexus_files, read_nexus_file, get_recent_logs, update_env_config, restore_nexus_snapshot, update_personality, reset_session_context
from src.adapters.media.hybrid_stt_adapter import HybridSTTAdapter
from src.adapters.media.hybrid_tts_adapter import HybridTTSAdapter
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger("Nexus.Gateway")
app = FastAPI(title='Nexus Gateway (Notification Hub v4.3)')

# --- Housekeeping ---
TEMP_TTS_DIR = "src/brain/vault/temp_tts"
CACHE_TTS_DIR = "src/brain/vault/cache_tts"
LOGS_DIR = "src/brain/vault/logs"
for d in [TEMP_TTS_DIR, CACHE_TTS_DIR, LOGS_DIR]: os.makedirs(d, exist_ok=True)
app.mount("/static/audio", StaticFiles(directory=TEMP_TTS_DIR), name="audio")
app.mount("/cache/audio", StaticFiles(directory=CACHE_TTS_DIR), name="audio_cache")

# --- Adapters ---
brain_adapter = GeminiCLIBrainAdapter()
memory_adapter = VaultAdapter()
tool_adapter = PythonToolAdapter()
stt_adapter = HybridSTTAdapter()
tts_adapter = HybridTTSAdapter()
session_store = SessionStore()

active_connections: Dict[str, WebSocket] = {}
# --- 平台客戶端暫存 (用於離線通知) ---
# platform_name -> callback_url (例如 tg -> http://localhost:9000/send)
platform_clients: Dict[str, str] = {}

# --- Register Skills (略) ---
tool_adapter.register_tool("get_system_time", "獲取時間", lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
tool_adapter.register_tool("list_nexus_files", "查看目錄", list_nexus_files)
tool_adapter.register_tool("read_nexus_file", "讀取檔案", read_nexus_file)
tool_adapter.register_tool("get_recent_logs", "日誌分析", get_recent_logs)
tool_adapter.register_tool("update_env_config", "設定金鑰", update_env_config)
tool_adapter.register_tool("restore_nexus_snapshot", "回滾快照", restore_nexus_snapshot)
tool_adapter.register_tool("update_personality", "優化性格", update_personality)
tool_adapter.register_tool("reset_session_context", "重置對話歷史。", reset_session_context)

def create_orchestrator(on_status_cb=None):
    return NexusOrchestrator(brain=brain_adapter, memory=memory_adapter, tool=tool_adapter, on_status=on_status_cb)

@app.post('/register_client')
async def register_client(request: Request):
    """供 Bot 客戶端註冊其接收通知的接口"""
    data = await request.json()
    platform = data.get("platform")
    callback_url = data.get("url")
    platform_clients[platform] = callback_url
    return {"status": "registered", "platform": platform}

@app.post('/notify')
async def notify_user(request: Request):
    """
    OpenClaw-style 通知接口。
    不論用戶是否在線，嘗試透過其最後使用的平台發送訊息。
    """
    data = await request.json()
    session_id = data.get("session_id")
    content = data.get("content", "")
    
    # 1. 嘗試 WebSocket (即時)
    if session_id in active_connections:
        ws = active_connections[session_id]
        if ws.client_state.name == "CONNECTED":
            await ws.send_json({"type": "text", "content": content, "is_proactive": True})
            return {"sent_via": "websocket"}

    # 2. 嘗試平台 API (離線通知)
    with session_store._init_db() as _: # 這裡只是確保 session_store 可用
        # 我們直接從資料庫查找該 session_id 的平台資訊
        import sqlite3
        with sqlite3.connect(session_store.DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT platform, platform_user_id FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            
            if row and row["platform"] in platform_clients:
                platform = row["platform"]
                target_url = platform_clients[platform]
                import requests
                # 呼叫 Bot 的轉發接口
                try:
                    requests.post(target_url, json={
                        "user_id": row["platform_user_id"],
                        "content": content
                    }, timeout=5)
                    return {"sent_via": platform}
                except: pass

    return {"status": "failed", "reason": "user_offline_and_no_relay"}

@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket, session_id: str = Query(None), platform: str = Query(None), platform_id: str = Query(None)):
    await websocket.accept()
    if not session_id: session_id = f"anonymous_{str(uuid4())[:8]}"
    
    active_connections[session_id] = websocket
    
    # 紀錄平台資訊
    if platform and platform_id:
        session_store.register_platform(session_id, platform, platform_id)

    async def on_status_update(state: str, reasoning: str):
        if websocket.client_state.name == "CONNECTED":
            try: await websocket.send_json({"type": "thought", "state": state, "content": reasoning})
            except: pass

    try:
        while True:
            try:
                data = await websocket.receive()
                if "text" not in data and "bytes" not in data: continue
            except: break
            
            try:
                user_input = ""
                if "text" in data:
                    user_input = json.loads(data["text"]).get("content", "")
                elif "bytes" in data:
                    user_input = await stt_adapter.speech_to_text(data["bytes"])
                    await on_status_update("observation", f"聽到了: {user_input}")

                if not user_input: continue
                
                history = session_store.get_messages(session_id)
                orchestrator = create_orchestrator(on_status_cb=on_status_update)
                reply_text = await asyncio.wait_for(orchestrator.run(user_input, session_context=history, session_id=session_id), timeout=120.0)
                
                if reply_text and websocket.client_state.name == "CONNECTED":
                    emotion = "neutral"
                    emotion_match = re.search(r"\[EMOTION: (.*?)\]", reply_text)
                    if emotion_match: emotion = emotion_match.group(1).lower().strip()
                    clean_text = re.sub(r"\[EMOTION: .*?\]", "", reply_text).strip()
                    await websocket.send_json({"type": "text", "content": clean_text, "emotion": emotion})
                    
                    async def handle_tts(text, em):
                        try:
                            audio_path = await tts_adapter.text_to_speech(text, emotion=em)
                            if audio_path and websocket.client_state.name == "CONNECTED":
                                sub = "cache/audio" if "cache_tts" in audio_path else "static/audio"
                                await websocket.send_json({"type": "audio", "audio_url": f"/{sub}/{os.path.basename(audio_path)}"})
                        except: pass
                    asyncio.create_task(handle_tts(clean_text, emotion))
                    
                    history = session_store.get_messages(session_id)
                    history.append(HumanMessage(content=user_input))
                    history.append(AIMessage(content=reply_text))
                    # 保存時帶上平台資訊
                    session_store.save_messages(session_id, history, platform=platform, platform_user_id=platform_id)

            except Exception as req_err:
                if websocket.client_state.name == "CONNECTED":
                    await websocket.send_json({"type": "text", "content": f"思考出錯：{str(req_err)}"})
                
    finally:
        if session_id in active_connections: del active_connections[session_id]
        if websocket.client_state.name == "CONNECTED":
            try: await websocket.close()
            except: pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, ws_ping_interval=20, ws_ping_timeout=20)
