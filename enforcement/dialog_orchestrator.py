"""
Dialog Orchestrator for tracking multi-turn conversational state.
This mimics the conversational capabilities of NeMo Guardrails but with a native Pythonic approach.
"""

from typing import Dict, List, Any
import logging
from collections import deque

logger = logging.getLogger(__name__)

class DialogManager:
    """Manages conversational state and dialogue history for multi-turn evaluations."""
    
    def __init__(self, max_history_turns: int = 5):
        """
        Initialize the Dialog Manager.
        
        Args:
            max_history_turns: Maximum number of previous turns to keep in memory per session.
        """
        # In-memory store: { session_id: deque([turn1, turn2, ...]) }
        # Note: For strict production environments, this should be backed by Redis or similar.
        self._sessions: Dict[str, deque] = {}
        self.max_history_turns = max_history_turns
        
    def add_turn(self, session_id: str, utterance: str, evaluation_result: str = None) -> None:
        """
        Add a new conversational turn to the session history.
        
        Args:
            session_id: Unique identifier for the conversation.
            utterance: The LLM response or user prompt to store.
            evaluation_result: Optional context roughly categorizing the turn (e.g. 'safe', 'warned').
        """
        if not session_id:
            return
            
        if session_id not in self._sessions:
            self._sessions[session_id] = deque(maxlen=self.max_history_turns)
            
        self._sessions[session_id].append({
            "text": utterance,
            "status": evaluation_result or "unknown"
        })
        logger.debug(f"Added turn to session '{session_id}'. Total turns: {len(self._sessions[session_id])}")

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        Retrieve the conversational history for a given session.
        
        Args:
            session_id: Unique identifier for the conversation.
            
        Returns:
            A list of dictionary objects representing previous utterances in chronological order.
        """
        if not session_id or session_id not in self._sessions:
            return []
            
        return list(self._sessions[session_id])
    
    def clear_session(self, session_id: str) -> None:
        """Clear memory for a specific session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.debug(f"Cleared session history for '{session_id}'")
