"""Completion check node for determining if conversation is complete."""

import uuid
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from .base_node import BaseNode
from ..state_schema import ExecutiveSearchState
from ...services.conversation_service import ConversationService
from ...models.conversation import ConversationPhase
from ...logger import logger


class CompletionCheckNode(BaseNode):
    """Node for checking if conversation is complete."""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__("completion_check")
        self.db_session = db_session
        self.conversation_service = ConversationService(db_session)
    
    async def execute(self, state: ExecutiveSearchState) -> ExecutiveSearchState:
        """Check if all questions have been answered."""
        try:
            logger.info(f"Checking completion for conversation {state['conversation_id']}")
            
            conversation_id = uuid.UUID(state["conversation_id"])
            
            # Get current conversation state
            conversation = await self.conversation_service.get_conversation(conversation_id)
            if not conversation:
                logger.error(f"Conversation {conversation_id} not found")
                return self._handle_error(state, ValueError("Conversation not found"))
            
            # Check if all questions have been answered
            questions_answered = conversation.current_question_index
            total_questions = conversation.total_questions
            
            logger.info(f"Questions answered: {questions_answered}/{total_questions}")
            
            if questions_answered >= total_questions:
                # All questions answered - mark as complete
                logger.info(f"All questions answered for conversation {conversation_id}")
                
                # Update conversation to completed phase
                await self.conversation_service.complete_conversation(conversation_id)
                
                updated_state = self._update_state_metadata(state)
                updated_state.update({
                    "phase": "completed",
                    "status": "completed",
                    "is_complete": True,
                    "next_action": "generate_summary",
                    "progress": {
                        "phase": "completed",
                        "current_question": total_questions,
                        "total_questions": total_questions,
                        "progress_percentage": 100.0
                    }
                })
                
                return updated_state
            else:
                # More questions to ask
                logger.info(f"More questions remaining for conversation {conversation_id}")
                
                updated_state = self._update_state_metadata(state)
                updated_state.update({
                    "next_action": "present_next_question",
                    "current_question_index": questions_answered,
                    "progress": {
                        "phase": "questioning",
                        "current_question": questions_answered + 1,
                        "total_questions": total_questions,
                        "progress_percentage": (questions_answered / total_questions) * 100 if total_questions > 0 else 0
                    }
                })
                
                return updated_state
                
        except Exception as e:
            logger.error(f"Error checking completion: {str(e)}", exc_info=True)
            return self._handle_error(state, e)


def create_completion_check_node(db_session: AsyncSession) -> CompletionCheckNode:
    """Factory function to create completion check node."""
    return CompletionCheckNode(db_session)