"""Question generation tools for LangGraph workflow."""

import json
import uuid
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ...services.llm_factory import LLMFactory
from ...models.job_requirements import JobRequirements, SeniorityLevel, FunctionalArea
from ...models.company_info import CompanyInfo
from ...prompts.question_generation_prompts import (
    QUESTION_GENERATION_PROMPT,
    QUESTION_VALIDATION_PROMPT
)
from ...prompts.role_specific_templates import RoleSpecificQuestionGenerator
from ...logger import logger


class QuestionData:
    """Data structure for a generated question."""
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


@tool
async def generate_research_driven_questions(
    job_requirements: Dict[str, Any],
    company_info: Dict[str, Any],
    research_insights: Dict[str, Any],
    company_research: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate research-driven questions based on company research and insights."""
    logger.info(f"Generating research-driven questions for {company_info.get('name', 'Unknown')} - {job_requirements.get('title', 'Unknown role')}")
    
    try:
        # Initialize LLM and parser
        generation_llm = LLMFactory.create_generation_llm()
        json_parser = JsonOutputParser()
        
        # Prepare context for question generation (identical to service)
        context = {
            "company_name": company_research.get("company_name", "Unknown"),
            "industry": company_research.get("industry", "Unknown"),
            "funding_stage": company_research.get("funding_stage", "unknown"),
            "company_size": company_research.get("company_size", "unknown"),
            "competitors": ", ".join(company_research.get("key_competitors", [])[:3]) if company_research.get("key_competitors") else "Not identified",
            "recent_developments": "; ".join(company_research.get("recent_developments", [])[:2]) if company_research.get("recent_developments") else "Not available",
            "regulatory_environment": company_research.get("regulatory_environment", "Standard business environment"),
            "job_title": job_requirements.get("title", "Executive"),
            "seniority_level": job_requirements.get("seniority_level", "unknown").replace("_", " ").title(),
            "functional_area": job_requirements.get("functional_area", "unknown").replace("_", " ").title(),
            "stage_insights": "; ".join(research_insights.get("stage_insights", [])),
            "industry_insights": "; ".join(research_insights.get("industry_insights", [])),
            "competitive_insights": "; ".join(research_insights.get("competitive_insights", [])),
            "leadership_needs": "; ".join(research_insights.get("leadership_insights", [])),
            "ipo_insights": "; ".join(research_insights.get("ipo_insights", [])) if research_insights.get("ipo_insights") else "Not applicable"
        }
        
        # Generate questions using LLM with research context
        logger.info("Generating questions using LLM...")
        generation_chain = QUESTION_GENERATION_PROMPT | generation_llm | json_parser
        
        raw_questions = await generation_chain.ainvoke(context)
        
        logger.info(f"Generated {len(raw_questions)} research-driven questions")
        for i, q in enumerate(raw_questions):
            logger.debug(f"  Question {i+1}: {q.get('question', 'N/A')[:80]}...")
        
        return {
            "questions": raw_questions,
            "context": context,
            "generation_method": "research_driven"
        }
        
    except Exception as e:
        logger.error(f"Error generating research-driven questions: {str(e)}", exc_info=True)
        return {
            "questions": [],
            "context": {},
            "generation_method": "research_driven",
            "error": str(e)
        }


async def validate_questions_batch(questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate questions to ensure they don't ask for researchable information."""
    logger.info(f"Validating {len(questions)} questions...")
    
    validated_questions = []
    validation_results = []
    
    # Initialize LLM
    validation_llm = LLMFactory.create_validation_llm()
    
    for i, q in enumerate(questions):
        try:
            # Skip if missing required fields
            if not all(k in q for k in ["question_id", "question", "category", "rationale"]):
                missing_fields = [k for k in ["question_id", "question", "category", "rationale"] if k not in q]
                logger.warning(f"Question {i+1} missing required fields: {missing_fields}")
                validation_results.append({
                    "question_id": q.get("question_id", f"q{i+1}"),
                    "question": q.get("question", ""),
                    "result": "INVALID",
                    "reason": f"Missing fields: {missing_fields}"
                })
                continue
            
            # Validate using LLM
            logger.debug(f"Validating question {i+1}: {q['question'][:50]}...")
            validation_chain = QUESTION_VALIDATION_PROMPT | validation_llm
            result = await validation_chain.ainvoke({"question": q["question"]})
            
            # Parse validation result
            validation_result = result.content.strip().upper()
            logger.debug(f"Validation result for question {i+1}: {validation_result[:50]}")
            
            if "APPROPRIATE" in validation_result:
                validated_questions.append({
                    "question_id": q["question_id"],
                    "question": q["question"],
                    "category": q["category"],
                    "rationale": q["rationale"]
                })
                validation_results.append({
                    "question_id": q["question_id"],
                    "question": q["question"],
                    "result": "VALID",
                    "reason": "Appropriate for client intake"
                })
                logger.debug(f"Question {i+1} validated successfully")
            else:
                validation_results.append({
                    "question_id": q["question_id"],
                    "question": q["question"],
                    "result": "INVALID",
                    "reason": validation_result
                })
                logger.info(f"Filtered out inappropriate question: {q['question']}")
                logger.debug(f"Reason: {validation_result}")
                
        except Exception as e:
            logger.error(f"Error validating question {i+1}: {str(e)}", exc_info=True)
            validation_results.append({
                "question_id": q.get("question_id", f"q{i+1}"),
                "question": q.get("question", ""),
                "result": "ERROR",
                "reason": str(e)
            })
            continue
    
    logger.info(f"Validation complete: {len(validated_questions)} of {len(questions)} questions passed")
    
    return {
        "validated_questions": validated_questions,
        "validation_results": validation_results,
        "total_input": len(questions),
        "total_valid": len(validated_questions),
        "filtered_count": len(questions) - len(validated_questions)
    }


@tool
async def generate_role_specific_questions(
    job_requirements: Dict[str, Any],
    company_info: Dict[str, Any],
    existing_questions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generate role-specific questions to supplement validated questions."""
    logger.info(f"Generating role-specific questions for {job_requirements.get('title', 'Unknown')} role")
    
    try:
        # Initialize role question generator
        role_generator = RoleSpecificQuestionGenerator()
        
        # Map string values to enum values
        functional_area_map = {
            "sales": FunctionalArea.SALES,
            "engineering": FunctionalArea.ENGINEERING,
            "marketing": FunctionalArea.MARKETING,
            "product": FunctionalArea.PRODUCT,
            "finance": FunctionalArea.FINANCE,
            "operations": FunctionalArea.OPERATIONS
        }
        
        seniority_level_map = {
            "c_suite": SeniorityLevel.C_SUITE,
            "evp": SeniorityLevel.EVP,
            "svp": SeniorityLevel.SVP,
            "vp": SeniorityLevel.VP,
            "director": SeniorityLevel.DIRECTOR
        }
        
        # Get enum values
        functional_area = functional_area_map.get(
            job_requirements.get("functional_area", "").lower(),
            FunctionalArea.SALES
        )
        
        seniority_level = seniority_level_map.get(
            job_requirements.get("seniority_level", "").lower(),
            SeniorityLevel.VP
        )
        
        # Get role-specific question templates
        templates = role_generator.get_role_specific_questions(
            functional_area,
            seniority_level,
            company_info.get("stage", "unknown")
        )
        
        # Filter out questions similar to existing ones
        existing_texts = [q.get("question", "").lower() for q in existing_questions]
        unique_templates = [
            t for t in templates 
            if not any(existing.replace(" ", "") in t.lower().replace(" ", "") 
                      for existing in existing_texts)
        ]
        
        # Create question objects
        role_questions = []
        for i, template in enumerate(unique_templates[:2]):  # Add up to 2 more
            question_id = f"role_{i+1}"
            category = _categorize_question(template)
            
            role_questions.append({
                "question_id": question_id,
                "question": template,
                "category": category,
                "rationale": "Role-specific question based on functional area and seniority"
            })
        
        logger.info(f"Generated {len(role_questions)} role-specific questions")
        
        return {
            "role_questions": role_questions,
            "total_templates": len(templates),
            "unique_templates": len(unique_templates),
            "selected_count": len(role_questions)
        }
        
    except Exception as e:
        logger.error(f"Error generating role-specific questions: {str(e)}", exc_info=True)
        return {
            "role_questions": [],
            "total_templates": 0,
            "unique_templates": 0,
            "selected_count": 0,
            "error": str(e)
        }


@tool
async def generate_fallback_questions(
    job_requirements: Dict[str, Any],
    company_info: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate fallback questions if all other generation methods fail."""
    logger.warning(f"Using fallback questions for {job_requirements.get('title', 'Unknown')} at {company_info.get('name', 'Unknown')}")
    
    try:
        # Initialize role question generator
        role_generator = RoleSpecificQuestionGenerator()
        
        # Map string values to enum values
        functional_area_map = {
            "sales": FunctionalArea.SALES,
            "engineering": FunctionalArea.ENGINEERING,
            "marketing": FunctionalArea.MARKETING,
            "product": FunctionalArea.PRODUCT,
            "finance": FunctionalArea.FINANCE,
            "operations": FunctionalArea.OPERATIONS
        }
        
        seniority_level_map = {
            "c_suite": SeniorityLevel.C_SUITE,
            "evp": SeniorityLevel.EVP,
            "svp": SeniorityLevel.SVP,
            "vp": SeniorityLevel.VP,
            "director": SeniorityLevel.DIRECTOR
        }
        
        # Get enum values
        functional_area = functional_area_map.get(
            job_requirements.get("functional_area", "").lower(),
            FunctionalArea.SALES
        )
        
        seniority_level = seniority_level_map.get(
            job_requirements.get("seniority_level", "").lower(),
            SeniorityLevel.VP
        )
        
        # Use role-specific templates as fallback
        templates = role_generator.get_role_specific_questions(
            functional_area,
            seniority_level,
            company_info.get("stage", "unknown")
        )
        
        logger.info(f"Found {len(templates)} role-specific templates")
        
        # Take first 4 questions
        fallback_questions = []
        for i, template in enumerate(templates[:4]):
            question_id = f"fallback_{i+1}"
            category = _categorize_question(template)
            
            fallback_questions.append({
                "question_id": question_id,
                "question": template,
                "category": category,
                "rationale": "Standard question for this role type"
            })
            logger.debug(f"Fallback question {i+1}: {template[:60]}...")
        
        logger.info(f"Created {len(fallback_questions)} fallback questions")
        
        return {
            "fallback_questions": fallback_questions,
            "total_templates": len(templates),
            "selected_count": len(fallback_questions)
        }
        
    except Exception as e:
        logger.error(f"Error generating fallback questions: {str(e)}", exc_info=True)
        return {
            "fallback_questions": [],
            "total_templates": 0,
            "selected_count": 0,
            "error": str(e)
        }


def _categorize_question(question_text: str) -> str:
    """Categorize a question based on its content (identical to service)."""
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


# List of all question generation tools
QUESTION_GENERATION_TOOLS = [
    generate_research_driven_questions,
    generate_role_specific_questions,
    generate_fallback_questions
]