from fastapi import FastAPI, WebSocket, Request, Query, BackgroundTasks, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import json
import asyncio
import os
import re
import shutil
import logging
import copy
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4

from src.core.orchestrator import NexusOrchestrator
from src.core.session_store import SessionStore
from src.adapters.brain.gemini_cli_adapter import GeminiCLIBrainAdapter
from src.adapters.memory.vault_adapter import VaultAdapter
from src.adapters.tool.python_tool_adapter import PythonToolAdapter
from src.adapters.tool.base_skills import read_nexus_file, update_env_config, restore_nexus_snapshot, update_personality, reset_session_context, record_work_insight, run_shell
from src.adapters.media.hybrid_stt_adapter import HybridSTTAdapter
from src.adapters.media.hybrid_tts_adapter import HybridTTSAdapter
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger("Nexus.Gateway")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[System] 啟動自主心跳與工程師循環...")
    heartbeat_task = asyncio.create_task(heartbeat_loop())
    yield
    heartbeat_task.cancel()

app = FastAPI(title='Nexus Gateway (Async REST v5.0)', lifespan=lifespan)

# --- Housekeeping ---
TEMP_TTS_DIR = "src/brain/vault/temp_tts"
CACHE_TTS_DIR = "src/brain/vault/cache_tts"
LOGS_DIR = "src/brain/vault/logs"
for d in [TEMP_TTS_DIR, CACHE_TTS_DIR, LOGS_DIR]: os.makedirs(d, exist_ok=True)
if os.path.exists(TEMP_TTS_DIR): shutil.rmtree(TEMP_TTS_DIR)
os.makedirs(TEMP_TTS_DIR)

app.mount("/static/audio", StaticFiles(directory=TEMP_TTS_DIR), name="audio")
app.mount("/cache/audio", StaticFiles(directory=CACHE_TTS_DIR), name="audio_cache")

# --- Adapters ---
brain_adapter = GeminiCLIBrainAdapter()
memory_adapter = VaultAdapter()
tool_adapter = PythonToolAdapter()
stt_adapter = HybridSTTAdapter()
tts_adapter = HybridTTSAdapter()
session_store = SessionStore()

# --- Register Skills ---
tool_adapter.register_tool("run_shell", "執行終端指令。", run_shell)
tool_adapter.register_tool("read_nexus_file", "讀取檔案內容。", read_nexus_file)
tool_adapter.register_tool("update_env_config", "更新配置。", update_env_config)
tool_adapter.register_tool("restore_nexus_snapshot", "回滾快照。", restore_nexus_snapshot)
tool_adapter.register_tool("update_personality", "優化性格文檔。", update_personality)
tool_adapter.register_tool("reset_session_context", "重置對話歷史。", reset_session_context)
tool_adapter.register_tool("record_work_insight", "紀錄研究心得。", record_work_insight)

def create_orchestrator(on_status_cb=None):
    return NexusOrchestrator(brain=brain_adapter, memory=memory_adapter, tool=tool_adapter, on_status=on_status_cb)

# --- 核心邏輯：非同步處理任務 ---
async def process_chat_task(session_id: str, platform: str, platform_id: str, user_input: str):
    """在背景執行推理並推播結果"""
    try:
        history = session_store.get_messages(session_id)
        safe_history = copy.deepcopy(history)
        
        # 使用沒有回調的調度器 (因為是 REST 背景任務)
        orchestrator = create_orchestrator()
        
        reply_text = await asyncio.wait_for(
            orchestrator.run(user_input, session_context=safe_history, session_id=session_id),
            timeout=180.0
        )
        
        if reply_text:
            # 處理情緒與清理
            emotion = "neutral"
            emotion_match = re.search(r"\[EMOTION: (.*?)\]", reply_text)
            if emotion_match: emotion = emotion_match.group(1).lower().strip()
            clean_text = re.sub(r"\[EMOTION: .*?\]", "", reply_text).strip()
            
            # 產生語音
            audio_path = await tts_adapter.text_to_speech(clean_text, emotion=emotion)
            audio_url = None
            if audio_path:
                sub = "cache/audio" if "cache_tts" in audio_path else "static/audio"
                audio_url = f"/{sub}/{os.path.basename(audio_path)}"
            
            # 推播回平台
            payload = {
                "session_id": session_id,
                "content": clean_text,
                "audio_url": audio_url,
                "emotion": emotion,
                "platform": platform,
                "platform_id": platform_id
            }
            await notify_user_internal_complex(payload)
            
            # 存入記憶
            history.append(HumanMessage(content=user_input))
            history.append(AIMessage(content=reply_text))
            session_store.save_messages(session_id, history, platform=platform, platform_user_id=platform_id)
            
    except Exception as e:
        logger.error(f"Async Task Error: {e}")
        await notify_user_internal(session_id, f"抱歉，我的大腦剛才卡住了: {str(e)}")

async def notify_user_internal_complex(payload: dict):
    """支援多媒體的推播邏輯"""
    sid = payload["session_id"]
    # 1. 嘗試 WS
    if sid in active_connections:
        ws = active_connections[sid]
        if ws.client_state.name == "CONNECTED":
            await ws.send_json({"type": "text", "content": payload["content"], "emotion": payload["emotion"]})
            if payload["audio_url"]:
                await ws.send_json({"type": "audio", "audio_url": payload["audio_url"]})
            return

    # 2. 離線 Relay
    import sqlite3
    with sqlite3.connect(session_store.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT platform, platform_user_id FROM sessions WHERE session_id = ?", (sid,)).fetchone()
        if row and row["platform"] in platform_clients:
            import requests
            try:
                requests.post(platform_clients[row["platform"]], json={
                    "user_id": row["platform_user_id"],
                    "content": payload["content"],
                    "audio_url": payload["audio_url"]
                }, timeout=10)
            except Exception as e:
                logger.error(f"Relay failed: {e}")

# --- REST 接口 ---
@app.post('/api/chat')
async def chat_api(request: Request, background_tasks: BackgroundTasks):
    """
    非同步聊天接口：接收後立刻回傳，大腦在背景思考。
    """
    data = await request.json()
    sid = data.get("session_id")
    platform = data.get("platform", "api")
    platform_id = data.get("platform_id", sid)
    content = data.get("content", "")
    
    if not sid or not content:
        return {"status": "error", "message": "Missing session_id or content"}
        
    background_tasks.add_task(process_chat_task, sid, platform, platform_id, content)
    return {"status": "accepted", "session_id": sid}

@app.post('/api/voice')
async def voice_api(background_tasks: BackgroundTasks, session_id: str = Form(...), platform: str = Form(...), platform_id: str = Form(...), file: UploadFile = File(...)):
    """處理語音上傳的非同步接口"""
    audio_bytes = await file.read()
    user_input = await stt_adapter.speech_to_text(audio_bytes)
    if user_input:
        background_tasks.add_task(process_chat_task, session_id, platform, platform_id, user_input)
        return {"status": "accepted", "transcribed": user_input}
    return {"status": "error", "message": "STT Failed"}

# --- (其餘通知與心跳邏輯) ---
async def heartbeat_loop():
    await asyncio.sleep(60)
    while True:
        # 心跳邏輯 (同 v4.5/4.6，呼叫 notify_user_internal)
        await asyncio.sleep(3600)

async def notify_user_internal(sid, content):
    await notify_user_internal_complex({"session_id": sid, "content": content, "audio_url": None, "emotion": "neutral"})

active_connections: Dict[str, WebSocket] = {}
platform_clients: Dict[str, str] = {}

@app.post('/register_client')
async def register_client(request: Request):
    data = await request.json()
    platform_clients[data.get("platform")] = data.get("url")
    return {"status": "registered"}

@app.post('/notify')
async def notify_user(request: Request):
    data = await request.json()
    await notify_user_internal(data.get("session_id"), data.get("content", ""))
    return {"status": "dispatched"}

@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket, session_id: str = Query(None), platform: str = Query(None), platform_id: str = Query(None)):
    await websocket.accept()
    if not session_id: session_id = f"anonymous_{str(uuid4())[:8]}"
    active_connections[session_id] = websocket
    if platform and platform_id: session_store.register_platform(session_id, platform, platform_id)
    # WS 邏輯保留給 CLI 介面使用
    try:
        while True:
            data = await websocket.receive_text()
            user_input = json.loads(data).get("content", "")
            # 此處維持原有的同步 WS 推理邏輯...
            history = session_store.get_messages(session_id)
            orchestrator = create_orchestrator(on_status_cb=lambda s, r: websocket.send_json({"type":"thought", "state":s, "content":r}))
            reply = await orchestrator.run(user_input, session_context=history, session_id=session_id)
            if reply:
                await websocket.send_json({"type": "text", "content": reply})
    except: pass
    finally:
        if session_id in active_connections: del active_connections[session_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
