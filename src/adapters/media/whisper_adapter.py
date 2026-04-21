import io
import os
import logging
from typing import Any
try:
    from faster_whisper import WhisperModel
except ImportError:
    faster_whisper = None

from src.core.protocols import IMediaAdapter

logger = logging.getLogger("Nexus.Media.STT")

class WhisperSTTAdapter(IMediaAdapter):
    """
    基於 Faster-Whisper 的本地語音辨識適配器。
    """
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self.model = None
        # 預延遲載入模型
        self._load_model()

    def _load_model(self):
        try:
            # 優先使用 CUDA，若無則降級到 CPU
            # compute_type="int8" 可以在不損失太多準確度的情況下大幅提升 CPU 速度
            self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            logger.info(f"Whisper model '{self.model_size}' loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")

    async def speech_to_text(self, audio_data: bytes) -> str:
        """
        將原始音訊位元組轉換為文字。
        支援主流格式 (wav, mp3, etc.)
        """
        if not self.model:
            return "Error: STT model not loaded."
            
        try:
            # 將 bytes 轉為類檔案對象
            audio_file = io.BytesIO(audio_data)
            
            # 執行辨識
            segments, info = self.model.transcribe(audio_file, beam_size=5)
            
            # 合併所有片段
            full_text = "".join([segment.text for segment in segments])
            
            logger.info(f"STT Completed (Lang: {info.language}): {full_text[:30]}...")
            return full_text.strip()
            
        except Exception as e:
            logger.error(f"STT Conversion Error: {e}")
            return f"Error converting speech: {str(e)}"

    async def text_to_speech(self, text: str) -> str:
        """(此適配器暫不負責 TTS)"""
        return ""
