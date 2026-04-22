import os
import json
import asyncio
import logging
import websockets
import discord
import requests
from discord.ext import commands
from fastapi import FastAPI, Request
import uvicorn
from threading import Thread
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Nexus.Discord")

GATEWAY_WS_URL = "ws://localhost:8000/ws"
GATEWAY_BASE_URL = "http://localhost:8000"
# 本地 Discord Bot 通知接收地址 (換一個 Port，避免與 TG 衝突)
BOT_NOTIFY_PORT = 9001
BOT_NOTIFY_URL = f"http://localhost:{BOT_NOTIFY_PORT}/push"

class NexusDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def call_nexus_gateway(self, user_id: str, message_obj: discord.Message, text: str = None, voice_bytes: bytes = None):
        # 註冊平台資訊
        url = f"{GATEWAY_WS_URL}?session_id=discord_{user_id}&platform=discord&platform_id={user_id}"
        is_voice = (voice_bytes is not None)
        async with message_obj.channel.typing():
            try:
                async with websockets.connect(url) as ws:
                    if is_voice: await ws.send(voice_bytes)
                    else: await ws.send(json.dumps({"content": text}))
                    while True:
                        res = await ws.recv()
                        data = json.loads(res)
                        if data["type"] == "text":
                            await message_obj.reply(data["content"])
                            if not is_voice: break
                        elif data["type"] == "audio" and is_voice:
                            audio_res = requests.get(GATEWAY_BASE_URL + data["audio_url"])
                            if audio_res.status_code == 200:
                                with open("temp_discord.mp3", "wb") as f: f.write(audio_res.content)
                                await message_obj.reply(file=discord.File("temp_discord.mp3"))
                            break
            except Exception as e:
                logger.error(f"Discord Relay Error: {e}")

bot = NexusDiscordBot()

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    if isinstance(message.channel, discord.DMChannel) or bot.user.mentioned_in(message):
        voice_data = None
        if message.attachments:
            for att in message.attachments:
                if att.content_type and "audio" in att.content_type:
                    voice_data = await att.read()
                    break
        clean_text = message.content.replace(f'<@!{bot.user.id}>', '').replace(f'<@{bot.user.id}>', '').strip()
        await bot.call_nexus_gateway(str(message.author.id), message, text=clean_text, voice_bytes=voice_data)

# --- 通知接收伺服器 ---
notify_server = FastAPI()

@notify_server.post("/push")
async def receive_push(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    content = data.get("content")
    
    # 在 Discord 中主動發送訊息
    user = await bot.fetch_user(int(user_id))
    if user:
        await user.send(f"🔔 **Nexus 提醒**\n{content}")
    return {"status": "ok"}

def run_notify_server():
    uvicorn.run(notify_server, host="0.0.0.0", port=BOT_NOTIFY_PORT)

if __name__ == '__main__':
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("[!] No Token.")
    else:
        # 1. 啟動通知接收伺服器
        Thread(target=run_notify_server, daemon=True).start()
        
        # 2. 向 Gateway 註冊
        try:
            requests.post(f"{GATEWAY_BASE_URL}/register_client", json={"platform": "discord", "url": BOT_NOTIFY_URL})
        except: pass
        
        bot.run(token)
