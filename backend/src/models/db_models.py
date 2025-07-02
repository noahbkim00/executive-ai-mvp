"""SQLAlchemy database models for conversation management."""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, Float, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from uuid import uuid4

from .base import Base


class ConversationDB(Base):
    """Database model for conversations"""
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    phase = Column(String(50), nullable=False, default="initial")
    status = Column(String(50), nullable=False, default="active")
    current_question_index = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    conversation_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    questions_responses = relationship("QuestionResponseDB", back_populates="conversation", cascade="all, delete-orphan")
    job_requirements = relationship("JobRequirementsDB", back_populates="conversation", uselist=False, cascade="all, delete-orphan")
    company_info = relationship("CompanyInfoDB", back_populates="conversation", uselist=False, cascade="all, delete-orphan")


class QuestionResponseDB(Base):
    """Database model for question-response pairs"""
    __tablename__ = "question_responses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    question_id = Column(String(100), nullable=False)
    question_text = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    conversation = relationship("ConversationDB", back_populates="questions_responses")


class JobRequirementsDB(Base):
    """Database model for job requirements"""
    __tablename__ = "job_requirements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    
    # Basic role information
    title = Column(String(255), nullable=False)
    seniority_level = Column(String(50), nullable=False)
    functional_area = Column(String(50), nullable=False)
    reporting_structure = Column(String(255))
    team_size = Column(Integer)
    
    # Structured requirements (stored as JSON)
    experience_requirements = Column(JSON, default=list)
    cultural_requirements = Column(JSON, default=list)
    compensation = Column(JSON)
    key_metrics = Column(JSON, default=list)
    deal_breakers = Column(JSON, default=list)
    additional_context = Column(JSON, default=dict)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    conversation = relationship("ConversationDB", back_populates="job_requirements")


class CompanyInfoDB(Base):
    """Database model for company information"""
    __tablename__ = "company_info"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    
    # Basic company details
    name = Column(String(255), nullable=False)
    industry = Column(String(50), nullable=False)
    business_model = Column(String(50), nullable=False)
    stage = Column(String(50), nullable=False)
    
    # Company characteristics (stored as JSON for flexibility)
    mission_vision = Column(Text)
    core_values = Column(JSON, default=list)
    company_culture = Column(Text)
    growth_stage_description = Column(Text)
    key_challenges = Column(JSON, default=list)
    recent_milestones = Column(JSON, default=list)
    
    # Work environment
    work_model = Column(String(50))
    headquarters_location = Column(String(255))
    team_locations = Column(JSON, default=list)
    
    # Leadership context
    leadership_style = Column(Text)
    reporting_culture = Column(Text)
    additional_context = Column(JSON, default=dict)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    conversation = relationship("ConversationDB", back_populates="company_info")