"""State schema for ExecutiveSearch LangGraph workflow."""

from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime


class ExecutiveSearchState(TypedDict):
    """State schema for the Executive Search workflow."""
    
    # Conversation metadata
    conversation_id: str
    phase: str
    status: str
    
    # User input
    messages: List[Dict[str, Any]]
    current_message: str
    
    # Extracted data
    job_requirements: Optional[Dict[str, Any]]
    company_info: Optional[Dict[str, Any]]
    
    # Research data
    company_research: Optional[Dict[str, Any]]
    research_insights: Optional[Dict[str, Any]]
    
    # Generated questions
    questions: List[Dict[str, Any]]
    current_question_index: int
    question_responses: List[Dict[str, Any]]
    
    # Control flow
    next_action: Optional[str]
    error_message: Optional[str]
    retry_count: int
    
    # Conversation flow
    is_complete: Optional[bool]
    response_content: Optional[str]
    next_question: Optional[Dict[str, Any]]
    summary: Optional[Dict[str, Any]]
    
    # Feature flags
    feature_flags: Dict[str, bool]
    
    # Timestamps
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    # Progress tracking
    progress: Dict[str, Any]
    
    # Workflow metadata
    workflow_version: str
    node_history: List[str]