from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


class SeniorityLevel(str, Enum):
    """Seniority levels for executive positions"""
    VP = "vp"                    # Vice President
    SVP = "svp"                  # Senior Vice President
    EVP = "evp"                  # Executive Vice President
    C_SUITE = "c_suite"          # CEO, CTO, CFO, etc.
    DIRECTOR = "director"        # Director level
    SENIOR_DIRECTOR = "senior_director"


class FunctionalArea(str, Enum):
    """Functional areas for executive roles"""
    SALES = "sales"
    MARKETING = "marketing"
    ENGINEERING = "engineering"
    PRODUCT = "product"
    FINANCE = "finance"
    OPERATIONS = "operations"
    HR = "hr"
    LEGAL = "legal"
    STRATEGY = "strategy"
    GENERAL_MANAGEMENT = "general_management"
    OTHER = "other"


class RequirementType(str, Enum):
    """Types of requirements"""
    MUST_HAVE = "must_have"
    NICE_TO_HAVE = "nice_to_have"
    DEAL_BREAKER = "deal_breaker"


class ExperienceRequirement(BaseModel):
    """Specific experience requirement"""
    area: str                    # e.g., "SaaS scaling", "IPO experience"
    years_required: Optional[int] = None
    requirement_type: RequirementType
    description: str


class CulturalRequirement(BaseModel):
    """Cultural fit and soft skill requirements"""
    trait: str                   # e.g., "collaborative leadership", "data-driven"
    importance: RequirementType
    description: str


class CompensationRange(BaseModel):
    """Compensation expectations"""
    base_salary_min: Optional[int] = None
    base_salary_max: Optional[int] = None
    total_comp_min: Optional[int] = None
    total_comp_max: Optional[int] = None
    equity_percentage: Optional[float] = None
    currency: str = "USD"


class JobRequirements(BaseModel):
    """Complete job requirements structure"""
    conversation_id: UUID
    
    # Basic role information
    title: str
    seniority_level: SeniorityLevel
    functional_area: FunctionalArea
    reporting_structure: Optional[str] = None  # e.g., "Reports to CEO"
    team_size: Optional[int] = None
    
    # Experience requirements
    experience_requirements: List[ExperienceRequirement] = Field(default_factory=list)
    
    # Cultural and soft requirements
    cultural_requirements: List[CulturalRequirement] = Field(default_factory=list)
    
    # Compensation
    compensation: Optional[CompensationRange] = None
    
    # Key success metrics
    key_metrics: List[str] = Field(default_factory=list)  # First year goals
    
    # Deal breakers
    deal_breakers: List[str] = Field(default_factory=list)
    
    # Additional context
    additional_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RequirementsUpdate(BaseModel):
    """Update to job requirements"""
    conversation_id: UUID
    field_updates: Dict[str, Any]  # Flexible updates to any field
    append_to_lists: Optional[Dict[str, List[Any]]] = None  # For adding to list fields


class RequirementsSummary(BaseModel):
    """Summary of collected requirements"""
    conversation_id: UUID
    title: str
    seniority_level: SeniorityLevel
    functional_area: FunctionalArea
    
    # Counts
    total_experience_requirements: int
    total_cultural_requirements: int
    total_deal_breakers: int
    
    # Completeness indicators
    has_compensation_info: bool
    has_key_metrics: bool
    completeness_score: float  # 0-1 scale
    
    # For export to future agents
    structured_data: Dict[str, Any]
    
    created_at: datetime
    last_updated: datetime