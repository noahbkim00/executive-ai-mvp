from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


class CompanyStage(str, Enum):
    """Company funding/growth stage"""
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C = "series_c"
    SERIES_D_PLUS = "series_d_plus"
    PRE_IPO = "pre_ipo"
    PUBLIC = "public"
    PRIVATE_EQUITY = "private_equity"
    BOOTSTRAPPED = "bootstrapped"
    UNKNOWN = "unknown"


class Industry(str, Enum):
    """Company industry categories"""
    FINTECH = "fintech"
    HEALTHTECH = "healthtech"
    EDTECH = "edtech"
    ENTERPRISE_SOFTWARE = "enterprise_software"
    CONSUMER_SOFTWARE = "consumer_software"
    ECOMMERCE = "ecommerce"
    BIOTECH = "biotech"
    HARDWARE = "hardware"
    MARKETPLACE = "marketplace"
    MEDIA = "media"
    AUTOMOTIVE = "automotive"
    REAL_ESTATE = "real_estate"
    ENERGY = "energy"
    MANUFACTURING = "manufacturing"
    CONSULTING = "consulting"
    OTHER = "other"


class BusinessModel(str, Enum):
    """Business model types"""
    B2B_SAAS = "b2b_saas"
    B2C_SAAS = "b2c_saas"
    MARKETPLACE = "marketplace"
    ECOMMERCE = "ecommerce"
    ENTERPRISE = "enterprise"
    CONSUMER = "consumer"
    FREEMIUM = "freemium"
    SUBSCRIPTION = "subscription"
    TRANSACTION = "transaction"
    ADVERTISING = "advertising"
    OTHER = "other"


class CompanyInfo(BaseModel):
    """Company information and context"""
    conversation_id: UUID
    
    # Basic company details
    name: str
    industry: Industry
    business_model: BusinessModel
    stage: CompanyStage
    
    # Company characteristics
    mission_vision: Optional[str] = None
    core_values: List[str] = Field(default_factory=list)
    company_culture: Optional[str] = None
    
    # Growth and performance context
    growth_stage_description: Optional[str] = None  # e.g., "scaling from $2M to $10M ARR"
    key_challenges: List[str] = Field(default_factory=list)
    recent_milestones: List[str] = Field(default_factory=list)
    
    # Work environment
    work_model: Optional[str] = None  # remote, hybrid, in-person
    headquarters_location: Optional[str] = None
    team_locations: List[str] = Field(default_factory=list)
    
    # Leadership context
    leadership_style: Optional[str] = None
    reporting_culture: Optional[str] = None  # e.g., "data-driven", "collaborative"
    
    # Additional context that affects hiring
    additional_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CompanyUpdate(BaseModel):
    """Update to company information"""
    conversation_id: UUID
    field_updates: Dict[str, Any]
    append_to_lists: Optional[Dict[str, List[str]]] = None


class CompanyContext(BaseModel):
    """Processed company context for question generation"""
    conversation_id: UUID
    name: str
    industry: Industry
    stage: CompanyStage
    business_model: BusinessModel
    
    # Key context for intelligent questioning
    growth_context: Optional[str] = None
    cultural_indicators: List[str] = Field(default_factory=list)
    leadership_context: Optional[str] = None
    unique_challenges: List[str] = Field(default_factory=list)
    
    # Flags for question generation
    needs_cultural_assessment: bool = True
    needs_growth_experience: bool = True
    needs_leadership_style: bool = True
    
    # Completeness
    context_completeness: float  # 0-1 scale
    missing_context_areas: List[str] = Field(default_factory=list)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))