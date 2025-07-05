"""Service for extracting and structuring job requirements from conversation."""

import re
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ..services.llm_factory import LLMFactory
from ..utils.error_handler import ErrorHandler
from ..exceptions.service_exceptions import RequirementsExtractionError

from ..models.job_requirements import (
    JobRequirements, SeniorityLevel, FunctionalArea, 
    ExperienceRequirement, CulturalRequirement, RequirementType
)
from ..models.company_info import CompanyInfo, Industry, BusinessModel, CompanyStage
from ..models.db_models import JobRequirementsDB, CompanyInfoDB
from ..logger import logger


class RequirementsExtractionService:
    """Service for extracting structured requirements from initial user input"""
    
    def __init__(self, db_session: AsyncSession, openai_api_key: str):
        self.db = db_session
        # Initialize LLM using factory for structured extraction
        self.llm = LLMFactory.create_extraction_llm()
        
        # Parser for structured output
        self.json_parser = JsonOutputParser()
        
        # Prompt for extracting job requirements
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
        
        # Prompt for company context extraction
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
    
    async def extract_initial_requirements(
        self, 
        conversation_id: uuid.UUID, 
        user_input: str
    ) -> tuple[Optional[JobRequirements], Optional[CompanyInfo]]:
        """Extract structured job and company requirements from initial user input"""
        
        try:
            # Extract job requirements using LLM
            job_chain = self.job_extraction_prompt | self.llm | self.json_parser
            extracted_data = await job_chain.ainvoke({"user_input": user_input})
            
            logger.info(f"Extracted data for conversation {conversation_id}: {extracted_data}")
            
            # Create JobRequirements object
            job_requirements = None
            if extracted_data.get("job_title"):
                job_requirements = JobRequirements(
                    conversation_id=conversation_id,
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
            
            # Create CompanyInfo object
            company_info = None
            if extracted_data.get("company_name"):
                company_info = CompanyInfo(
                    conversation_id=conversation_id,
                    name=extracted_data.get("company_name", "Unknown Company"),
                    industry=self._parse_industry(extracted_data.get("company_industry")),
                    business_model=self._parse_business_model(extracted_data.get("business_model")),
                    stage=self._parse_company_stage(extracted_data.get("company_stage")),
                    growth_stage_description=extracted_data.get("growth_context")
                )
                
                # Enhance with additional context
                if company_info.name != "Unknown Company":
                    await self._enhance_company_context(company_info, user_input)
                
                # Save to database
                await self._save_company_info(company_info)
            
            return job_requirements, company_info
            
        except Exception as e:
            logger.error(f"Error extracting requirements: {str(e)}", exc_info=True)
            # Return empty objects instead of None for better error handling
            return self._create_fallback_requirements(), self._create_fallback_company_info()
    
    def _create_fallback_requirements(self) -> JobRequirements:
        """Create fallback job requirements when extraction fails."""
        return JobRequirements(
            title="Unknown Position",
            seniority_level=SeniorityLevel.UNKNOWN,
            functional_area=FunctionalArea.UNKNOWN,
            key_requirements=[],
            nice_to_haves=[],
            deal_breakers=[]
        )
    
    def _create_fallback_company_info(self) -> CompanyInfo:
        """Create fallback company info when extraction fails."""
        return CompanyInfo(
            name="Unknown Company",
            industry="Unknown",
            stage="unknown",
            description="Unable to extract company information"
        )
    
    async def _enhance_company_context(self, company_info: CompanyInfo, user_context: str):
        """Enhance company information with additional context"""
        try:
            context_chain = self.company_extraction_prompt | self.llm | self.json_parser
            enhanced_data = await context_chain.ainvoke({
                "company_name": company_info.name,
                "industry": company_info.industry.value,
                "stage": company_info.stage.value,
                "business_model": company_info.business_model.value,
                "user_context": user_context
            })
            
            # Update company info with enhanced context
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
    
    def _parse_seniority_level(self, level_str: str) -> SeniorityLevel:
        """Parse seniority level from string"""
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
        """Parse functional area from string"""
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
        """Parse industry from string"""
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
        """Parse business model from string"""
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
        """Parse company stage from string"""
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
        """Save job requirements to database"""
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
        """Save company info to database"""
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
    
    async def get_job_requirements(self, conversation_id: uuid.UUID) -> Optional[JobRequirements]:
        """Get job requirements for a conversation"""
        stmt = select(JobRequirementsDB).where(JobRequirementsDB.conversation_id == conversation_id)
        result = await self.db.execute(stmt)
        db_job = result.scalar_one_or_none()
        
        if not db_job:
            return None
        
        return JobRequirements(
            conversation_id=db_job.conversation_id,
            title=db_job.title,
            seniority_level=SeniorityLevel(db_job.seniority_level),
            functional_area=FunctionalArea(db_job.functional_area),
            reporting_structure=db_job.reporting_structure,
            team_size=db_job.team_size,
            experience_requirements=[
                ExperienceRequirement(**req) for req in (db_job.experience_requirements or [])
            ],
            cultural_requirements=[
                CulturalRequirement(**req) for req in (db_job.cultural_requirements or [])
            ],
            key_metrics=db_job.key_metrics or [],
            deal_breakers=db_job.deal_breakers or [],
            additional_context=db_job.additional_context or {},
            created_at=db_job.created_at,
            updated_at=db_job.updated_at
        )
    
    async def get_company_info(self, conversation_id: uuid.UUID) -> Optional[CompanyInfo]:
        """Get company info for a conversation"""
        stmt = select(CompanyInfoDB).where(CompanyInfoDB.conversation_id == conversation_id)
        result = await self.db.execute(stmt)
        db_company = result.scalar_one_or_none()
        
        if not db_company:
            return None
        
        return CompanyInfo(
            conversation_id=db_company.conversation_id,
            name=db_company.name,
            industry=Industry(db_company.industry),
            business_model=BusinessModel(db_company.business_model),
            stage=CompanyStage(db_company.stage),
            mission_vision=db_company.mission_vision,
            core_values=db_company.core_values or [],
            company_culture=db_company.company_culture,
            growth_stage_description=db_company.growth_stage_description,
            key_challenges=db_company.key_challenges or [],
            recent_milestones=db_company.recent_milestones or [],
            work_model=db_company.work_model,
            headquarters_location=db_company.headquarters_location,
            team_locations=db_company.team_locations or [],
            leadership_style=db_company.leadership_style,
            reporting_culture=db_company.reporting_culture,
            additional_context=db_company.additional_context or {},
            created_at=db_company.created_at,
            updated_at=db_company.updated_at
        )