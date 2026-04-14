import os
import json
import asyncio
import requests
import uuid
from datetime import datetime
from src.shared.bus import MessageBus, CHANNELS
from src.shared.schemas import NexusEnvelope, MessageType, AudioPayload

# GPT-SoVITS API 配置
SOVITS_API_URL = os.getenv("SOVITS_API_URL", "http://127.0.0.1:9880")
AUDIO_SAVE_DIR = "temp/audio"

class ExpressionWorker:
    def __init__(self):
        self.bus = MessageBus()
        self.p = self.bus.r.pubsub()
        self.p.subscribe(CHANNELS['TEXT'])
        
        if not os.path.exists(AUDIO_SAVE_DIR):
            os.makedirs(AUDIO_SAVE_DIR)

    async def generate_tts(self, text, emotion, trace_id):
        """呼叫 GPT-SoVITS API 生成語音"""
        # 這裡可以根據 emotion 切換不同的參考音檔或參數
        params = {
            "text": text,
            "text_language": "zh", # 預設中文
            # 這裡可以加入更多 GPT-SoVITS 支援的參數，例如 top_k, top_p 等
        }
        
        filename = f"{uuid.uuid4()}.wav"
        filepath = os.path.join(AUDIO_SAVE_DIR, filename)
        
        try:
            print(f"[Exp] 🎤 Generating TTS for: {text[:20]}...")
            response = requests.get(SOVITS_API_URL, params=params, timeout=30)
            
            if response.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(response.content)
                return filepath
            else:
                print(f"[Exp] ❌ TTS API Error: {response.status_code}")
                return None
        except Exception as e:
            print(f"[Exp] ❌ TTS Connection Error: {e}")
            return None

    async def run(self):
        print('--- Nexus Expression Worker Started ---')
        print(f'[*] Monitoring {CHANNELS["TEXT"]} for TTS triggers...')
        
        while True:
            message = self.p.get_message(ignore_subscribe_messages=True)
            if message:
                try:
                    data = json.loads(message['data'])
                    # 相容 NexusEnvelope 格式
                    text = data['payload'].get('content', '')
                    emotion = data['payload'].get('emotion', 'neutral')
                    trace_id = data.get('trace_id')
                    session_id = data.get('session_id')

                    if text:
                        # 1. 生成語音
                        audio_path = await self.generate_tts(text, emotion, trace_id)
                        
                        if audio_path:
                            # 2. 封裝並發布語音訊息
                            audio_envelope = NexusEnvelope(
                                source="exp:worker",
                                type=MessageType.AUDIO,
                                trace_id=trace_id,
                                session_id=session_id,
                                payload={
                                    "url": os.path.abspath(audio_path),
                                    "format": "wav",
                                    "content": text,
                                    "emotion": emotion
                                }
                            )
                            self.bus.publish_envelope(audio_envelope)
                            print(f"[Exp] ✅ Audio Generated: {audio_path}")
                            
                            # 3. (選配) 本地開發時可以直接播放測試
                            # os.system(f"afplay {audio_path}") # macOS 專用播放指令
                            
                except Exception as e:
                    print(f"[Exp] Error processing message: {e}")
            
            await asyncio.sleep(0.1)

if __name__ == "__main__":
    worker = ExpressionWorker()
    asyncio.run(worker.run())
