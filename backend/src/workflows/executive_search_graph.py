"""Executive Search LangGraph workflow implementation."""

from typing import Dict, Any
from datetime import datetime
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession

from .state_schema import ExecutiveSearchState
from .nodes.base_node import BaseNode
from .nodes.extraction_node import create_requirements_extraction_node
from .nodes.research_node import create_company_research_node
from .nodes.question_generation_node import create_question_generation_node
from .nodes.answer_processing_node import create_answer_processing_node
from .nodes.completion_check_node import create_completion_check_node
from .nodes.question_presentation_node import create_question_presentation_node
from .nodes.summary_generation_node import create_summary_generation_node
from ..logger import logger


class ExecutiveSearchWorkflow:
    """Executive Search workflow using LangGraph."""
    
    def __init__(self, db_session: AsyncSession):
        """Initialize the workflow with database session."""
        self.db_session = db_session
        self.workflow = None
        self._build_workflow()
    
    def _build_workflow(self):
        """Build the LangGraph workflow."""
        workflow = StateGraph(ExecutiveSearchState)
        
        # Create nodes with database session
        extraction_node = create_requirements_extraction_node(self.db_session)
        research_node = create_company_research_node()
        question_generation_node = create_question_generation_node(self.db_session)
        answer_processing_node = create_answer_processing_node(self.db_session)
        completion_check_node = create_completion_check_node(self.db_session)
        question_presentation_node = create_question_presentation_node(self.db_session)
        summary_generation_node = create_summary_generation_node(self.db_session)
        
        # Add nodes for extraction workflow
        workflow.add_node("extract_requirements", extraction_node.execute)
        workflow.add_node("research_company", research_node.execute)
        workflow.add_node("generate_questions", question_generation_node.execute)
        workflow.add_node("skip_research", self._skip_research_node)
        
        # Add nodes for questioning workflow
        workflow.add_node("process_answer", answer_processing_node.execute)
        workflow.add_node("check_completion", completion_check_node.execute)
        workflow.add_node("present_next_question", question_presentation_node.execute)
        workflow.add_node("generate_summary", summary_generation_node.execute)
        
        # Add utility nodes
        workflow.add_node("end", self._end_node)
        
        # Define extraction + research + question generation workflow
        workflow.set_entry_point("extract_requirements")
        workflow.add_conditional_edges(
            "extract_requirements",
            self._route_after_extraction,
            {
                "research": "research_company",
                "skip_research": "skip_research",
                "error": "end"
            }
        )
        workflow.add_edge("research_company", "generate_questions")
        workflow.add_edge("skip_research", "generate_questions")
        workflow.add_edge("generate_questions", "present_next_question")
        
        # Define questioning phase workflow
        workflow.add_edge("process_answer", "check_completion")
        workflow.add_conditional_edges(
            "check_completion",
            self._route_after_completion_check,
            {
                "present_next_question": "present_next_question",
                "generate_summary": "generate_summary",
                "error": "end"
            }
        )
        workflow.add_edge("present_next_question", "end")
        workflow.add_edge("generate_summary", "end")
        workflow.add_edge("end", END)
        
        # Compile workflow
        self.workflow = workflow.compile()
    
    def _route_after_extraction(self, state: ExecutiveSearchState) -> str:
        """Route workflow after requirements extraction."""
        if state.get("error_message"):
            return "error"
        
        # Check if we have company info that warrants research
        company_info = state.get("company_info")
        if company_info and company_info.get("name") and company_info["name"] != "Unknown Company":
            logger.info(f"Company detected: {company_info['name']} - routing to research")
            return "research"
        else:
            logger.info("No company info or unknown company - skipping research")
            return "skip_research"
    
    def _route_after_completion_check(self, state: ExecutiveSearchState) -> str:
        """Route workflow after completion check."""
        if state.get("error_message"):
            return "error"
        
        next_action = state.get("next_action")
        if next_action == "present_next_question":
            logger.info("More questions available - presenting next question")
            return "present_next_question"
        elif next_action == "generate_summary":
            logger.info("All questions completed - generating summary")
            return "generate_summary"
        else:
            logger.warning(f"Unknown next action: {next_action}")
            return "error"
    
    async def _skip_research_node(self, state: ExecutiveSearchState) -> ExecutiveSearchState:
        """Skip research node when no company info is available."""
        logger.info("Skipping research - no company info available")
        return {
            **state,
            "node_history": state.get("node_history", []) + ["skip_research"],
            "updated_at": datetime.now(),
            "company_research": None,
            "research_insights": None,
            "next_action": "generate_questions"
        }
    
    async def _end_node(self, state: ExecutiveSearchState) -> ExecutiveSearchState:
        """End node that preserves final state."""
        updated_state = {
            **state,
            "node_history": state.get("node_history", []) + ["end"],
            "updated_at": datetime.now()
        }
        
        # Only set next_action to None if it's not already set to something meaningful
        if state.get("next_action") not in ["wait_for_answer", "generate_summary"]:
            updated_state["next_action"] = None
            
        return updated_state
    
    async def process_extraction(
        self, 
        conversation_id: str, 
        message: str, 
        feature_flags: Dict[str, bool]
    ) -> ExecutiveSearchState:
        """Process requirements extraction through the workflow."""
        
        # Create initial state for extraction
        initial_state = ExecutiveSearchState(
            conversation_id=conversation_id,
            phase="extraction",
            status="active",
            messages=[{"role": "user", "content": message}],
            current_message=message,
            job_requirements=None,
            company_info=None,
            company_research=None,
            research_insights=None,
            questions=[],
            current_question_index=0,
            question_responses=[],
            next_action="extract_requirements",
            error_message=None,
            retry_count=0,
            is_complete=None,
            response_content=None,
            next_question=None,
            summary=None,
            feature_flags=feature_flags,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            progress={"phase": "extraction", "step": "requirements_extraction"},
            workflow_version="2.0",
            node_history=[]
        )
        
        # Execute workflow (without checkpointing for Phase 1)
        result = await self.workflow.ainvoke(initial_state)
        
        return result
    
    async def process_answer(
        self,
        conversation_id: str,
        message: str,
        feature_flags: Dict[str, bool]
    ) -> ExecutiveSearchState:
        """Process user answer through the questioning workflow."""
        
        # Create initial state for answer processing
        initial_state = ExecutiveSearchState(
            conversation_id=conversation_id,
            phase="questioning",
            status="active",
            messages=[{"role": "user", "content": message}],
            current_message=message,
            job_requirements=None,  # Will be loaded from DB
            company_info=None,      # Will be loaded from DB
            company_research=None,
            research_insights=None,
            questions=[],
            current_question_index=0,
            question_responses=[],
            next_action="process_answer",
            error_message=None,
            retry_count=0,
            is_complete=None,
            response_content=None,
            next_question=None,
            summary=None,
            feature_flags=feature_flags,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            progress={"phase": "questioning", "step": "processing_answer"},
            workflow_version="2.0",
            node_history=[]
        )
        
        # Create a mini-workflow for answer processing
        answer_workflow = StateGraph(ExecutiveSearchState)
        
        # Get nodes
        answer_processing_node = create_answer_processing_node(self.db_session)
        completion_check_node = create_completion_check_node(self.db_session)
        question_presentation_node = create_question_presentation_node(self.db_session)
        summary_generation_node = create_summary_generation_node(self.db_session)
        
        # Add nodes
        answer_workflow.add_node("process_answer", answer_processing_node.execute)
        answer_workflow.add_node("check_completion", completion_check_node.execute)
        answer_workflow.add_node("present_next_question", question_presentation_node.execute)
        answer_workflow.add_node("generate_summary", summary_generation_node.execute)
        answer_workflow.add_node("end", self._end_node)
        
        # Define flow
        answer_workflow.set_entry_point("process_answer")
        answer_workflow.add_edge("process_answer", "check_completion")
        answer_workflow.add_conditional_edges(
            "check_completion",
            self._route_after_completion_check,
            {
                "present_next_question": "present_next_question",
                "generate_summary": "generate_summary",
                "error": "end"
            }
        )
        answer_workflow.add_edge("present_next_question", "end")
        answer_workflow.add_edge("generate_summary", "end")
        answer_workflow.add_edge("end", END)
        
        # Compile and execute
        compiled_workflow = answer_workflow.compile()
        result = await compiled_workflow.ainvoke(initial_state)
        
        return result


def create_executive_search_workflow(db_session: AsyncSession) -> ExecutiveSearchWorkflow:
    """Factory function to create executive search workflow."""
    return ExecutiveSearchWorkflow(db_session)