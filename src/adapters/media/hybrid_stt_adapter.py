import os
import io
import logging
import asyncio
from typing import Optional
import tempfile

try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:
    speechsdk = None

from src.core.protocols import IMediaAdapter
from src.adapters.media.whisper_adapter import WhisperSTTAdapter

logger = logging.getLogger("Nexus.Media.STT")

class AzureSTTAdapter:
    """
    Azure Speech-to-Text 適配器 (具備 SDK 實作)。
    """
    def __init__(self):
        self.key = os.getenv("AZURE_SPEECH_KEY")
        self.region = os.getenv("AZURE_SPEECH_REGION", "eastus")
        self.enabled = bool(self.key and speechsdk)

    async def speech_to_text(self, audio_data: bytes) -> str:
        if not self.enabled:
            return ""
            
        try:
            # 將 bytes 儲存為暫存檔，因為 Azure SDK 偏好讀取檔案
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name

            speech_config = speechsdk.SpeechConfig(subscription=self.key, region=self.region)
            speech_config.speech_recognition_language = "zh-CN"
            audio_config = speechsdk.audio.AudioConfig(filename=tmp_path)
            
            recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
            
            # 使用同步方法在 executor 中執行，以免阻塞事件循環
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, recognizer.recognize_once_async)
            
            # 清理暫存檔
            os.remove(tmp_path)

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                return result.text
            else:
                logger.warning(f"Azure STT failed or silent: {result.reason}")
                return ""
        except Exception as e:
            logger.error(f"Azure STT Exception: {e}")
            return ""

class HybridSTTAdapter(IMediaAdapter):
    def __init__(self, local_model_size: str = "base"):
        self.cloud_adapter = AzureSTTAdapter()
        self.local_adapter = WhisperSTTAdapter(model_size=local_model_size)

    async def speech_to_text(self, audio_data: bytes) -> str:
        if self.cloud_adapter.enabled:
            result = await self.cloud_adapter.speech_to_text(audio_data)
            if result:
                return f"[Azure] {result}"
        
        logger.info("Falling back to local Whisper STT...")
        return await self.local_adapter.speech_to_text(audio_data)

    async def text_to_speech(self, text: str) -> str:
        return ""
