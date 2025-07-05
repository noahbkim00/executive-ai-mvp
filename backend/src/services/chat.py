import uuid
from typing import List

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from ..models.chat import ChatMessage, ChatResponse
from ..config import get_settings
from ..services.llm_factory import LLMFactory
from ..logger import logger


class ChatService:
    def __init__(self):
        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please set it in your .env file or environment."
            )
        
        # Initialize LLM using factory
        self.llm = LLMFactory.create_generation_llm()
        
        # System prompt for candidate analysis
        self.system_prompt = """You are an AI assistant specialized in analyzing and discussing candidates 
for various positions. You help users evaluate candidate descriptions, provide insights about their 
qualifications, and answer questions about hiring and talent assessment. 

Be helpful, professional, and objective in your responses. If a user provides a candidate description, 
analyze their strengths, potential areas for development, and suitability for different roles."""
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])
        
        # Create the chain
        self.chain = self.prompt | self.llm
    
    async def get_response(
        self, 
        message: str, 
        chat_history: List[ChatMessage] = None
    ) -> ChatResponse:
        """
        Get AI response for a user message with optional chat history
        """
        try:
            # Convert chat history to LangChain messages
            messages = []
            if chat_history:
                for msg in chat_history:
                    if msg.role == "user":
                        messages.append(HumanMessage(content=msg.content))
                    elif msg.role == "assistant":
                        messages.append(AIMessage(content=msg.content))
                    elif msg.role == "system":
                        messages.append(SystemMessage(content=msg.content))
            
            # Invoke the chain
            response = await self.chain.ainvoke({
                "chat_history": messages,
                "input": message
            })
            
            # Create response
            return ChatResponse(
                id=str(uuid.uuid4()),
                role="assistant",
                content=response.content
            )
            
        except Exception as e:
            logger.error(f"Error getting chat response: {str(e)}")
            raise