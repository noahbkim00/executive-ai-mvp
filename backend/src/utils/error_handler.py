"""Standardized error handling utilities."""

from typing import TypeVar, Callable, Optional
from logging import Logger

from ..exceptions.service_exceptions import ServiceError
from ..logger import logger as default_logger

T = TypeVar('T')


class ErrorHandler:
    """Utility class for consistent error handling across services."""
    
    @staticmethod
    def handle_with_fallback(
        operation: Callable[[], T],
        fallback_fn: Callable[[], T],
        error_message: str,
        logger: Optional[Logger] = None,
        raise_on_fallback_failure: bool = True
    ) -> T:
        """Execute operation with fallback on error.
        
        Args:
            operation: Primary operation to execute
            fallback_fn: Fallback function if operation fails
            error_message: Message to log on primary operation failure
            logger: Logger instance to use (defaults to app logger)
            raise_on_fallback_failure: Whether to raise if fallback also fails
            
        Returns:
            Result from operation or fallback
            
        Raises:
            ServiceError: If both operation and fallback fail (when raise_on_fallback_failure=True)
        """
        if logger is None:
            logger = default_logger
            
        try:
            return operation()
        except Exception as e:
            logger.error(f"{error_message}: {str(e)}", exc_info=True)
            
            try:
                logger.warning("Attempting fallback operation...")
                result = fallback_fn()
                logger.info("Fallback operation successful")
                return result
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {str(fallback_error)}", exc_info=True)
                
                if raise_on_fallback_failure:
                    raise ServiceError(
                        f"Both primary and fallback operations failed: {error_message}"
                    ) from fallback_error
                else:
                    # Return None or handle as needed
                    raise
    
    @staticmethod
    async def handle_with_fallback_async(
        operation: Callable[[], T],
        fallback_fn: Callable[[], T],
        error_message: str,
        logger: Optional[Logger] = None,
        raise_on_fallback_failure: bool = True
    ) -> T:
        """Async version of handle_with_fallback.
        
        Args:
            operation: Primary async operation to execute
            fallback_fn: Fallback async function if operation fails
            error_message: Message to log on primary operation failure
            logger: Logger instance to use (defaults to app logger)
            raise_on_fallback_failure: Whether to raise if fallback also fails
            
        Returns:
            Result from operation or fallback
            
        Raises:
            ServiceError: If both operation and fallback fail (when raise_on_fallback_failure=True)
        """
        if logger is None:
            logger = default_logger
            
        try:
            return await operation()
        except Exception as e:
            logger.error(f"{error_message}: {str(e)}", exc_info=True)
            
            try:
                logger.warning("Attempting fallback operation...")
                result = await fallback_fn()
                logger.info("Fallback operation successful")
                return result
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {str(fallback_error)}", exc_info=True)
                
                if raise_on_fallback_failure:
                    raise ServiceError(
                        f"Both primary and fallback operations failed: {error_message}"
                    ) from fallback_error
                else:
                    # Return None or handle as needed
                    raise