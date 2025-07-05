"""Centralized factory for creating LLM instances with consistent configurations."""

from langchain_openai import ChatOpenAI
from ..config import get_settings
from ..logger import logger


class LLMFactory:
    """Factory for creating configured LLM instances."""
    
    @staticmethod
    def create_chat_llm(temperature: float = 0.7, model: str = None) -> ChatOpenAI:
        """Create a ChatOpenAI instance with specified configuration.
        
        Args:
            temperature: Temperature for response generation (0.0-1.0)
            model: Model name to use, defaults to configured model
            
        Returns:
            Configured ChatOpenAI instance
        """
        settings = get_settings()
        
        if model is None:
            model = "gpt-4o-mini"  # Default model
            
        logger.debug(f"Creating LLM instance - Model: {model}, Temperature: {temperature}")
        
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=settings.openai_api_key
        )
    
    @staticmethod
    def create_generation_llm() -> ChatOpenAI:
        """Create LLM for creative generation tasks (higher temperature)."""
        return LLMFactory.create_chat_llm(temperature=0.7)
    
    @staticmethod
    def create_extraction_llm() -> ChatOpenAI:
        """Create LLM for data extraction tasks (lower temperature)."""
        return LLMFactory.create_chat_llm(temperature=0.1)
    
    @staticmethod
    def create_validation_llm() -> ChatOpenAI:
        """Create LLM for validation tasks (deterministic)."""
        return LLMFactory.create_chat_llm(temperature=0.0)