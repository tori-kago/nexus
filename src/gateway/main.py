from fastapi import FastAPI, WebSocket, Request, Query, BackgroundTasks
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
from typing import Dict, List, Any
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
    print("[System] 啟動自主心跳與工程師循環...")
    heartbeat_task = asyncio.create_task(heartbeat_loop())
    yield
    heartbeat_task.cancel()

app = FastAPI(title='Nexus Gateway (Knowledge Enabled v4.6)', lifespan=lifespan)

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

# --- 核心優化：針對性心跳循環 ---
async def heartbeat_loop():
    """背景心跳：每小時反思，僅針對綁定平台(TG/DC)的用戶"""
    await asyncio.sleep(30) # 啟動後稍等
    while True:
        current_hour = datetime.now().hour
        is_work_time = (9 <= current_hour <= 11)
        
        logger.info(f"[Heartbeat] 啟動循環 (工作時間: {is_work_time})...")
        
        # 獲取最近 24 小時內活躍的會話
        active_sessions = session_store.get_active_sessions(hours=24)
        
        for session in active_sessions:
            sid = session["session_id"]
            platform = session["platform"]
            
            # --- 關鍵優化：只對真實 IM 平台用戶進行主動反思 ---
            if not platform or platform not in ["tg", "discord"]:
                continue
                
            history = session_store.get_messages(sid)
            safe_history = copy.deepcopy(history)
            orchestrator = create_orchestrator()
            
            if is_work_time:
                prompt = """
[SYSTEM WORK] 現在是研究時間。請閱讀 soul/ 指南、分析近期日誌與技能，執行必要的自我優化。
若有心得請用 record_work_insight 紀錄，完成後回傳 {"thought": "...", "action_type": "REPLY", "action_param": "IGNORE"}。
"""
            else:
                prompt = "[SYSTEM HEARTBEAT] 檢查近期對話與記憶，決定是否主動聯繫用戶。若無事請回 IGNORE。"
                
            try:
                # 心跳推理超時設為 180 秒以因應深度思維
                reply = await asyncio.wait_for(orchestrator.run(prompt, is_proactive=True, session_context=safe_history, session_id=sid), timeout=180.0)
                if reply and "IGNORE" not in reply:
                    await notify_user_internal(sid, reply)
            except Exception as e:
                logger.error(f"Heartbeat error for {sid}: {e}")
        
        await asyncio.sleep(3600) # 每小時一次

async def notify_user_internal(session_id: str, content: str):
    if session_id in active_connections:
        ws = active_connections[session_id]
        if ws.client_state.name == "CONNECTED":
            await ws.send_json({"type": "text", "content": content, "is_proactive": True})
            return
    import sqlite3
    with sqlite3.connect(session_store.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT platform, platform_user_id FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row and row["platform"] in platform_clients:
            import requests
            try: requests.post(platform_clients[row["platform"]], json={"user_id": row["platform_user_id"], "content": content}, timeout=5)
            except: pass

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
                if "text" in data: user_input = json.loads(data["text"]).get("content", "")
                elif "bytes" in data:
                    user_input = await stt_adapter.speech_to_text(data["bytes"])
                    await on_status_update("observation", f"聽到了: {user_input}")
                if not user_input: continue
                history = session_store.get_messages(session_id)
                safe_history = copy.deepcopy(history)
                orchestrator = create_orchestrator(on_status_cb=on_status_update)
                reply_text = await asyncio.wait_for(orchestrator.run(user_input, session_context=safe_history, session_id=session_id), timeout=120.0)
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
                    session_store.save_messages(session_id, history, platform=platform, platform_user_id=platform_id)
            except Exception as e:
                if websocket.client_state.name == "CONNECTED": await websocket.send_json({"type": "text", "content": f"思考故障: {e}"})
    finally:
        if session_id in active_connections: del active_connections[session_id]
        if websocket.client_state.name == "CONNECTED":
            try: await websocket.close()
            except: pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, ws_ping_interval=20, ws_ping_timeout=20)
