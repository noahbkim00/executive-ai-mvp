"""Service for generating intelligent follow-up questions for executive search."""

import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage, SystemMessage

from ..models.job_requirements import JobRequirements, SeniorityLevel, FunctionalArea
from ..models.company_info import CompanyInfo
from ..models.conversation import ConversationPhase
from ..prompts.question_generation_prompts import (
    QUESTION_GENERATION_PROMPT,
    QUESTION_VALIDATION_PROMPT
)
from ..prompts.role_specific_templates import RoleSpecificQuestionGenerator
from ..services.conversation_service import ConversationService
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
        
        # Initialize LLMs
        self.generation_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,  # More creative for question generation
            api_key=openai_api_key
        )
        
        self.validation_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,  # Deterministic for validation
            api_key=openai_api_key
        )
        
        self.json_parser = JsonOutputParser()
        self.role_question_generator = RoleSpecificQuestionGenerator()
    
    async def generate_questions(
        self,
        conversation_id: uuid.UUID,
        job_requirements: JobRequirements,
        company_info: CompanyInfo
    ) -> List[Question]:
        """Generate 3-5 follow-up questions based on job and company context."""
        
        try:
            # Prepare context for question generation
            context = self._prepare_context(job_requirements, company_info)
            
            # Generate questions using LLM
            generation_chain = QUESTION_GENERATION_PROMPT | self.generation_llm | self.json_parser
            
            raw_questions = await generation_chain.ainvoke(context)
            
            logger.info(f"Generated {len(raw_questions)} raw questions for conversation {conversation_id}")
            
            # Validate and filter questions
            validated_questions = await self._validate_questions(raw_questions)
            
            # Enhance with role-specific questions if needed
            if len(validated_questions) < 3:
                role_questions = await self._add_role_specific_questions(
                    job_requirements, company_info, validated_questions
                )
                validated_questions.extend(role_questions)
            
            # Limit to 5 questions max
            final_questions = validated_questions[:5]
            
            # Update conversation with total questions
            await self.conversation_service.set_total_questions(
                conversation_id, len(final_questions)
            )
            
            return final_questions
            
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            # Fallback to role-specific questions
            return await self._get_fallback_questions(job_requirements, company_info)
    
    def _prepare_context(
        self, 
        job_requirements: JobRequirements, 
        company_info: CompanyInfo
    ) -> Dict[str, Any]:
        """Prepare context for question generation."""
        
        # Extract initial requirements from additional context
        initial_reqs = job_requirements.additional_context.get(
            "initial_requirements", []
        )
        
        # Format as readable list
        if isinstance(initial_reqs, list):
            initial_requirements_text = "\n".join([f"- {req}" for req in initial_reqs])
        else:
            initial_requirements_text = str(initial_reqs)
        
        return {
            "company_name": company_info.name,
            "industry": company_info.industry.value.replace("_", " ").title(),
            "company_stage": company_info.stage.value.replace("_", " ").title(),
            "business_model": company_info.business_model.value.replace("_", " ").upper(),
            "job_title": job_requirements.title,
            "seniority_level": job_requirements.seniority_level.value.replace("_", " ").upper(),
            "functional_area": job_requirements.functional_area.value.replace("_", " ").title(),
            "initial_requirements": initial_requirements_text or "Not specified",
            "growth_context": company_info.growth_stage_description or "Not specified",
            "key_challenges": "\n".join([f"- {c}" for c in company_info.key_challenges]) if company_info.key_challenges else "Not specified"
        }
    
    async def _validate_questions(self, raw_questions: List[Dict[str, Any]]) -> List[Question]:
        """Validate questions to ensure they don't ask for researchable information."""
        validated = []
        
        for q in raw_questions:
            try:
                # Skip if missing required fields
                if not all(k in q for k in ["question_id", "question", "category", "rationale"]):
                    continue
                
                # Validate using LLM
                validation_chain = QUESTION_VALIDATION_PROMPT | self.validation_llm
                result = await validation_chain.ainvoke({"question": q["question"]})
                
                # Parse validation result
                validation_result = result.content.strip().upper()
                
                if "NOT_RESEARCHABLE" in validation_result:
                    validated.append(Question(
                        question_id=q["question_id"],
                        question=q["question"],
                        category=q["category"],
                        rationale=q["rationale"]
                    ))
                else:
                    logger.info(f"Filtered out researchable question: {q['question']}")
                    
            except Exception as e:
                logger.warning(f"Error validating question: {str(e)}")
                continue
        
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
        
        # Use role-specific templates as fallback
        templates = self.role_question_generator.get_role_specific_questions(
            job_requirements.functional_area,
            job_requirements.seniority_level,
            company_info.stage.value
        )
        
        # Take first 4 questions
        questions = []
        for i, template in enumerate(templates[:4]):
            questions.append(Question(
                question_id=f"fallback_{i+1}",
                question=template,
                category=self._categorize_question(template),
                rationale="Standard question for this role type"
            ))
        
        return questions
    
    async def get_next_question(
        self,
        conversation_id: uuid.UUID
    ) -> Optional[Tuple[Question, int, int]]:
        """Get the next question for a conversation."""
        
        # Get conversation state
        conversation = await self.conversation_service.get_conversation(conversation_id)
        if not conversation:
            return None
        
        # Check if we're in questioning phase
        if conversation.phase != ConversationPhase.QUESTIONING:
            return None
        
        # Check if all questions have been answered
        if conversation.current_question_index >= conversation.total_questions:
            return None
        
        # Get stored questions from metadata
        stored_questions = conversation.metadata.get("questions", [])
        if not stored_questions:
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
            
            return question, current_index + 1, conversation.total_questions
        
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