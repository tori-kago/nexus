import os
import logging
import asyncio
import uuid
import re
import requests
import hashlib
from typing import Optional

try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:
    speechsdk = None

try:
    import edge_tts
except ImportError:
    edge_tts = None

from src.core.protocols import IMediaAdapter

logger = logging.getLogger("Nexus.Media.TTS")

def clean_text_for_speech(text: str) -> str:
    kaomoji_pattern = r"\([^\u4e00-\u9fa5a-zA-Z0-9]{2,}\)"
    text = re.sub(kaomoji_pattern, "", text)
    text = "".join(c for c in text if c.isalnum() or c in "，。！？、~ ")
    return re.sub(r"([，。！？])\1+", r"\1", text).strip()

class ElevenLabsTTSAdapter:
    def __init__(self):
        self.key = os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
        self.enabled = bool(self.key)

    async def generate(self, text: str, output_path: str) -> bool:
        if not self.enabled: return False
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
            headers = {"xi-api-key": self.key, "Content-Type": "application/json"}
            data = {"text": text, "model_id": "eleven_multilingual_v2"}
            loop = asyncio.get_event_loop()
            def _call():
                res = requests.post(url, json=data, headers=headers)
                if res.status_code == 200:
                    with open(output_path, "wb") as f: f.write(res.content)
                    return True
                return False
            return await loop.run_in_executor(None, _call)
        except Exception: return False

class AzureTTSAdapter:
    def __init__(self):
        self.key = os.getenv("AZURE_SPEECH_KEY")
        self.region = os.getenv("AZURE_SPEECH_REGION", "eastus")
        self.voice = os.getenv("AZURE_TTS_VOICE", "zh-CN-XiaoxiaoNeural")
        self.enabled = bool(self.key and speechsdk)
        self.style_config = {
            "gentle": {"style": "whispering", "rate": "-10%", "pitch": "-5%"},
            "cheerful": {"style": "cheerful", "rate": "+15%", "pitch": "+10%"},
            "sad": {"style": "sad", "rate": "-15%", "pitch": "-10%"},
            "serious": {"style": "professional", "rate": "+5%", "pitch": "-2%"},
            "neutral": {"style": "friendly", "rate": "+0%", "pitch": "0%"}
        }

    async def generate(self, text: str, emotion: str, output_path: str) -> bool:
        if not self.enabled: return False
        config = self.style_config.get(emotion, self.style_config["neutral"])
        ssml = f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' 
               xmlns:mstts='http://www.w3.org/2001/mstts' xml:lang='zh-CN'>
            <voice name='{self.voice}'>
                <mstts:express-as style='{config["style"]}'>
                    <prosody rate='{config["rate"]}' pitch='{config["pitch"]}'>
                        {text}
                    </prosody>
                </mstts:express-as>
            </voice>
        </speak>
        """
        try:
            speech_config = speechsdk.SpeechConfig(subscription=self.key, region=self.region)
            audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: synthesizer.speak_ssml_async(ssml).get())
            return result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted
        except Exception: return False

class EdgeTTSAdapter:
    def __init__(self):
        self.voice = os.getenv("EDGE_TTS_VOICE", "zh-CN-XiaoxiaoNeural")

    async def generate(self, text: str, output_path: str) -> bool:
        if not edge_tts: return False
        try:
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(output_path)
            return True
        except Exception: return False

class HybridTTSAdapter(IMediaAdapter):
    """
    具有快取機制的混合 TTS 適配器。
    """
    def __init__(self):
        self.eleven = ElevenLabsTTSAdapter()
        self.azure = AzureTTSAdapter()
        self.edge = EdgeTTSAdapter()
        self.output_dir = "src/brain/vault/temp_tts"
        self.cache_dir = "src/brain/vault/cache_tts"
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, text: str, emotion: str) -> str:
        """根據文字與情緒內容計算 Hash 作為快取鍵"""
        hash_key = hashlib.mdsize(f"{text}_{emotion}".encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{hash_key}.mp3")

    async def text_to_speech(self, text: str, emotion: str = "neutral") -> str:
        speech_text = clean_text_for_speech(text)
        if not speech_text: return ""
        
        # 1. 檢查快取 (對於常用短語極其有效)
        # 這裡為了簡單，我們先用 hashlib.md5
        hash_key = hashlib.md5(f"{speech_text}_{emotion}".encode()).hexdigest()
        cache_path = os.path.join(self.cache_dir, f"{hash_key}.mp3")
        
        if os.path.exists(cache_path):
            logger.info(f"TTS Cache Hit: {speech_text[:10]}...")
            return cache_path
        
        # 2. 如果沒快取，則生成新音訊
        temp_filename = f"{uuid.uuid4()}.mp3"
        output_path = os.path.join(self.output_dir, temp_filename)
        
        success = False
        if await self.eleven.generate(speech_text, output_path): success = True
        elif await self.azure.generate(speech_text, emotion, output_path): success = True
        elif await self.edge.generate(speech_text, output_path): success = True
        
        if success:
            # 將產出的檔案複製到快取目錄
            import shutil
            os.makedirs(self.cache_dir, exist_ok=True)
            shutil.copy(output_path, cache_path)
            return output_path
            
        return ""

    async def speech_to_text(self, audio_data: bytes) -> str: return ""
