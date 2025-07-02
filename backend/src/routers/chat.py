from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid
import os

from ..models.chat import ChatRequest, ChatResponse
from ..models.conversation import ConversationRequest, ConversationResponse, ConversationSummary, ConversationPhase, ConversationStatus
from ..services.chat import ChatService
from ..services.conversation_service import ConversationService
from ..services.requirements_extraction_service import RequirementsExtractionService
from ..services.question_generation_service import QuestionGenerationService
from ..database import get_db
from ..logger import logger


router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def send_message(request: ChatRequest) -> ChatResponse:
    """
    Send a message to the AI assistant and get a response (legacy endpoint)
    """
    try:
        logger.info(f"Received chat request: {request.message[:50]}...")
        
        # Initialize chat service after request validation
        try:
            chat_service = ChatService()
        except ValueError as e:
            logger.error(f"Failed to initialize chat service: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Chat service unavailable. Please check your API key configuration."
            )
        
        # Get response from chat service
        response = await chat_service.get_response(request.message)
        
        logger.info(f"Generated response: {response.content[:50]}...")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process your message. Please try again."
        )


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
        
        # Get OpenAI API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(
                status_code=500,
                detail="OpenAI API key not configured"
            )
        
        # Initialize services
        conversation_service = ConversationService(db)
        requirements_service = RequirementsExtractionService(db, openai_api_key)
        question_service = QuestionGenerationService(db, openai_api_key)
        
        # Get or create conversation
        if request.conversation_id:
            conversation = await conversation_service.get_conversation(request.conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            # Create new conversation
            conversation = await conversation_service.create_conversation()
        
        # Extract requirements if this is the initial message  
        if conversation.phase.value == "initial":
            job_requirements, company_info = await requirements_service.extract_initial_requirements(
                conversation.conversation_id, request.message
            )
            
            if job_requirements and company_info:
                # Generate follow-up questions
                questions = await question_service.generate_questions(
                    conversation.conversation_id, job_requirements, company_info
                )
                
                # Store questions in conversation
                await question_service.store_questions_in_conversation(
                    conversation.conversation_id, questions
                )
                
                # Move to questioning phase
                await conversation_service.update_conversation_phase(
                    conversation.conversation_id, 
                    ConversationPhase.QUESTIONING,
                    {"initial_extraction_complete": True}
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
                    next_question=f"Question 1 of {len(questions)}: {first_question.question}" if first_question else None,
                    is_complete=False
                )
        
        # Handle questioning phase
        elif conversation.phase.value == "questioning":
            # Store the answer to the current question
            current_question_index = conversation.current_question_index
            stored_questions = conversation.metadata.get("questions", [])
            
            if current_question_index < len(stored_questions):
                current_question = stored_questions[current_question_index]
                await conversation_service.add_question_response(
                    conversation.conversation_id,
                    current_question["question_id"],
                    current_question["question"],
                    request.message
                )
            
            # Get next question
            next_question_data = await question_service.get_next_question(conversation.conversation_id)
            
            if next_question_data:
                next_question, current_num, total_questions = next_question_data
                progress_percentage = ((current_num - 1) / total_questions) * 100
                
                return ConversationResponse(
                    conversation_id=conversation.conversation_id,
                    phase=ConversationPhase.QUESTIONING,
                    status=ConversationStatus.ACTIVE,
                    response_content="Thank you for that information. Here's my next question:",
                    progress={
                        "phase": "questioning",
                        "current_question": current_num,
                        "total_questions": total_questions,
                        "progress_percentage": progress_percentage
                    },
                    next_question=f"Question {current_num} of {total_questions}: {next_question.question}",
                    is_complete=False
                )
            else:
                # All questions answered - move to completed phase
                await conversation_service.complete_conversation(conversation.conversation_id)
                
                return ConversationResponse(
                    conversation_id=conversation.conversation_id,
                    phase=ConversationPhase.COMPLETED,
                    status=ConversationStatus.COMPLETED,
                    response_content="Thank you for providing all that valuable information! I now have a comprehensive understanding of your requirements. Your background search has begun, and we will notify you when we have identified potential candidates that match your specific needs.",
                    progress={
                        "phase": "completed",
                        "current_question": total_questions if 'total_questions' in locals() else conversation.total_questions,
                        "total_questions": total_questions if 'total_questions' in locals() else conversation.total_questions,
                        "progress_percentage": 100.0
                    },
                    is_complete=True
                )
        
        # For other phases, return a basic response
        else:
            chat_service = ChatService()
            basic_response = await chat_service.get_response(request.message)
            
            return ConversationResponse(
                conversation_id=conversation.conversation_id,
                phase=conversation.phase,
                status=conversation.status,
                response_content=basic_response.content,
                progress=await conversation_service.get_conversation_progress(conversation.conversation_id),
                is_complete=conversation.phase.value == "completed"
            )
        
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