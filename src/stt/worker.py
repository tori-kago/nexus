import os
import json
import redis
import asyncio
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from src.shared.bus import MessageBus, CHANNELS
from src.shared.schemas import NexusEnvelope, MessageType

# 載入 .env 檔案中的環境變數
load_dotenv()

class STTWorker:
    def __init__(self, model_size="small", device="cpu", compute_type="int8"):
        # 取得 HF_TOKEN 以支援 Hugging Face 高速率下載 (選填)
        hf_token = os.getenv("HF_TOKEN")
        if hf_token:
            print("[*] HF_TOKEN detected, using it for model downloads.")
            # Faster-Whisper 本身不直接提供傳入 HF_TOKEN 的參數，
            # 但它底層調用時會讀取環境變數。
            
        print(f"[*] Loading Faster-Whisper model: {model_size}...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.bus = MessageBus()
        self.redis = self.bus.r

    async def run(self):
        p = self.redis.pubsub()
        p.subscribe(CHANNELS['AUDIO_IN'])
        
        print(f"--- Nexus STT Worker ({CHANNELS['AUDIO_IN']}) Started ---")
        
        while True:
            message = p.get_message(ignore_subscribe_messages=True)
            if message:
                try:
                    # 期待收到包含 file_path 的 JSON
                    data = json.loads(message['data'])
                    file_path = data.get("file_path")
                    trace_id = data.get("trace_id")
                    session_id = data.get("session_id")
                    user_name = data.get("user", "User")
                    
                    if not file_path or not os.path.exists(file_path):
                        print(f"[STT] File not found: {file_path}")
                        continue

                    print(f"[STT] Transcribing: {file_path} (Trace: {trace_id[:8]})")
                    
                    # 執行轉譯
                    segments, info = self.model.transcribe(file_path, beam_size=5)
                    text = "".join([segment.text for segment in segments]).strip()
                    
                    if text:
                        print(f"[STT] Result: {text}")
                        
                        # 封裝為標準 INPUT 封包發布回 Bus
                        envelope = NexusEnvelope(
                            source="stt_worker",
                            type=MessageType.INPUT,
                            trace_id=trace_id,
                            session_id=session_id,
                            payload={
                                "content": text,
                                "platform": data.get("platform", "voice"),
                                "user": user_name
                            }
                        )
                        self.bus.publish_envelope(envelope)
                    
                    # 轉譯完成後可選擇是否刪除暫存檔
                    # os.remove(file_path)
                    
                except Exception as e:
                    print(f"[STT Error] {e}")
            
            await asyncio.sleep(0.1)

if __name__ == "__main__":
    worker = STTWorker(model_size="small")
    asyncio.run(worker.run())
