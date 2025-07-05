"""Service for generating intelligent follow-up questions for executive search."""

import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage, SystemMessage

from ..services.llm_factory import LLMFactory
from ..utils.error_handler import ErrorHandler
from ..exceptions.service_exceptions import QuestionGenerationError

from ..models.job_requirements import JobRequirements, SeniorityLevel, FunctionalArea
from ..models.company_info import CompanyInfo
from ..models.conversation import ConversationPhase
from ..prompts.question_generation_prompts import (
    QUESTION_GENERATION_PROMPT,
    QUESTION_VALIDATION_PROMPT
)
from ..prompts.role_specific_templates import RoleSpecificQuestionGenerator
from ..services.conversation_service import ConversationService
from ..services.company_research_service import CompanyResearchService
from ..logger import logger


class Question:
    """Represents a generated follow-up question."""
    def __init__(self, question_id: str, question: str, category: str, rationale: str):
        self.question_id = question_id
        self.question = question
        self.category = category
        self.rationale = rationale
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "question_id": self.question_id,
            "question": self.question,
            "category": self.category,
            "rationale": self.rationale
        }


class QuestionGenerationService:
    """Service for generating contextual follow-up questions."""
    
    def __init__(self, db_session: AsyncSession, openai_api_key: str):
        self.db = db_session
        self.conversation_service = ConversationService(db_session)
        self.research_service = CompanyResearchService(openai_api_key)
        
        # Initialize LLMs using factory
        self.generation_llm = LLMFactory.create_generation_llm()
        self.validation_llm = LLMFactory.create_validation_llm()
        
        self.json_parser = JsonOutputParser()
        self.role_question_generator = RoleSpecificQuestionGenerator()
    
    async def generate_questions(
        self,
        conversation_id: uuid.UUID,
        job_requirements: JobRequirements,
        company_info: CompanyInfo
    ) -> List[Question]:
        """Generate 3-5 follow-up questions based on company research and context."""
        
        logger.info(f"Starting question generation for conversation {conversation_id}")
        logger.debug(f"Job: {job_requirements.title} at {company_info.name}")
        
        try:
            # First, conduct company research
            logger.info(f"Initiating company research for {company_info.name}...")
            company_research = await self.research_service.research_company(
                company_info.name,
                job_requirements.title
            )
            
            logger.info(f"Company research completed for {company_info.name} with confidence {company_research.research_confidence}")
            
            # Get research insights
            insights = self.research_service.get_research_insights(company_research, job_requirements.title)
            logger.debug(f"Research insights extracted: {len(insights)} categories")
            
            # Prepare context for question generation
            context = self._prepare_research_context(job_requirements, company_info, company_research, insights)
            logger.debug(f"Context prepared with {len(context)} fields")
            
            # Generate questions using LLM with research context
            logger.info("Generating questions using LLM...")
            generation_chain = QUESTION_GENERATION_PROMPT | self.generation_llm | self.json_parser
            
            raw_questions = await generation_chain.ainvoke(context)
            
            logger.info(f"Generated {len(raw_questions)} research-driven questions for conversation {conversation_id}")
            for i, q in enumerate(raw_questions):
                logger.debug(f"  Question {i+1}: {q.get('question', 'N/A')[:80]}...")
            
            # Validate and filter questions
            logger.info("Validating generated questions...")
            validated_questions = await self._validate_questions(raw_questions)
            logger.info(f"Validated {len(validated_questions)} questions (filtered {len(raw_questions) - len(validated_questions)})")
            
            # Enhance with role-specific questions if needed
            if len(validated_questions) < 3:
                logger.warning(f"Only {len(validated_questions)} valid questions, adding role-specific questions...")
                role_questions = await self._add_role_specific_questions(
                    job_requirements, company_info, validated_questions
                )
                validated_questions.extend(role_questions)
                logger.info(f"Added {len(role_questions)} role-specific questions")
            
            # Limit to 5 questions max
            final_questions = validated_questions[:5]
            logger.info(f"Final question count: {len(final_questions)}")
            
            # Update conversation with total questions
            await self.conversation_service.set_total_questions(
                conversation_id, len(final_questions)
            )
            
            return final_questions
            
        except Exception as e:
            # Use standardized error handling with fallback
            return await ErrorHandler.handle_with_fallback_async(
                operation=lambda: self._raise_error(e),
                fallback_fn=lambda: self._get_fallback_questions(job_requirements, company_info),
                error_message=f"Error generating questions for conversation {conversation_id}",
                logger=logger,
                raise_on_fallback_failure=True
            )
    
    async def _raise_error(self, e: Exception):
        """Helper to re-raise exception for error handler."""
        raise e
    
    def _prepare_research_context(
        self, 
        job_requirements: JobRequirements, 
        company_info: CompanyInfo,
        company_research,
        insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare research-enhanced context for question generation."""
        
        return {
            "company_name": company_research.company_name,
            "industry": company_research.industry,
            "funding_stage": company_research.funding_stage.value,
            "company_size": company_research.company_size.value,
            "competitors": ", ".join(company_research.key_competitors[:3]) if company_research.key_competitors else "Not identified",
            "recent_developments": "; ".join(company_research.recent_developments[:2]) if company_research.recent_developments else "Not available",
            "regulatory_environment": company_research.regulatory_environment or "Standard business environment",
            "job_title": job_requirements.title,
            "seniority_level": job_requirements.seniority_level.value.replace("_", " ").title(),
            "functional_area": job_requirements.functional_area.value.replace("_", " ").title(),
            "stage_insights": "; ".join(insights.get("stage_insights", [])),
            "industry_insights": "; ".join(insights.get("industry_insights", [])),
            "competitive_insights": "; ".join(insights.get("competitive_insights", [])),
            "leadership_needs": "; ".join(insights.get("leadership_insights", [])),
            "ipo_insights": "; ".join(insights.get("ipo_insights", [])) if insights.get("ipo_insights") else "Not applicable"
        }
    
    async def _validate_questions(self, raw_questions: List[Dict[str, Any]]) -> List[Question]:
        """Validate questions to ensure they don't ask for researchable information."""
        validated = []
        
        logger.debug(f"Validating {len(raw_questions)} questions...")
        
        for i, q in enumerate(raw_questions):
            try:
                # Skip if missing required fields
                if not all(k in q for k in ["question_id", "question", "category", "rationale"]):
                    missing_fields = [k for k in ["question_id", "question", "category", "rationale"] if k not in q]
                    logger.warning(f"Question {i+1} missing required fields: {missing_fields}")
                    continue
                
                # Validate using LLM
                logger.debug(f"Validating question {i+1}: {q['question'][:50]}...")
                validation_chain = QUESTION_VALIDATION_PROMPT | self.validation_llm
                result = await validation_chain.ainvoke({"question": q["question"]})
                
                # Parse validation result
                validation_result = result.content.strip().upper()
                logger.debug(f"Validation result for question {i+1}: {validation_result[:50]}")
                
                if "APPROPRIATE" in validation_result:
                    validated.append(Question(
                        question_id=q["question_id"],
                        question=q["question"],
                        category=q["category"],
                        rationale=q["rationale"]
                    ))
                    logger.debug(f"Question {i+1} validated successfully")
                else:
                    logger.info(f"Filtered out inappropriate question: {q['question']}")
                    logger.debug(f"Reason: {validation_result}")
                    
            except Exception as e:
                logger.error(f"Error validating question {i+1}: {str(e)}", exc_info=True)
                continue
        
        logger.info(f"Validation complete: {len(validated)} of {len(raw_questions)} questions passed")
        return validated
    
    async def _add_role_specific_questions(
        self,
        job_requirements: JobRequirements,
        company_info: CompanyInfo,
        existing_questions: List[Question]
    ) -> List[Question]:
        """Add role-specific questions to reach minimum count."""
        
        # Get role-specific question templates
        templates = self.role_question_generator.get_role_specific_questions(
            job_requirements.functional_area,
            job_requirements.seniority_level,
            company_info.stage.value
        )
        
        # Filter out questions similar to existing ones
        existing_texts = [q.question.lower() for q in existing_questions]
        unique_templates = [
            t for t in templates 
            if not any(existing.replace(" ", "") in t.lower().replace(" ", "") 
                      for existing in existing_texts)
        ]
        
        # Create Question objects
        additional_questions = []
        for i, template in enumerate(unique_templates[:2]):  # Add up to 2 more
            additional_questions.append(Question(
                question_id=f"role_{i+1}",
                question=template,
                category=self._categorize_question(template),
                rationale="Role-specific question based on functional area and seniority"
            ))
        
        return additional_questions
    
    def _categorize_question(self, question_text: str) -> str:
        """Categorize a question based on its content."""
        question_lower = question_text.lower()
        
        if any(word in question_lower for word in ["lead", "team", "manage", "culture"]):
            return "leadership"
        elif any(word in question_lower for word in ["experience", "background", "track record"]):
            return "experience"
        elif any(word in question_lower for word in ["salary", "compensation", "equity"]):
            return "compensation"
        elif any(word in question_lower for word in ["technical", "stack", "architecture"]):
            return "expertise"
        elif any(word in question_lower for word in ["why", "motivation", "goal"]):
            return "motivation"
        else:
            return "culture"
    
    async def _get_fallback_questions(
        self,
        job_requirements: JobRequirements,
        company_info: CompanyInfo
    ) -> List[Question]:
        """Get fallback questions if generation fails."""
        
        logger.warning(f"Using fallback questions for {job_requirements.title} at {company_info.name}")
        
        # Use role-specific templates as fallback
        templates = self.role_question_generator.get_role_specific_questions(
            job_requirements.functional_area,
            job_requirements.seniority_level,
            company_info.stage.value
        )
        
        logger.info(f"Found {len(templates)} role-specific templates")
        
        # Take first 4 questions
        questions = []
        for i, template in enumerate(templates[:4]):
            questions.append(Question(
                question_id=f"fallback_{i+1}",
                question=template,
                category=self._categorize_question(template),
                rationale="Standard question for this role type"
            ))
            logger.debug(f"Fallback question {i+1}: {template[:60]}...")
        
        logger.info(f"Created {len(questions)} fallback questions")
        return questions
    
    async def get_next_question(
        self,
        conversation_id: uuid.UUID
    ) -> Optional[Tuple[Question, int, int]]:
        """Get the next question for a conversation."""
        
        logger.debug(f"Getting next question for conversation {conversation_id}")
        
        # Get conversation state
        conversation = await self.conversation_service.get_conversation(conversation_id)
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found")
            return None
        
        # Check if we're in questioning phase
        if conversation.phase != ConversationPhase.QUESTIONING:
            logger.info(f"Conversation {conversation_id} not in questioning phase (current: {conversation.phase})")
            return None
        
        # Check if all questions have been answered
        if conversation.current_question_index >= conversation.total_questions:
            logger.info(f"All questions answered for conversation {conversation_id} ({conversation.current_question_index}/{conversation.total_questions})")
            return None
        
        # Get stored questions from metadata
        stored_questions = conversation.metadata.get("questions", [])
        if not stored_questions:
            logger.error(f"No questions found in metadata for conversation {conversation_id}")
            return None
        
        # Get current question
        current_index = conversation.current_question_index
        if current_index < len(stored_questions):
            question_data = stored_questions[current_index]
            question = Question(
                question_id=question_data["question_id"],
                question=question_data["question"],
                category=question_data["category"],
                rationale=question_data["rationale"]
            )
            
            logger.info(f"Returning question {current_index + 1} of {conversation.total_questions} for conversation {conversation_id}")
            logger.debug(f"Question: {question.question[:80]}...")
            
            return question, current_index + 1, conversation.total_questions
        
        logger.error(f"Current index {current_index} out of bounds for {len(stored_questions)} questions")
        return None
    
    async def store_questions_in_conversation(
        self,
        conversation_id: uuid.UUID,
        questions: List[Question]
    ) -> bool:
        """Store generated questions in conversation metadata."""
        
        # Convert questions to dict format
        questions_data = [q.to_dict() for q in questions]
        
        # Update conversation metadata
        return await self.conversation_service.update_conversation_phase(
            conversation_id,
            ConversationPhase.QUESTIONING,
            {"questions": questions_data, "questions_generated_at": datetime.now(timezone.utc).isoformat()}
        )