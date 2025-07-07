"""Summary generation node for creating completion summary."""

import uuid
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from .base_node import BaseNode
from ..state_schema import ExecutiveSearchState
from ...services.conversation_service import ConversationService
from ...logger import logger


class SummaryGenerationNode(BaseNode):
    """Node for generating conversation completion summary."""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__("summary_generation")
        self.db_session = db_session
        self.conversation_service = ConversationService(db_session)
    
    async def execute(self, state: ExecutiveSearchState) -> ExecutiveSearchState:
        """Generate completion summary for the conversation."""
        try:
            logger.info(f"Generating summary for conversation {state['conversation_id']}")
            
            conversation_id = uuid.UUID(state["conversation_id"])
            
            # Get current conversation state
            conversation = await self.conversation_service.get_conversation(conversation_id)
            if not conversation:
                logger.error(f"Conversation {conversation_id} not found")
                return self._handle_error(state, ValueError("Conversation not found"))
            
            # Generate completion message
            total_questions = conversation.total_questions
            completion_message = (
                f"Thank you for providing all that valuable information! "
                f"I now have a comprehensive understanding of your requirements after answering {total_questions} questions. "
                f"Your background search has begun, and we will notify you when we have identified potential candidates "
                f"that match your specific needs."
            )
            
            logger.info(f"Generated completion summary for conversation {conversation_id}")
            
            updated_state = self._update_state_metadata(state)
            updated_state.update({
                "phase": "completed",
                "status": "completed",
                "is_complete": True,
                "response_content": completion_message,
                "next_action": None,
                "progress": {
                    "phase": "completed",
                    "current_question": total_questions,
                    "total_questions": total_questions,
                    "progress_percentage": 100.0
                },
                "summary": {
                    "total_questions_answered": total_questions,
                    "completion_time": datetime.now().isoformat(),
                    "status": "completed"
                }
            })
            
            return updated_state
                
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}", exc_info=True)
            return self._handle_error(state, e)


def create_summary_generation_node(db_session: AsyncSession) -> SummaryGenerationNode:
    """Factory function to create summary generation node."""
    return SummaryGenerationNode(db_session)