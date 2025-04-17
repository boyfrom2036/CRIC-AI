from langchain.schema import BaseChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from typing import Dict, Tuple

class SessionManager:
    def __init__(self):
        self.store: Dict[str, BaseChatMessageHistory] = {}
    
    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """Get or create a session history for the given session ID."""
        if session_id not in self.store:
            self.store[session_id] = InMemoryChatMessageHistory()
        return self.store[session_id]