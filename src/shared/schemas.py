from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4
from typing import Any, Optional, Dict, List
from enum import Enum

class MessageType(str, Enum):
    INPUT = "input"
    THOUGHT = "thought"
    TEXT = "text"
    COMMAND = "command"
    SYSTEM = "system"

class NexusEnvelope(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    source: str
    type: MessageType
    trace_id: str
    session_id: Optional[str] = None
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = {}

    class Config:
        use_enum_values = True

# 以下為各類型的常用 Payload 結構（供參考與驗證使用）
class InputPayload(BaseModel):
    content: str
    platform: str
    raw_data: Optional[Dict[str, Any]] = None

class ThoughtPayload(BaseModel):
    state: str  # thinking | reflecting | searching
    reasoning: str
    context_refs: Optional[List[str]] = None

class TextPayload(BaseModel):
    content: str
    emotion: str = "neutral"
    tts_url: Optional[str] = None

class CommandPayload(BaseModel):
    action: str
    params: Dict[str, Any] = {}
