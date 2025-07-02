from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class ConversationPhase(str, Enum):
    """Phases of the executive search conversation flow"""
    INITIAL = "initial"           # Collecting basic job requirements
    QUESTIONING = "questioning"   # Asking follow-up questions
    COMPLETED = "completed"       # All information collected
    ERROR = "error"              # Error state


class ConversationStatus(str, Enum):
    """Status of the conversation"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class QuestionResponse(BaseModel):
    """Response to a follow-up question"""
    question_id: str
    question_text: str
    response: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationState(BaseModel):
    """Current state of a conversation"""
    conversation_id: UUID = Field(default_factory=uuid4)
    phase: ConversationPhase = ConversationPhase.INITIAL
    status: ConversationStatus = ConversationStatus.ACTIVE
    current_question_index: int = 0
    total_questions: int = 0
    questions_responses: List[QuestionResponse] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationRequest(BaseModel):
    """Request to update conversation state"""
    conversation_id: Optional[UUID] = None
    message: str = Field(..., min_length=1)
    phase: Optional[ConversationPhase] = None


class ConversationResponse(BaseModel):
    """Response from conversation service"""
    conversation_id: UUID
    phase: ConversationPhase
    status: ConversationStatus
    response_content: str
    progress: Dict[str, Any] = Field(default_factory=dict)  # Progress indicators
    next_question: Optional[str] = None
    is_complete: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationSummary(BaseModel):
    """Summary of completed conversation"""
    conversation_id: UUID
    phase: ConversationPhase
    status: ConversationStatus
    total_messages: int
    questions_asked: int
    questions_answered: int
    duration_minutes: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None