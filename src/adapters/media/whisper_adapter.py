import io
import os
import logging
from typing import Any

# 修正導入邏輯：確保 faster_whisper 變數始終存在
try:
    import faster_whisper
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    faster_whisper = None
    HAS_WHISPER = False

from src.core.protocols import IMediaAdapter

logger = logging.getLogger("Nexus.Media.STT")

class WhisperSTTAdapter(IMediaAdapter):
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self.model = None
        self._load_model()

    def _load_model(self):
        if not HAS_WHISPER:
            logger.error("faster-whisper library not installed.")
            return
            
        try:
            # 優先嘗試載入模型
            self.model = WhisperModel(
                self.model_size, 
                device="cpu", 
                compute_type="int8",
                local_files_only=False
            )
            logger.info(f"Whisper model '{self.model_size}' loaded.")
        except Exception as e:
            logger.error(f"Whisper load error: {e}")
            self.model = None

    async def speech_to_text(self, audio_data: bytes) -> str:
        if not self.model:
            return "Error: 本地語音模型未就緒。"
            
        try:
            audio_file = io.BytesIO(audio_data)
            segments, info = self.model.transcribe(audio_file, beam_size=5)
            full_text = "".join([segment.text for segment in segments])
            return full_text.strip()
        except Exception as e:
            return f"Error converting speech: {str(e)}"

    async def text_to_speech(self, text: str) -> str: return ""
