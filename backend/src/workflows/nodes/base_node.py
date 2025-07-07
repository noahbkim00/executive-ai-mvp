"""Base node class for executive search workflow nodes."""

from abc import ABC, abstractmethod
from typing import Dict, Any
from datetime import datetime

from ..state_schema import ExecutiveSearchState


class BaseNode(ABC):
    """Abstract base class for workflow nodes."""
    
    def __init__(self, node_name: str):
        """Initialize the node with a name."""
        self.node_name = node_name
    
    @abstractmethod
    async def execute(self, state: ExecutiveSearchState) -> ExecutiveSearchState:
        """Execute the node logic."""
        pass
    
    def _update_state_metadata(self, state: ExecutiveSearchState) -> Dict[str, Any]:
        """Update state with common metadata."""
        node_history = state.get("node_history", [])
        node_history.append(self.node_name)
        
        return {
            **state,
            "node_history": node_history,
            "updated_at": datetime.now()
        }
    
    def _handle_error(self, state: ExecutiveSearchState, error: Exception) -> ExecutiveSearchState:
        """Handle errors in node execution."""
        retry_count = state.get("retry_count", 0)
        
        return {
            **state,
            "error_message": str(error),
            "retry_count": retry_count + 1,
            "next_action": "error_recovery" if retry_count < 3 else "fallback",
            "updated_at": datetime.now()
        }