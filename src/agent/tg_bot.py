import os
import json
import asyncio
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from fastapi import FastAPI, Request
import uvicorn
from threading import Thread
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Nexus.TG")

GATEWAY_BASE_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
# 本地 Bot 通知接收地址
BOT_NOTIFY_HOST = "0.0.0.0"
BOT_NOTIFY_PORT = 9000
BOT_NOTIFY_URL = f"http://localhost:{BOT_NOTIFY_PORT}/push"

# 全局 TG 應用實例，用於推播
tg_app = None

async def call_nexus_gateway_async(user_id: str, text: str = None, voice_bytes: bytes = None):
    """
    透過 REST API 非同步呼叫 Nexus Gateway。
    發送後立刻結束，不維持連線。
    """
    sid = f"tg_{user_id}"
    try:
        if voice_bytes:
            # 呼叫語音接口
            files = {'file': ('voice.ogg', voice_bytes, 'audio/ogg')}
            data = {'session_id': sid, 'platform': 'tg', 'platform_id': str(user_id)}
            res = requests.post(f"{GATEWAY_BASE_URL}/api/voice", files=files, data=data, timeout=10)
        else:
            # 呼叫文字接口
            payload = {"session_id": sid, "platform": "tg", "platform_id": str(user_id), "content": text}
            res = requests.post(f"{GATEWAY_BASE_URL}/api/chat", json=payload, timeout=10)
        
        if res.status_code != 200:
            logger.error(f"Gateway rejected request: {res.text}")
    except Exception as e:
        logger.error(f"Failed to call Gateway: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if not text: return
    
    # 提示用戶正在處理 (Telegram 的亮點：顯示 Typing...)
    await context.bot.send_chat_action(chat_id=user_id, action="typing")
    await call_nexus_gateway_async(user_id, text=text)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    voice = update.message.voice
    
    await context.bot.send_chat_action(chat_id=user_id, action="record_voice")
    
    file = await context.bot.get_file(voice.file_id)
    data = await file.download_as_bytearray()
    await call_nexus_gateway_async(user_id, voice_bytes=bytes(data))

# --- 通知接收服務 (REST Webhook) ---
notify_server = FastAPI()

@notify_server.post("/push")
async def receive_push(request: Request):
    """接收來自 Gateway 的推理結果"""
    data = await request.json()
    user_id = data.get("user_id")
    content = data.get("content")
    audio_url = data.get("audio_url")
    
    if tg_app:
        # 1. 發送文字
        await tg_app.bot.send_message(chat_id=user_id, text=content)
        
        # 2. 如果有語音且 URL 有效
        if audio_url:
            try:
                voice_res = requests.get(GATEWAY_BASE_URL + audio_url, timeout=10)
                if voice_res.status_code == 200:
                    await tg_app.bot.send_voice(chat_id=user_id, voice=voice_res.content)
            except Exception as e:
                logger.error(f"Failed to send voice push: {e}")
                
    return {"status": "ok"}

def run_notify_server():
    uvicorn.run(notify_server, host=BOT_NOTIFY_HOST, port=BOT_NOTIFY_PORT)

if __name__ == '__main__':
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("[!] TELEGRAM_BOT_TOKEN is missing.")
    else:
        # 啟動背景 Webhook 伺服器
        Thread(target=run_notify_server, daemon=True).start()
        
        # 向 Gateway 註冊
        try:
            requests.post(f"{GATEWAY_BASE_URL}/register_client", json={"platform": "tg", "url": BOT_NOTIFY_URL})
        except: pass
        
        tg_app = ApplicationBuilder().token(token).build()
        tg_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        tg_app.add_handler(MessageHandler(filters.VOICE, handle_voice))
        
        print("--- Nexus TG Bot (Robust Async Mode) Started ---")
        tg_app.run_polling()
