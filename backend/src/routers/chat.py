from fastapi import APIRouter, HTTPException

from ..models.chat import ChatRequest, ChatResponse
from ..services.chat import ChatService
from ..logger import logger


router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def send_message(request: ChatRequest) -> ChatResponse:
    """
    Send a message to the AI assistant and get a response
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