import os
import json
import asyncio
import logging
import websockets
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
GATEWAY_WS_URL = GATEWAY_BASE_URL.replace("http", "ws") + "/ws"

# 本地 Bot 通知接收地址
BOT_NOTIFY_HOST = os.getenv("BOT_NOTIFY_HOST", "0.0.0.0")
BOT_NOTIFY_PORT = int(os.getenv("BOT_NOTIFY_PORT", "9000"))
# Gateway 用來回呼此 Bot 的 URL
BOT_NOTIFY_URL = os.getenv("BOT_NOTIFY_URL", f"http://localhost:{BOT_NOTIFY_PORT}/push")

# --- TG Bot 客戶端部分 ---
tg_app = None

async def call_nexus_gateway(user_id: str, message_obj: Update, text: str = None, voice_bytes: bytes = None):
    # 連線時帶入平台資訊
    url = f"{GATEWAY_WS_URL}?session_id=tg_{user_id}&platform=tg&platform_id={user_id}"
    is_voice = (voice_bytes is not None)
    try:
        async with websockets.connect(url) as ws:
            if is_voice: await ws.send(voice_bytes)
            else: await ws.send(json.dumps({"content": text}))
            while True:
                res = await ws.recv()
                data = json.loads(res)
                if data["type"] == "text":
                    await message_obj.message.reply_text(data["content"])
                    if not is_voice: break
                elif data["type"] == "audio" and is_voice:
                    audio_res = requests.get(GATEWAY_BASE_URL + data["audio_url"])
                    if audio_res.status_code == 200:
                        await message_obj.message.reply_voice(voice=audio_res.content)
                    break
    except Exception as e:
        logger.error(f"TG Relay Error: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await call_nexus_gateway(str(update.effective_user.id), update, text=update.message.text)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await context.bot.get_file(update.message.voice.file_id)
    data = await file.download_as_bytearray()
    await call_nexus_gateway(str(update.effective_user.id), update, voice_bytes=bytes(data))

# --- 通知接收服務 (用於主動推播) ---
notify_server = FastAPI()

@notify_server.post("/push")
async def receive_push(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    content = data.get("content")
    if tg_app:
        # 透過 TG Bot 主動發送訊息
        await tg_app.bot.send_message(chat_id=user_id, text=f"[Nexus 主動通知]\n{content}")
    return {"status": "ok"}

def run_notify_server():
    uvicorn.run(notify_server, host=BOT_NOTIFY_HOST, port=BOT_NOTIFY_PORT)

if __name__ == '__main__':
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("[!] No Token.")
    else:
        # 1. 啟動通知接收伺服器 (背景執行)
        Thread(target=run_notify_server, daemon=True).start()
        
        # 2. 向 Gateway 註冊此機器人
        try:
            requests.post(f"{GATEWAY_BASE_URL}/register_client", json={"platform": "tg", "url": BOT_NOTIFY_URL})
        except: pass
        
        # 3. 啟動 TG Bot
        tg_app = ApplicationBuilder().token(token).build()
        tg_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        tg_app.add_handler(MessageHandler(filters.VOICE, handle_voice))
        
        print("--- Nexus TG Bot (with Push Support) Started ---")
        tg_app.run_polling()
