from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid

from ..models.conversation import ConversationRequest, ConversationResponse, ConversationSummary, ConversationPhase, ConversationStatus
from ..services.conversation_service import ConversationService
from ..services.requirements_extraction_service import RequirementsExtractionService
from ..services.question_generation_service import QuestionGenerationService
from ..database import get_db
from ..config import get_settings
from ..logger import logger
# LangGraph import - enabled for Phase 2 testing
from ..workflows.executive_search_graph import create_executive_search_workflow


router = APIRouter(prefix="/api/chat", tags=["chat"])




@router.post("/conversation", response_model=ConversationResponse)
async def send_conversation_message(
    request: ConversationRequest, 
    db: AsyncSession = Depends(get_db)
) -> ConversationResponse:
    """
    Send a message within a conversation context (new multi-phase flow)
    """
    try:
        logger.info(f"Received conversation request: {request.message[:50]}...")
        
        # Get settings
        settings = get_settings()
        if not settings.openai_api_key:
            raise HTTPException(
                status_code=500,
                detail="OpenAI API key not configured"
            )
        
        # Use LangGraph workflow for conversation processing
        logger.info("Using LangGraph workflow for conversation processing")
        return await _process_with_langgraph(request, db, settings)
        
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing conversation request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process your message. Please try again."
        )


@router.get("/conversation/{conversation_id}", response_model=ConversationSummary)
async def get_conversation_summary(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
) -> ConversationSummary:
    """
    Get summary of a conversation
    """
    try:
        conversation_uuid = uuid.UUID(conversation_id)
        conversation_service = ConversationService(db)
        
        conversation = await conversation_service.get_conversation(conversation_uuid)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Calculate duration if completed
        duration_minutes = None
        completed_at = None
        if conversation.phase == "completed" and "completed_at" in conversation.metadata:
            try:
                from datetime import datetime
                completed_at = datetime.fromisoformat(conversation.metadata["completed_at"])
                duration_minutes = (completed_at - conversation.created_at).total_seconds() / 60
            except:
                pass
        
        return ConversationSummary(
            conversation_id=conversation.conversation_id,
            phase=conversation.phase,
            status=conversation.status,
            total_messages=len(conversation.questions_responses) * 2,  # Questions + responses
            questions_asked=conversation.total_questions,
            questions_answered=conversation.current_question_index,
            duration_minutes=duration_minutes,
            created_at=conversation.created_at,
            completed_at=completed_at
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get conversation summary")


@router.get("/conversation/{conversation_id}/progress")
async def get_conversation_progress(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get current progress of a conversation
    """
    try:
        conversation_uuid = uuid.UUID(conversation_id)
        conversation_service = ConversationService(db)
        
        progress = await conversation_service.get_conversation_progress(conversation_uuid)
        if not progress:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return progress
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation progress: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get conversation progress")


# Helper functions for feature flag processing

async def _process_with_langgraph(
    request: ConversationRequest, 
    db: AsyncSession, 
    settings
) -> ConversationResponse:
    """Process conversation using LangGraph workflow."""
    try:
        logger.info("Processing with LangGraph workflow")
        
        # Initialize services for compatibility
        conversation_service = ConversationService(db)
        question_service = QuestionGenerationService(db, settings.openai_api_key)
        
        # Get or create conversation
        if request.conversation_id:
            conversation = await conversation_service.get_conversation(request.conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            # Create new conversation
            conversation = await conversation_service.create_conversation()
        
        # Process extraction with LangGraph only for initial phase
        if conversation.phase.value == "initial":
            logger.info(f"Processing initial message with LangGraph for conversation {conversation.conversation_id}")
            
            # Initialize LangGraph workflow
            workflow = create_executive_search_workflow(db)
            
            # Process extraction + research + question generation through workflow
            feature_flags = {"use_langgraph": True}
            result = await workflow.process_extraction(
                conversation_id=str(conversation.conversation_id),
                message=request.message,
                feature_flags=feature_flags
            )
            
            # Check if the full workflow was successful
            if result.get("job_requirements") and result.get("questions"):
                logger.info(f"LangGraph workflow successful for conversation {conversation.conversation_id}")
                
                # Get questions from the workflow result
                questions = result.get("questions", [])
                logger.info(f"LangGraph generated {len(questions)} questions for conversation {conversation.conversation_id}")
                
                # Get job requirements and company info for response
                from ..services.requirements_extraction_service import RequirementsExtractionService
                req_service = RequirementsExtractionService(db, settings.openai_api_key)
                job_requirements = await req_service.get_job_requirements(conversation.conversation_id)
                company_info = await req_service.get_company_info(conversation.conversation_id)
                
                if job_requirements and company_info and questions:
                    # Move to questioning phase
                    from ..models.conversation import ConversationPhase
                    await conversation_service.update_conversation_phase(
                        conversation.conversation_id, 
                        ConversationPhase.QUESTIONING,
                        {"initial_extraction_complete": True, "langgraph_used": True, "langgraph_questions_generated": True}
                    )
                    
                    # Prepare response with first question
                    response_content = f"Great! I understand you're looking for a {job_requirements.title} for {company_info.name}. To ensure we find the perfect candidate, I'd like to ask you {len(questions)} key questions about the role and your specific needs."
                    
                    first_question = questions[0] if questions else None
                    
                    return ConversationResponse(
                        conversation_id=conversation.conversation_id,
                        phase=ConversationPhase.QUESTIONING,
                        status=ConversationStatus.ACTIVE,
                        response_content=response_content,
                        progress={
                            "phase": "questioning",
                            "current_question": 1,
                            "total_questions": len(questions),
                            "progress_percentage": 0
                        },
                        next_question=f"Question 1 of {len(questions)}: {first_question.get('question', 'N/A')}" if first_question else None,
                        is_complete=False
                    )
            
            # Extraction failed - return error
            logger.warning(f"LangGraph extraction failed for conversation {conversation.conversation_id}")
            return ConversationResponse(
                conversation_id=conversation.conversation_id,
                phase=ConversationPhase.INITIAL,
                status=ConversationStatus.ACTIVE,
                response_content="I'm sorry, I couldn't understand your requirements. Could you please rephrase your request? For example: 'I'm looking for a VP of Engineering at Stripe'.",
                progress={"phase": "initial", "current_question": 0, "total_questions": 0, "progress_percentage": 0},
                is_complete=False
            )
        
        else:
            # Handle non-initial phases with LangGraph
            logger.info(f"Processing {conversation.phase.value} phase with LangGraph")
            return await _process_questioning_with_langgraph(request, db, settings, conversation)
        
    except Exception as e:
        logger.error(f"Error in LangGraph processing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"LangGraph processing failed: {str(e)}"
        )


async def _process_questioning_with_langgraph(
    request: ConversationRequest,
    db: AsyncSession,
    settings,
    conversation
) -> ConversationResponse:
    """Process questioning phase using LangGraph workflow."""
    try:
        logger.info(f"Processing questioning phase with LangGraph for conversation {conversation.conversation_id}")
        
        # Initialize LangGraph workflow
        workflow = create_executive_search_workflow(db)
        
        # Process the answer through LangGraph
        feature_flags = {"use_langgraph": True}
        result = await workflow.process_answer(
            conversation_id=str(conversation.conversation_id),
            message=request.message,
            feature_flags=feature_flags
        )
        
        logger.info(f"LangGraph answer processing completed for conversation {conversation.conversation_id}")
        
        # Check if conversation is complete
        if result.get("is_complete"):
            logger.info(f"Conversation {conversation.conversation_id} completed")
            return ConversationResponse(
                conversation_id=conversation.conversation_id,
                phase=ConversationPhase.COMPLETED,
                status=ConversationStatus.COMPLETED,
                response_content=result.get("response_content", "Thank you for providing all that information!"),
                progress=result.get("progress", {
                    "phase": "completed",
                    "current_question": conversation.total_questions,
                    "total_questions": conversation.total_questions,
                    "progress_percentage": 100.0
                }),
                is_complete=True
            )
        
        # Present next question
        next_question = result.get("next_question")
        if next_question:
            question_text = next_question.get("question", "")
            question_number = next_question.get("number", 1)
            total_questions = next_question.get("total", 1)
            
            return ConversationResponse(
                conversation_id=conversation.conversation_id,
                phase=ConversationPhase.QUESTIONING,
                status=ConversationStatus.ACTIVE,
                response_content=result.get("response_content", "Thank you for that information. Here's my next question:"),
                progress=result.get("progress", {
                    "phase": "questioning",
                    "current_question": question_number,
                    "total_questions": total_questions,
                    "progress_percentage": ((question_number - 1) / total_questions) * 100 if total_questions > 0 else 0
                }),
                next_question=f"Question {question_number} of {total_questions}: {question_text}",
                is_complete=False
            )
        
        # Error state - no next question but not complete
        logger.warning(f"No next question available but conversation not complete for {conversation.conversation_id}")
        return ConversationResponse(
            conversation_id=conversation.conversation_id,
            phase=conversation.phase,
            status=conversation.status,
            response_content="I encountered an issue processing your response. Please try again.",
            progress={"phase": "questioning", "current_question": 0, "total_questions": 0, "progress_percentage": 0},
            is_complete=False
        )
        
    except Exception as e:
        logger.error(f"Error in LangGraph questioning: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"LangGraph questioning failed: {str(e)}"
        )


