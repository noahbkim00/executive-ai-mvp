"""Tests for conversation endpoint and service."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from uuid import uuid4

from src.main import app
from src.services.chat import ChatService
from src.models.chat import ChatMessage, ChatResponse
from src.models.conversation import ConversationRequest, ConversationResponse, ConversationPhase, ConversationStatus


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


class TestConversationAPI:
    """Test cases for conversation API endpoints."""

    def test_conversation_endpoint_success(self, client):
        """Test successful conversation endpoint call."""
        # Mock the LangGraph workflow and database dependencies
        mock_conversation_id = uuid4()
        
        with patch('src.routers.chat.get_settings') as mock_settings:
            mock_settings.return_value.openai_api_key = "test-key"
            
            with patch('src.routers.chat._process_with_langgraph') as mock_process:
                mock_process.return_value = ConversationResponse(
                    conversation_id=mock_conversation_id,
                    phase=ConversationPhase.QUESTIONING,
                    status=ConversationStatus.ACTIVE,
                    response_content="Great! I understand you're looking for a Head of Sales. To ensure we find the perfect candidate, I'd like to ask you 5 key questions about the role and your specific needs.",
                    progress={
                        "phase": "questioning",
                        "current_question": 1,
                        "total_questions": 5,
                        "progress_percentage": 0
                    },
                    next_question="Question 1 of 5: What specific experience requirements do you have?",
                    is_complete=False
                )
                
                response = client.post(
                    "/api/chat/conversation",
                    json={"message": "I'm looking for a Head of Sales"}
                )
        
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert data["phase"] == "questioning"
        assert data["status"] == "active"
        assert "response_content" in data
        assert "progress" in data
        assert data["is_complete"] is False

    def test_conversation_endpoint_empty_message(self, client):
        """Test conversation endpoint with empty message."""
        response = client.post(
            "/api/chat/conversation",
            json={"message": ""}
        )
        
        assert response.status_code == 422  # Validation error

    def test_conversation_endpoint_missing_message(self, client):
        """Test conversation endpoint with missing message field."""
        response = client.post(
            "/api/chat/conversation",
            json={}
        )
        
        assert response.status_code == 422  # Validation error

    def test_conversation_endpoint_invalid_json(self, client):
        """Test conversation endpoint with invalid JSON."""
        response = client.post(
            "/api/chat/conversation",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422

    def test_conversation_endpoint_service_error(self, client):
        """Test conversation endpoint when service raises an error."""
        with patch('src.routers.chat.get_settings') as mock_settings:
            mock_settings.return_value.openai_api_key = "test-key"
            
            with patch('src.routers.chat._process_with_langgraph') as mock_process:
                mock_process.side_effect = Exception("Service error")
                
                response = client.post(
                    "/api/chat/conversation",
                    json={"message": "Test message"}
                )
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to process your message" in data["detail"]

    def test_conversation_endpoint_missing_api_key(self, client):
        """Test conversation endpoint when OpenAI API key is missing."""
        with patch('src.routers.chat.get_settings') as mock_settings:
            mock_settings.return_value.openai_api_key = None
            
            response = client.post(
                "/api/chat/conversation",
                json={"message": "Test message"}
            )
        
        assert response.status_code == 500
        data = response.json()
        assert "OpenAI API key not configured" in data["detail"]

    def test_conversation_summary_endpoint(self, client):
        """Test conversation summary endpoint."""
        mock_conversation_id = uuid4()
        
        with patch('src.routers.chat.ConversationService') as mock_conv_service_class:
            mock_conv_service = Mock()
            mock_conversation = Mock(
                conversation_id=mock_conversation_id,
                phase="completed",
                status="completed",
                questions_responses=[],
                total_questions=5,
                current_question_index=5,
                metadata={},
                created_at=datetime.now(timezone.utc)
            )
            mock_conv_service.get_conversation = AsyncMock(return_value=mock_conversation)
            mock_conv_service_class.return_value = mock_conv_service
            
            response = client.get(f"/api/chat/conversation/{mock_conversation_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == str(mock_conversation_id)
        assert data["phase"] == "completed"
        assert data["status"] == "completed"
        assert "total_messages" in data
        assert "questions_asked" in data
        assert "questions_answered" in data

    def test_conversation_progress_endpoint(self, client):
        """Test conversation progress endpoint."""
        mock_conversation_id = uuid4()
        mock_progress = {
            "phase": "questioning",
            "current_question": 3,
            "total_questions": 5,
            "progress_percentage": 60.0
        }
        
        with patch('src.routers.chat.ConversationService') as mock_conv_service_class:
            mock_conv_service = Mock()
            mock_conv_service.get_conversation_progress = AsyncMock(return_value=mock_progress)
            mock_conv_service_class.return_value = mock_conv_service
            
            response = client.get(f"/api/chat/conversation/{mock_conversation_id}/progress")
        
        assert response.status_code == 200
        data = response.json()
        assert data["phase"] == "questioning"
        assert data["current_question"] == 3
        assert data["total_questions"] == 5
        assert data["progress_percentage"] == 60.0


class TestChatService:
    """Test cases for chat service."""

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_chat_service_initialization(self):
        """Test chat service initializes with API key."""
        with patch('src.services.llm_factory.LLMFactory.create_generation_llm'):
            with patch('src.services.chat.get_settings') as mock_settings:
                mock_settings.return_value.openai_api_key = 'test-key'
                service = ChatService()
                assert service is not None

    def test_chat_service_missing_api_key(self):
        """Test chat service raises error without API key."""
        with patch('src.services.chat.get_settings') as mock_settings:
            mock_settings.return_value.openai_api_key = None
            with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is not set"):
                ChatService()

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @pytest.mark.asyncio
    async def test_get_response_success(self):
        """Test successful response generation."""
        mock_response = Mock()
        mock_response.content = "This is a test response about software engineers."
        
        with patch('src.services.llm_factory.LLMFactory.create_generation_llm') as mock_llm_factory:
            with patch('src.services.chat.ChatPromptTemplate') as mock_prompt:
                with patch('src.services.chat.get_settings') as mock_settings:
                    mock_settings.return_value.openai_api_key = 'test-key'
                    
                    # Mock the chain
                    mock_chain = AsyncMock()
                    mock_chain.ainvoke = AsyncMock(return_value=mock_response)
                    
                    # Mock prompt template
                    mock_prompt_instance = Mock()
                    mock_prompt.from_messages.return_value = mock_prompt_instance
                    mock_prompt_instance.__or__ = Mock(return_value=mock_chain)
                    
                    service = ChatService()
                    response = await service.get_response("What makes a good engineer?")
        
        assert isinstance(response, ChatResponse)
        assert response.role == "assistant"
        assert response.content == "This is a test response about software engineers."
        assert response.id is not None

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @pytest.mark.asyncio
    async def test_get_response_with_history(self):
        """Test response generation with chat history."""
        mock_response = Mock()
        mock_response.content = "Follow-up response based on history."
        
        chat_history = [
            ChatMessage(role="user", content="Previous question"),
            ChatMessage(role="assistant", content="Previous answer")
        ]
        
        with patch('src.services.llm_factory.LLMFactory.create_generation_llm') as mock_llm_factory:
            with patch('src.services.chat.ChatPromptTemplate') as mock_prompt:
                with patch('src.services.chat.get_settings') as mock_settings:
                    mock_settings.return_value.openai_api_key = 'test-key'
                    
                    # Mock the chain
                    mock_chain = AsyncMock()
                    mock_chain.ainvoke = AsyncMock(return_value=mock_response)
                    
                    # Mock prompt template
                    mock_prompt_instance = Mock()
                    mock_prompt.from_messages.return_value = mock_prompt_instance
                    mock_prompt_instance.__or__ = Mock(return_value=mock_chain)
                    
                    service = ChatService()
                    response = await service.get_response(
                        "Follow-up question", 
                        chat_history=chat_history
                    )
        
        assert isinstance(response, ChatResponse)
        assert response.content == "Follow-up response based on history."

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @pytest.mark.asyncio
    async def test_get_response_error_handling(self):
        """Test error handling in get_response."""
        with patch('src.services.llm_factory.LLMFactory.create_generation_llm') as mock_llm_factory:
            with patch('src.services.chat.ChatPromptTemplate') as mock_prompt:
                with patch('src.services.chat.get_settings') as mock_settings:
                    mock_settings.return_value.openai_api_key = 'test-key'
                    
                    # Mock the chain to raise an exception
                    mock_chain = AsyncMock()
                    mock_chain.ainvoke = AsyncMock(side_effect=Exception("OpenAI API error"))
                    
                    # Mock prompt template
                    mock_prompt_instance = Mock()
                    mock_prompt.from_messages.return_value = mock_prompt_instance
                    mock_prompt_instance.__or__ = Mock(return_value=mock_chain)
                    
                    service = ChatService()
                    
                    with pytest.raises(Exception):
                        await service.get_response("Test message")


class TestChatModels:
    """Test cases for chat data models."""

    def test_chat_request_valid(self):
        """Test valid chat request."""
        from src.models.chat import ChatRequest
        
        request = ChatRequest(message="What makes a good engineer?")
        assert request.message == "What makes a good engineer?"

    def test_chat_request_empty_message(self):
        """Test chat request with empty message fails validation."""
        from src.models.chat import ChatRequest
        
        with pytest.raises(ValueError):
            ChatRequest(message="")

    def test_chat_response_valid(self):
        """Test valid chat response."""
        response = ChatResponse(
            id="test-123",
            role="assistant",
            content="Test response",
            timestamp=datetime.utcnow()
        )
        
        assert response.id == "test-123"
        assert response.role == "assistant"
        assert response.content == "Test response"
        assert isinstance(response.timestamp, datetime)

    def test_chat_response_default_timestamp(self):
        """Test chat response with default timestamp."""
        response = ChatResponse(
            id="test-123",
            role="assistant",
            content="Test response"
        )
        
        assert isinstance(response.timestamp, datetime)

    def test_chat_message_valid(self):
        """Test valid chat message."""
        message = ChatMessage(role="user", content="Test message")
        assert message.role == "user"
        assert message.content == "Test message"

    def test_chat_message_invalid_role(self):
        """Test chat message with invalid role."""
        with pytest.raises(ValueError):
            ChatMessage(role="invalid", content="Test message")