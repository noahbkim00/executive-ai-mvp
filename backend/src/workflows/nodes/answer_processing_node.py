"""Answer processing node for handling user responses to questions."""

import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from .base_node import BaseNode
from ..state_schema import ExecutiveSearchState
from ...services.conversation_service import ConversationService
from ...logger import logger


class AnswerProcessingNode(BaseNode):
    """Node for processing user answers to questions."""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__("answer_processing")
        self.db_session = db_session
        self.conversation_service = ConversationService(db_session)
    
    async def execute(self, state: ExecutiveSearchState) -> ExecutiveSearchState:
        """Process user's answer and update conversation state."""
        try:
            logger.info(f"Processing answer for conversation {state['conversation_id']}")
            
            conversation_id = uuid.UUID(state["conversation_id"])
            current_message = state["current_message"]
            
            # Get current conversation state
            conversation = await self.conversation_service.get_conversation(conversation_id)
            if not conversation:
                logger.error(f"Conversation {conversation_id} not found")
                return self._handle_error(state, ValueError("Conversation not found"))
            
            # Get current question from stored questions
            current_question_index = conversation.current_question_index
            stored_questions = conversation.metadata.get("questions", [])
            
            if current_question_index < len(stored_questions):
                current_question = stored_questions[current_question_index]
                
                # Store the answer
                await self.conversation_service.add_question_response(
                    conversation_id,
                    current_question["question_id"],
                    current_question["question"],
                    current_message
                )
                
                logger.info(f"Stored answer for question {current_question_index + 1} of {len(stored_questions)}")
                
                # Update state with answer processing results
                updated_state = self._update_state_metadata(state)
                updated_state.update({
                    "current_question_index": current_question_index + 1,
                    "question_responses": state.get("question_responses", []) + [{
                        "question_id": current_question["question_id"],
                        "question": current_question["question"],
                        "answer": current_message,
                        "timestamp": datetime.now().isoformat()
                    }],
                    "next_action": "check_completion"
                })
                
                return updated_state
            else:
                logger.warning(f"Invalid question index {current_question_index} for conversation {conversation_id}")
                return self._handle_error(state, ValueError("Invalid question index"))
                
        except Exception as e:
            logger.error(f"Error processing answer: {str(e)}", exc_info=True)
            return self._handle_error(state, e)


def create_answer_processing_node(db_session: AsyncSession) -> AnswerProcessingNode:
    """Factory function to create answer processing node."""
    return AnswerProcessingNode(db_session)