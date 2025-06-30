from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message to send to the AI")


class ChatResponse(BaseModel):
    id: str
    role: Literal["assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)