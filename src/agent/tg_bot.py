import os
import asyncio
import json
import requests
import websockets
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from uuid import uuid4
from src.shared.schemas import NexusEnvelope

# 載入 .env 檔案中的環境變數
load_dotenv()

# 配置
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
WS_URL = os.getenv("WS_URL", "ws://localhost:8000/ws")

# 確保暫存目錄存在
TEMP_AUDIO_DIR = "temp/audio"
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

class NexusTelegramBot:
    def __init__(self, token: str, chat_id: str):
        self.app = ApplicationBuilder().token(token).build()
        self.master_chat_id = int(chat_id) if chat_id.isdigit() else None

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """處理 Telegram 語音訊息並通知 STT Worker"""
        current_chat_id = update.effective_chat.id
        
        # 安全性檢查
        if self.master_chat_id and current_chat_id != self.master_chat_id:
            return

        print(f"[TG] Received voice from Master ({current_chat_id})")
        
        try:
            # 1. 下載語音檔
            voice_file = await context.bot.get_file(update.message.voice.file_id)
            trace_id = str(uuid4())
            file_path = os.path.join(TEMP_AUDIO_DIR, f"{trace_id}.ogg")
            await voice_file.download_to_drive(file_path)
            
            # 2. 通知 STT Worker (發布到 nexus.audio_in)
            from src.shared.bus import MessageBus, CHANNELS
            bus = MessageBus()
            audio_info = {
                "file_path": file_path,
                "trace_id": trace_id,
                "session_id": str(current_chat_id),
                "platform": "telegram_voice",
                "user": update.effective_user.first_name
            }
            bus.r.publish(CHANNELS['AUDIO_IN'], json.dumps(audio_info))
            print(f"[TG] Voice downloaded and notification sent: {file_path}")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Voice Process Error: {e}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """處理 Telegram 用戶輸入並轉發至 Nexus Gateway"""
        user_text = update.message.text
        current_chat_id = update.effective_chat.id
        
        # 安全性檢查：白名單過濾
        if self.master_chat_id and current_chat_id != self.master_chat_id:
            print(f"[TG Security] Unauthorized access attempt from {current_chat_id}")
            await update.message.reply_text("⛔ 您無權操作此 Nexus 實體。")
            return

        print(f"[TG] Received from Master ({current_chat_id}): {user_text}")
        
        # 轉發至 Gateway
        try:
            payload = {
                "content": user_text,
                "platform": "telegram",
                "session_id": str(current_chat_id),
                "user": update.effective_user.first_name
            }
            res = requests.post(f"{GATEWAY_URL}/input", json=payload)
            res.raise_for_status()
            print(f"[TG] Forwarded to Gateway, Trace: {res.json().get('trace_id')}")
        except Exception as e:
            await update.message.reply_text(f"❌ Gateway Error: {e}")

    async def ws_listener(self):
        """從 WebSocket 接收 Nexus 回覆並轉發至 Telegram"""
        print(f"[TG] Connecting to WebSocket: {WS_URL}")
        while True:
            try:
                async with websockets.connect(WS_URL) as websocket:
                    while True:
                        message = await websocket.recv()
                        try:
                            envelope = json.loads(message)
                            msg_type = envelope.get("type")
                            payload = envelope.get("payload", {})
                            session_id = envelope.get("session_id")
                            
                            # 定向發送：優先發給 session_id，若無則發給主人
                            target_id = int(session_id) if (session_id and session_id.isdigit()) else self.master_chat_id
                            if not target_id: continue

                            # 處理文字訊息
                            if msg_type == "text":
                                content = payload.get("content", "")
                                if content:
                                    await self.app.bot.send_message(chat_id=target_id, text=content)
                                    print(f"[TG] Sent Text to {target_id}")

                            # 處理語音訊息 (🆕 新增)
                            elif msg_type == "audio":
                                audio_url = payload.get("url")
                                if audio_url and os.path.exists(audio_url):
                                    with open(audio_url, 'rb') as voice:
                                        await self.app.bot.send_voice(chat_id=target_id, voice=voice)
                                    print(f"[TG] Sent Voice to {target_id}: {audio_url}")
                                    
                        except Exception as e:
                            print(f"[TG WS Message Process Error] {e}")
            except Exception as e:
                print(f"[TG WS Connection Error] {e}")
                await asyncio.sleep(5) # 斷線重連

    async def startup_notify(self):
        """啟動時向主人報到"""
        if self.master_chat_id:
            try:
                await self.app.bot.send_message(chat_id=self.master_chat_id, text="🚀 Nexus 系統已在線。主人，請吩咐。")
                print(f"[TG] Startup notification sent to {self.master_chat_id}")
            except Exception as e:
                print(f"[TG Notify Error] {e}")

    def run(self):
        """啟動機器人"""
        print("--- Nexus Telegram Bot (Secured) Started ---")
        
        # 添加處理程序
        self.app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_message))
        self.app.add_handler(MessageHandler(filters.VOICE, self.handle_voice)) # 註冊語音處理器
        
        # 建立事件循環
        loop = asyncio.get_event_loop()
        
        # 啟動任務
        loop.create_task(self.ws_listener())
        loop.create_task(self.startup_notify())
        
        # 啟動 Telegram 機器人
        self.app.run_polling()

if __name__ == "__main__":
    if TELEGRAM_TOKEN == "YOUR_BOT_TOKEN_HERE" or not TELEGRAM_CHAT_ID:
        print("Please set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID environment variables.")
    else:
        bot = NexusTelegramBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
        bot.run()
