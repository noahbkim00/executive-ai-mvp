"""Question generation node for LangGraph workflow."""

import asyncio
from typing import Dict, Any, List
from datetime import datetime
from langgraph.prebuilt import ToolExecutor

from ..state_schema import ExecutiveSearchState
from .base_node import BaseNode
from ..tools.question_generation_tools import (
    generate_research_driven_questions,
    validate_questions_batch,
    generate_role_specific_questions,
    generate_fallback_questions,
    QUESTION_GENERATION_TOOLS
)
from ...services.conversation_service import ConversationService
from ...models.conversation import ConversationPhase
from ...logger import logger


class QuestionGenerationNode(BaseNode):
    """LangGraph node for question generation."""
    
    def __init__(self, db_session):
        """Initialize the question generation node."""
        super().__init__("question_generation")
        self.db_session = db_session
        self.conversation_service = ConversationService(db_session)
        
        # Initialize tool executor with question generation tools
        self.tool_executor = ToolExecutor(QUESTION_GENERATION_TOOLS)
    
    async def execute(self, state: ExecutiveSearchState) -> ExecutiveSearchState:
        """Execute question generation logic."""
        try:
            logger.info(f"Starting question generation for conversation {state['conversation_id']}")
            
            # Extract required data from state
            job_requirements = state.get("job_requirements")
            company_info = state.get("company_info")
            company_research = state.get("company_research")
            research_insights = state.get("research_insights")
            conversation_id = state.get("conversation_id")
            
            if not job_requirements or not company_info:
                logger.error("Missing job requirements or company info for question generation")
                return self._handle_error(state, ValueError("Missing job requirements or company info"))
            
            # Generate questions using the same logic as the service
            questions = await self._generate_questions(
                job_requirements,
                company_info,
                company_research,
                research_insights
            )
            
            # Store questions in conversation metadata
            await self._store_questions_in_conversation(conversation_id, questions)
            
            # Update state with generated questions
            updated_state = self._update_state_metadata(state)
            updated_state.update({
                "questions": [q for q in questions],
                "next_action": "start_questioning",
                "error_message": None
            })
            
            logger.info(f"Question generation completed for conversation {conversation_id} - generated {len(questions)} questions")
            return updated_state
            
        except Exception as e:
            logger.error(f"Error in question generation: {str(e)}", exc_info=True)
            return self._handle_error(state, e)
    
    async def _generate_questions(
        self,
        job_requirements: Dict[str, Any],
        company_info: Dict[str, Any],
        company_research: Dict[str, Any],
        research_insights: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate questions using the same logic as QuestionGenerationService."""
        
        logger.info(f"Generating questions for {job_requirements.get('title', 'Unknown')} at {company_info.get('name', 'Unknown')}")
        
        try:
            # Step 1: Generate research-driven questions
            logger.info("Generating research-driven questions...")
            research_result = await generate_research_driven_questions.ainvoke({
                "job_requirements": job_requirements,
                "company_info": company_info,
                "research_insights": research_insights or {},
                "company_research": company_research or {}
            })
            
            raw_questions = research_result.get("questions", [])
            logger.info(f"Generated {len(raw_questions)} research-driven questions")
            
            # Step 2: Validate questions
            logger.info("Validating generated questions...")
            validation_result = await validate_questions_batch(raw_questions)
            
            validated_questions = validation_result.get("validated_questions", [])
            logger.info(f"Validated {len(validated_questions)} questions (filtered {len(raw_questions) - len(validated_questions)})")
            
            # Step 3: Add role-specific questions if needed
            if len(validated_questions) < 3:
                logger.warning(f"Only {len(validated_questions)} valid questions, adding role-specific questions...")
                role_result = await generate_role_specific_questions.ainvoke({
                    "job_requirements": job_requirements,
                    "company_info": company_info,
                    "existing_questions": validated_questions
                })
                
                role_questions = role_result.get("role_questions", [])
                validated_questions.extend(role_questions)
                logger.info(f"Added {len(role_questions)} role-specific questions")
            
            # Step 4: Limit to 5 questions max
            final_questions = validated_questions[:5]
            logger.info(f"Final question count: {len(final_questions)}")
            
            return final_questions
            
        except Exception as e:
            logger.error(f"Error in question generation, falling back to fallback questions: {str(e)}", exc_info=True)
            
            # Fallback to role-specific questions
            try:
                fallback_result = await generate_fallback_questions.ainvoke({
                    "job_requirements": job_requirements,
                    "company_info": company_info
                })
                
                fallback_questions = fallback_result.get("fallback_questions", [])
                logger.info(f"Using {len(fallback_questions)} fallback questions")
                return fallback_questions
                
            except Exception as fallback_error:
                logger.error(f"Fallback question generation also failed: {str(fallback_error)}", exc_info=True)
                # Return minimal default questions
                return self._get_minimal_fallback_questions(job_requirements, company_info)
    
    def _get_minimal_fallback_questions(
        self,
        job_requirements: Dict[str, Any],
        company_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get minimal fallback questions when all generation methods fail."""
        
        logger.warning("Using minimal fallback questions due to generation failures")
        
        job_title = job_requirements.get("title", "Executive")
        company_name = company_info.get("name", "the company")
        
        minimal_questions = [
            {
                "question_id": "minimal_1",
                "question": f"What specific experience is most important for this {job_title} role at {company_name}?",
                "category": "experience",
                "rationale": "Essential experience requirements question"
            },
            {
                "question_id": "minimal_2",
                "question": f"What leadership qualities are critical for success in this {job_title} position?",
                "category": "leadership",
                "rationale": "Core leadership requirements question"
            },
            {
                "question_id": "minimal_3",
                "question": f"What would be considered a successful outcome for this {job_title} in the first 90 days?",
                "category": "success_criteria",
                "rationale": "Success metrics and expectations question"
            }
        ]
        
        logger.info(f"Created {len(minimal_questions)} minimal fallback questions")
        return minimal_questions
    
    async def _store_questions_in_conversation(
        self,
        conversation_id: str,
        questions: List[Dict[str, Any]]
    ) -> bool:
        """Store generated questions in conversation metadata."""
        
        try:
            # Convert conversation_id to UUID
            import uuid
            conversation_uuid = uuid.UUID(conversation_id)
            
            # Update conversation metadata with questions
            success = await self.conversation_service.update_conversation_phase(
                conversation_uuid,
                ConversationPhase.QUESTIONING,
                {
                    "questions": questions,
                    "questions_generated_at": datetime.now().isoformat(),
                    "langgraph_question_generation": True
                }
            )
            
            # Set total questions count
            await self.conversation_service.set_total_questions(
                conversation_uuid, len(questions)
            )
            
            logger.info(f"Stored {len(questions)} questions in conversation {conversation_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error storing questions in conversation {conversation_id}: {str(e)}", exc_info=True)
            return False


# Factory function for node creation
def create_question_generation_node(db_session) -> QuestionGenerationNode:
    """Factory function to create question generation node."""
    return QuestionGenerationNode(db_session)