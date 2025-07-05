"""Service-specific exceptions for better error handling."""


class ServiceError(Exception):
    """Base exception for all service errors."""
    pass


class ResearchError(ServiceError):
    """Raised when company research operations fail."""
    pass


class QuestionGenerationError(ServiceError):
    """Raised when question generation fails."""
    pass


class RequirementsExtractionError(ServiceError):
    """Raised when requirements extraction fails."""
    pass


class LLMError(ServiceError):
    """Raised when LLM operations fail."""
    pass