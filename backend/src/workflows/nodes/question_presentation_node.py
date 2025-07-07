"""Question presentation node for displaying next question to user."""

import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from .base_node import BaseNode
from ..state_schema import ExecutiveSearchState
from ...services.conversation_service import ConversationService
from ...logger import logger


class QuestionPresentationNode(BaseNode):
    """Node for presenting the next question to the user."""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__("question_presentation")
        self.db_session = db_session
        self.conversation_service = ConversationService(db_session)
    
    async def execute(self, state: ExecutiveSearchState) -> ExecutiveSearchState:
        """Present the next question to the user."""
        try:
            logger.info(f"Presenting next question for conversation {state['conversation_id']}")
            
            conversation_id = uuid.UUID(state["conversation_id"])
            
            # Get current conversation state
            conversation = await self.conversation_service.get_conversation(conversation_id)
            if not conversation:
                logger.error(f"Conversation {conversation_id} not found")
                return self._handle_error(state, ValueError("Conversation not found"))
            
            # Get questions from conversation metadata
            stored_questions = conversation.metadata.get("questions", [])
            current_question_index = conversation.current_question_index
            
            
            if current_question_index < len(stored_questions):
                next_question = stored_questions[current_question_index]
                total_questions = len(stored_questions)
                
                logger.info(f"Presenting question {current_question_index + 1} of {total_questions}")
                
                # Prepare response content
                response_content = "Thank you for that information. Here's my next question:" if current_question_index > 0 else "Let me ask you some questions to better understand your needs."
                
                updated_state = self._update_state_metadata(state)
                updated_state.update({
                    "phase": "questioning",
                    "status": "active",
                    "current_question_index": current_question_index,
                    "next_question": {
                        "question_id": next_question["question_id"],
                        "question": next_question["question"],
                        "category": next_question.get("category", "general"),
                        "number": current_question_index + 1,
                        "total": total_questions
                    },
                    "response_content": response_content,
                    "next_action": "wait_for_answer",
                    "progress": {
                        "phase": "questioning",
                        "current_question": current_question_index + 1,
                        "total_questions": total_questions,
                        "progress_percentage": (current_question_index / total_questions) * 100 if total_questions > 0 else 0
                    }
                })
                
                return updated_state
            else:
                logger.warning(f"No more questions available for conversation {conversation_id}")
                return self._handle_error(state, ValueError("No more questions available"))
                
        except Exception as e:
            logger.error(f"Error presenting question: {str(e)}", exc_info=True)
            return self._handle_error(state, e)


def create_question_presentation_node(db_session: AsyncSession) -> QuestionPresentationNode:
    """Factory function to create question presentation node."""
    return QuestionPresentationNode(db_session)