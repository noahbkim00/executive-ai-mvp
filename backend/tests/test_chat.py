"""Tests for chat endpoint and service."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime

from src.main import app
from src.services.chat import ChatService
from src.models.chat import ChatMessage, ChatResponse


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


class TestChatAPI:
    """Test cases for chat API endpoints."""

    def test_chat_endpoint_success(self, client):
        """Test successful chat endpoint call."""
        # Mock the chat service to avoid OpenAI API calls in tests
        mock_response = ChatResponse(
            id="test-123",
            role="assistant",
            content="This is a test response about candidates.",
            timestamp=datetime.utcnow()
        )
        
        with patch('src.routers.chat.ChatService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_response = AsyncMock(return_value=mock_response)
            mock_service_class.return_value = mock_service
            
            response = client.post(
                "/api/chat/",
                json={"message": "What makes a good engineer?"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-123"
        assert data["role"] == "assistant"
        assert data["content"] == "This is a test response about candidates."
        assert "timestamp" in data

    def test_chat_endpoint_empty_message(self, client):
        """Test chat endpoint with empty message."""
        response = client.post(
            "/api/chat/",
            json={"message": ""}
        )
        
        assert response.status_code == 422  # Validation error

    def test_chat_endpoint_missing_message(self, client):
        """Test chat endpoint with missing message field."""
        response = client.post(
            "/api/chat/",
            json={}
        )
        
        assert response.status_code == 422  # Validation error

    def test_chat_endpoint_invalid_json(self, client):
        """Test chat endpoint with invalid JSON."""
        response = client.post(
            "/api/chat/",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422

    def test_chat_endpoint_service_error(self, client):
        """Test chat endpoint when service raises an error."""
        with patch('src.routers.chat.ChatService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_response = AsyncMock(side_effect=Exception("Service error"))
            mock_service_class.return_value = mock_service
            
            response = client.post(
                "/api/chat/",
                json={"message": "Test message"}
            )
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to process your message" in data["detail"]

    def test_chat_endpoint_missing_api_key(self, client):
        """Test chat endpoint when OpenAI API key is missing."""
        with patch('src.routers.chat.ChatService') as mock_service_class:
            mock_service_class.side_effect = ValueError("OPENAI_API_KEY environment variable is not set")
            
            response = client.post(
                "/api/chat/",
                json={"message": "Test message"}
            )
        
        assert response.status_code == 500
        data = response.json()
        assert "Chat service unavailable" in data["detail"]


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