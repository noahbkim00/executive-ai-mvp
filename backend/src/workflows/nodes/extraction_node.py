"""Requirements extraction node for LangGraph workflow."""

import uuid
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from sqlalchemy.ext.asyncio import AsyncSession

from ..state_schema import ExecutiveSearchState
from .base_node import BaseNode
from ...services.llm_factory import LLMFactory
from ...models.job_requirements import (
    JobRequirements, SeniorityLevel, FunctionalArea, 
    ExperienceRequirement, CulturalRequirement
)
from ...models.company_info import CompanyInfo, Industry, BusinessModel, CompanyStage
from ...models.db_models import JobRequirementsDB, CompanyInfoDB
from ...logger import logger


class RequirementsExtractionNode(BaseNode):
    """LangGraph node for requirements extraction."""
    
    def __init__(self, db_session: AsyncSession):
        """Initialize the extraction node."""
        super().__init__("requirements_extraction")
        self.db = db_session
        
        # Initialize LLM using same factory as legacy
        self.llm = LLMFactory.create_extraction_llm()
        self.json_parser = JsonOutputParser()
        
        # Use identical prompts from legacy service
        self.job_extraction_prompt = ChatPromptTemplate.from_template("""
        You are an expert executive search consultant. Extract structured job requirements from the user's initial request.
        
        User Request: {user_input}
        
        Extract the following information and return it as JSON:
        
        {{
            "job_title": "exact title mentioned",
            "seniority_level": "one of: vp, svp, evp, c_suite, director, senior_director",
            "functional_area": "one of: sales, marketing, engineering, product, finance, operations, hr, legal, strategy, general_management, other",
            "company_name": "company name if mentioned",
            "company_industry": "one of: fintech, healthtech, edtech, enterprise_software, consumer_software, ecommerce, biotech, hardware, marketplace, media, automotive, real_estate, energy, manufacturing, consulting, other",
            "company_stage": "one of: seed, series_a, series_b, series_c, series_d_plus, pre_ipo, public, private_equity, bootstrapped, unknown",
            "business_model": "one of: b2b_saas, b2c_saas, marketplace, ecommerce, enterprise, consumer, freemium, subscription, transaction, advertising, other",
            "initial_requirements": [
                "list of any specific requirements mentioned"
            ],
            "growth_context": "any growth stage or scaling context mentioned",
            "key_metrics": [
                "any specific metrics or goals mentioned (e.g., revenue targets)"
            ]
        }}
        
        If information is not clearly stated, use "unknown" or leave arrays empty.
        Focus only on what is explicitly mentioned in the user's request.
        """)
        
        self.company_extraction_prompt = ChatPromptTemplate.from_template("""
        Based on the following information about a company, extract additional context that would be relevant for executive search:
        
        Company: {company_name}
        Industry: {industry}
        Stage: {stage}
        Business Model: {business_model}
        User Context: {user_context}
        
        Extract and return as JSON:
        {{
            "mission_vision": "company mission/vision if inferable from context",
            "growth_stage_description": "detailed description of current growth stage and challenges",
            "key_challenges": [
                "likely challenges based on stage and industry"
            ],
            "leadership_style_indicators": "likely leadership style needs based on stage",
            "cultural_context": "company culture indicators from the context"
        }}
        
        Focus on insights that would help generate better follow-up questions for executive search.
        """)
    
    async def execute(self, state: ExecutiveSearchState) -> ExecutiveSearchState:
        """Execute requirements extraction logic."""
        try:
            logger.info(f"Starting requirements extraction for conversation {state['conversation_id']}")
            
            # Extract requirements using identical logic
            job_requirements, company_info = await self._extract_requirements(
                state["conversation_id"], 
                state["current_message"]
            )
            
            # Update state with extracted data
            updated_state = self._update_state_metadata(state)
            updated_state.update({
                "job_requirements": job_requirements.dict() if job_requirements else None,
                "company_info": company_info.dict() if company_info else None,
                "next_action": "research" if (job_requirements and company_info and company_info.name != "Unknown Company") else "generate_questions",
                "error_message": None
            })
            
            logger.info(f"Requirements extraction completed for conversation {state['conversation_id']}")
            return updated_state
            
        except Exception as e:
            logger.error(f"Error in requirements extraction: {str(e)}", exc_info=True)
            return self._handle_error(state, e)
    
    async def _extract_requirements(
        self, 
        conversation_id: str, 
        user_input: str
    ) -> Tuple[Optional[JobRequirements], Optional[CompanyInfo]]:
        """Extract requirements using identical logic to legacy service."""
        
        try:
            # Extract job requirements using LLM (identical to legacy)
            job_chain = self.job_extraction_prompt | self.llm | self.json_parser
            extracted_data = await job_chain.ainvoke({"user_input": user_input})
            
            logger.info(f"Extracted data for conversation {conversation_id}: {extracted_data}")
            
            # Create JobRequirements object (identical logic)
            job_requirements = None
            if extracted_data.get("job_title"):
                job_requirements = JobRequirements(
                    conversation_id=uuid.UUID(conversation_id),
                    title=extracted_data.get("job_title", "Unknown Position"),
                    seniority_level=self._parse_seniority_level(extracted_data.get("seniority_level")),
                    functional_area=self._parse_functional_area(extracted_data.get("functional_area")),
                    key_metrics=extracted_data.get("key_metrics", []),
                    additional_context={
                        "initial_requirements": extracted_data.get("initial_requirements", []),
                        "growth_context": extracted_data.get("growth_context"),
                        "raw_user_input": user_input
                    }
                )
                
                # Save to database
                await self._save_job_requirements(job_requirements)
            
            # Create CompanyInfo object (identical logic)
            company_info = None
            if extracted_data.get("company_name"):
                company_info = CompanyInfo(
                    conversation_id=uuid.UUID(conversation_id),
                    name=extracted_data.get("company_name", "Unknown Company"),
                    industry=self._parse_industry(extracted_data.get("company_industry")),
                    business_model=self._parse_business_model(extracted_data.get("business_model")),
                    stage=self._parse_company_stage(extracted_data.get("company_stage")),
                    growth_stage_description=extracted_data.get("growth_context")
                )
                
                # Enhance with additional context (identical logic)
                if company_info.name != "Unknown Company":
                    await self._enhance_company_context(company_info, user_input)
                
                # Save to database
                await self._save_company_info(company_info)
            
            return job_requirements, company_info
            
        except Exception as e:
            logger.error(f"Error extracting requirements: {str(e)}", exc_info=True)
            # Return fallback objects (identical to legacy)
            return self._create_fallback_requirements(), self._create_fallback_company_info()
    
    def _create_fallback_requirements(self) -> JobRequirements:
        """Create fallback job requirements (identical to legacy)."""
        return JobRequirements(
            title="Unknown Position",
            seniority_level=SeniorityLevel.UNKNOWN,
            functional_area=FunctionalArea.UNKNOWN,
            key_requirements=[],
            nice_to_haves=[],
            deal_breakers=[]
        )
    
    def _create_fallback_company_info(self) -> CompanyInfo:
        """Create fallback company info (identical to legacy)."""
        return CompanyInfo(
            name="Unknown Company",
            industry="Unknown",
            stage="unknown",
            description="Unable to extract company information"
        )
    
    async def _enhance_company_context(self, company_info: CompanyInfo, user_context: str):
        """Enhance company information (identical to legacy)."""
        try:
            context_chain = self.company_extraction_prompt | self.llm | self.json_parser
            enhanced_data = await context_chain.ainvoke({
                "company_name": company_info.name,
                "industry": company_info.industry.value,
                "stage": company_info.stage.value,
                "business_model": company_info.business_model.value,
                "user_context": user_context
            })
            
            # Update company info with enhanced context (identical logic)
            if enhanced_data.get("mission_vision"):
                company_info.mission_vision = enhanced_data["mission_vision"]
            
            if enhanced_data.get("growth_stage_description"):
                if not company_info.growth_stage_description:
                    company_info.growth_stage_description = enhanced_data["growth_stage_description"]
            
            if enhanced_data.get("key_challenges"):
                company_info.key_challenges = enhanced_data["key_challenges"]
            
            if enhanced_data.get("leadership_style_indicators"):
                company_info.leadership_style = enhanced_data["leadership_style_indicators"]
            
            if enhanced_data.get("cultural_context"):
                company_info.company_culture = enhanced_data["cultural_context"]
                
        except Exception as e:
            logger.warning(f"Could not enhance company context: {str(e)}")
    
    # All parsing methods identical to legacy service
    def _parse_seniority_level(self, level_str: str) -> SeniorityLevel:
        """Parse seniority level from string (identical to legacy)."""
        if not level_str:
            return SeniorityLevel.VP
        
        level_map = {
            "vp": SeniorityLevel.VP,
            "svp": SeniorityLevel.SVP,
            "evp": SeniorityLevel.EVP,
            "c_suite": SeniorityLevel.C_SUITE,
            "director": SeniorityLevel.DIRECTOR,
            "senior_director": SeniorityLevel.SENIOR_DIRECTOR
        }
        
        return level_map.get(level_str.lower(), SeniorityLevel.VP)
    
    def _parse_functional_area(self, area_str: str) -> FunctionalArea:
        """Parse functional area from string (identical to legacy)."""
        if not area_str:
            return FunctionalArea.OTHER
        
        area_map = {
            "sales": FunctionalArea.SALES,
            "marketing": FunctionalArea.MARKETING,
            "engineering": FunctionalArea.ENGINEERING,
            "product": FunctionalArea.PRODUCT,
            "finance": FunctionalArea.FINANCE,
            "operations": FunctionalArea.OPERATIONS,
            "hr": FunctionalArea.HR,
            "legal": FunctionalArea.LEGAL,
            "strategy": FunctionalArea.STRATEGY,
            "general_management": FunctionalArea.GENERAL_MANAGEMENT
        }
        
        return area_map.get(area_str.lower(), FunctionalArea.OTHER)
    
    def _parse_industry(self, industry_str: str) -> Industry:
        """Parse industry from string (identical to legacy)."""
        if not industry_str:
            return Industry.OTHER
        
        industry_map = {
            "fintech": Industry.FINTECH,
            "healthtech": Industry.HEALTHTECH,
            "edtech": Industry.EDTECH,
            "enterprise_software": Industry.ENTERPRISE_SOFTWARE,
            "consumer_software": Industry.CONSUMER_SOFTWARE,
            "ecommerce": Industry.ECOMMERCE,
            "biotech": Industry.BIOTECH,
            "hardware": Industry.HARDWARE,
            "marketplace": Industry.MARKETPLACE,
            "media": Industry.MEDIA,
            "automotive": Industry.AUTOMOTIVE,
            "real_estate": Industry.REAL_ESTATE,
            "energy": Industry.ENERGY,
            "manufacturing": Industry.MANUFACTURING,
            "consulting": Industry.CONSULTING
        }
        
        return industry_map.get(industry_str.lower(), Industry.OTHER)
    
    def _parse_business_model(self, model_str: str) -> BusinessModel:
        """Parse business model from string (identical to legacy)."""
        if not model_str:
            return BusinessModel.OTHER
        
        model_map = {
            "b2b_saas": BusinessModel.B2B_SAAS,
            "b2c_saas": BusinessModel.B2C_SAAS,
            "marketplace": BusinessModel.MARKETPLACE,
            "ecommerce": BusinessModel.ECOMMERCE,
            "enterprise": BusinessModel.ENTERPRISE,
            "consumer": BusinessModel.CONSUMER,
            "freemium": BusinessModel.FREEMIUM,
            "subscription": BusinessModel.SUBSCRIPTION,
            "transaction": BusinessModel.TRANSACTION,
            "advertising": BusinessModel.ADVERTISING
        }
        
        return model_map.get(model_str.lower(), BusinessModel.OTHER)
    
    def _parse_company_stage(self, stage_str: str) -> CompanyStage:
        """Parse company stage from string (identical to legacy)."""
        if not stage_str:
            return CompanyStage.UNKNOWN
        
        stage_map = {
            "seed": CompanyStage.SEED,
            "series_a": CompanyStage.SERIES_A,
            "series_b": CompanyStage.SERIES_B,
            "series_c": CompanyStage.SERIES_C,
            "series_d_plus": CompanyStage.SERIES_D_PLUS,
            "pre_ipo": CompanyStage.PRE_IPO,
            "public": CompanyStage.PUBLIC,
            "private_equity": CompanyStage.PRIVATE_EQUITY,
            "bootstrapped": CompanyStage.BOOTSTRAPPED
        }
        
        return stage_map.get(stage_str.lower(), CompanyStage.UNKNOWN)
    
    async def _save_job_requirements(self, job_requirements: JobRequirements):
        """Save job requirements to database (identical to legacy)."""
        db_job = JobRequirementsDB(
            id=uuid.uuid4(),
            conversation_id=job_requirements.conversation_id,
            title=job_requirements.title,
            seniority_level=job_requirements.seniority_level.value,
            functional_area=job_requirements.functional_area.value,
            reporting_structure=job_requirements.reporting_structure,
            team_size=job_requirements.team_size,
            experience_requirements=[req.dict() for req in job_requirements.experience_requirements],
            cultural_requirements=[req.dict() for req in job_requirements.cultural_requirements],
            compensation=job_requirements.compensation.dict() if job_requirements.compensation else None,
            key_metrics=job_requirements.key_metrics,
            deal_breakers=job_requirements.deal_breakers,
            additional_context=job_requirements.additional_context
        )
        
        self.db.add(db_job)
        await self.db.commit()
        logger.info(f"Saved job requirements for conversation {job_requirements.conversation_id}")
    
    async def _save_company_info(self, company_info: CompanyInfo):
        """Save company info to database (identical to legacy)."""
        db_company = CompanyInfoDB(
            id=uuid.uuid4(),
            conversation_id=company_info.conversation_id,
            name=company_info.name,
            industry=company_info.industry.value,
            business_model=company_info.business_model.value,
            stage=company_info.stage.value,
            mission_vision=company_info.mission_vision,
            core_values=company_info.core_values,
            company_culture=company_info.company_culture,
            growth_stage_description=company_info.growth_stage_description,
            key_challenges=company_info.key_challenges,
            recent_milestones=company_info.recent_milestones,
            work_model=company_info.work_model,
            headquarters_location=company_info.headquarters_location,
            team_locations=company_info.team_locations,
            leadership_style=company_info.leadership_style,
            reporting_culture=company_info.reporting_culture,
            additional_context=company_info.additional_context
        )
        
        self.db.add(db_company)
        await self.db.commit()
        logger.info(f"Saved company info for conversation {company_info.conversation_id}")


# Factory function for node creation
def create_requirements_extraction_node(db_session: AsyncSession) -> RequirementsExtractionNode:
    """Factory function to create requirements extraction node."""
    return RequirementsExtractionNode(db_session)