"""Conversation state management service."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from ..models.conversation import ConversationPhase, ConversationStatus, ConversationState, QuestionResponse
from ..models.db_models import ConversationDB, QuestionResponseDB, JobRequirementsDB, CompanyInfoDB
from ..logger import logger


class ConversationService:
    """Service for managing conversation state and flow"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_conversation(self) -> ConversationState:
        """Create a new conversation"""
        conversation_id = uuid.uuid4()
        
        # Create database record
        db_conversation = ConversationDB(
            id=conversation_id,
            phase=ConversationPhase.INITIAL,
            status=ConversationStatus.ACTIVE,
            current_question_index=0,
            total_questions=0,
            conversation_metadata={}
        )
        
        self.db.add(db_conversation)
        await self.db.commit()
        await self.db.refresh(db_conversation)
        
        logger.info(f"Created new conversation: {conversation_id}")
        
        return ConversationState(
            conversation_id=conversation_id,
            phase=ConversationPhase.INITIAL,
            status=ConversationStatus.ACTIVE,
            current_question_index=0,
            total_questions=0,
            questions_responses=[],
            metadata=db_conversation.conversation_metadata or {},
            created_at=db_conversation.created_at,
            updated_at=db_conversation.updated_at
        )
    
    async def get_conversation(self, conversation_id: uuid.UUID) -> Optional[ConversationState]:
        """Get conversation state by ID"""
        stmt = select(ConversationDB).options(
            selectinload(ConversationDB.questions_responses)
        ).where(ConversationDB.id == conversation_id)
        
        result = await self.db.execute(stmt)
        db_conversation = result.scalar_one_or_none()
        
        if not db_conversation:
            return None
        
        # Convert question responses
        questions_responses = [
            QuestionResponse(
                question_id=qr.question_id,
                question_text=qr.question_text,
                response=qr.response,
                timestamp=qr.timestamp
            )
            for qr in db_conversation.questions_responses
        ]
        
        return ConversationState(
            conversation_id=db_conversation.id,
            phase=ConversationPhase(db_conversation.phase),
            status=ConversationStatus(db_conversation.status),
            current_question_index=db_conversation.current_question_index,
            total_questions=db_conversation.total_questions,
            questions_responses=questions_responses,
            metadata=db_conversation.conversation_metadata or {},
            created_at=db_conversation.created_at,
            updated_at=db_conversation.updated_at
        )
    
    async def update_conversation_phase(
        self, 
        conversation_id: uuid.UUID, 
        phase: ConversationPhase,
        metadata_updates: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update conversation phase"""
        updates = {
            "phase": phase.value,
            "updated_at": datetime.now(timezone.utc)
        }
        
        if metadata_updates:
            # Get current conversation to merge metadata
            current = await self.get_conversation(conversation_id)
            if current:
                merged_metadata = {**current.metadata, **metadata_updates}
                updates["conversation_metadata"] = merged_metadata
        
        stmt = update(ConversationDB).where(
            ConversationDB.id == conversation_id
        ).values(**updates)
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        logger.info(f"Updated conversation {conversation_id} to phase {phase}")
        return result.rowcount > 0
    
    async def add_question_response(
        self,
        conversation_id: uuid.UUID,
        question_id: str,
        question_text: str,
        response: str
    ) -> bool:
        """Add a question-response pair to the conversation"""
        db_response = QuestionResponseDB(
            conversation_id=conversation_id,
            question_id=question_id,
            question_text=question_text,
            response=response,
            timestamp=datetime.now(timezone.utc)
        )
        
        self.db.add(db_response)
        
        # Update conversation question index
        await self.db.execute(
            update(ConversationDB)
            .where(ConversationDB.id == conversation_id)
            .values(
                current_question_index=ConversationDB.current_question_index + 1,
                updated_at=datetime.now(timezone.utc)
            )
        )
        
        await self.db.commit()
        logger.info(f"Added question response to conversation {conversation_id}")
        return True
    
    async def set_total_questions(self, conversation_id: uuid.UUID, total: int) -> bool:
        """Set the total number of questions for the conversation"""
        stmt = update(ConversationDB).where(
            ConversationDB.id == conversation_id
        ).values(
            total_questions=total,
            updated_at=datetime.now(timezone.utc)
        )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        return result.rowcount > 0
    
    async def complete_conversation(self, conversation_id: uuid.UUID) -> bool:
        """Mark conversation as completed"""
        return await self.update_conversation_phase(
            conversation_id, 
            ConversationPhase.COMPLETED,
            {"completed_at": datetime.now(timezone.utc).isoformat()}
        )
    
    async def is_conversation_complete(self, conversation_id: uuid.UUID) -> bool:
        """Check if conversation has answered all questions"""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return False
        
        return (
            conversation.phase == ConversationPhase.COMPLETED or
            (conversation.total_questions > 0 and 
             conversation.current_question_index >= conversation.total_questions)
        )
    
    async def get_conversation_progress(self, conversation_id: uuid.UUID) -> Dict[str, Any]:
        """Get conversation progress information"""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return {}
        
        progress = {
            "phase": conversation.phase.value,
            "status": conversation.status.value,
            "current_question": conversation.current_question_index,
            "total_questions": conversation.total_questions,
            "progress_percentage": 0.0,
            "is_complete": conversation.phase == ConversationPhase.COMPLETED
        }
        
        if conversation.total_questions > 0:
            progress["progress_percentage"] = min(
                100.0, 
                (conversation.current_question_index / conversation.total_questions) * 100
            )
        
        return progress