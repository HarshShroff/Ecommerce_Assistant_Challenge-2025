import time
from typing import Dict, Any, Optional, List
import logging
import uuid

logger = logging.getLogger(__name__)

class Session:
    """
    Represents a user session.
    """
    def __init__(self, session_id: str):
        """
        Initializes a new session.

        Args:
            session_id (str): The unique ID of the session.
        """
        self.session_id: str = session_id
        self.created_at: float = time.time()
        self.last_active: float = time.time()
        self.data: Dict[str, Any] = {}
        self.conversation_history: List[Dict[str, Any]] = []
        self.expected_input: Optional[str] = None

    def update_activity(self):
        """
        Updates the last active timestamp for the session.
        """
        self.last_active = time.time()

    def set_data(self, key: str, value: Any):
        """
        Sets a key-value pair in the session's data dictionary.

        Args:
            key (str): The key to set.
            value (Any): The value to set.
        """
        self.data[key] = value
        self.update_activity()

    def get_data(self, key: str, default: Any = None) -> Any:
        """
        Gets a value from the session's data dictionary.

        Args:
            key (str): The key to get.
            default (Any, optional): The default value to return if the key is not found. Defaults to None.

        Returns:
            Any: The value associated with the key, or the default value if the key is not found.
        """
        self.update_activity()
        return self.data.get(key, default)

    def add_to_history(self, role: str, message: str):
        """
        Adds a message to the session's conversation history.

        Args:
            role (str): The role of the message sender (e.g., "user" or "bot").
            message (str): The message to add.
        """
        if not isinstance(message, str):
            logger.warning(f"Attempted to add non-string message to history: {type(message)}")
            message = str(message)
        self.conversation_history.append({
            "role": role,
            "message": message,
            "timestamp": time.time()
        })
        self.update_activity()

    def get_history(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """
        Gets the session's conversation history.

        Args:
            max_messages (int, optional): The maximum number of messages to return. Defaults to 10.

        Returns:
            List[Dict[str, Any]]: The session's conversation history.
        """
        self.update_activity()
        if max_messages <= 0:
            return self.conversation_history
        return self.conversation_history[-max_messages:]

    def set_expected_input(self, expectation: Optional[str]):
        """
        Sets the expected input for the session.

        Args:
            expectation (Optional[str]): The expected input.
        """
        self.expected_input = expectation
        logger.info(f"Session {self.session_id}: Expected input set to '{expectation}'")
        self.update_activity()

    def get_expected_input(self) -> Optional[str]:
        """
        Gets the expected input for the session.

        Returns:
            Optional[str]: The expected input.
        """
        self.update_activity()
        logger.debug(f"Session {self.session_id}: Getting expected input: '{self.expected_input}'")
        return self.expected_input

class SessionManager:
    """
    Manages user sessions.
    """
    def __init__(self, session_expiry_seconds: int = 86400):
        """
        Initializes a new session manager.

        Args:
            session_expiry_seconds (int, optional): The session expiry time in seconds. Defaults to 86400 (24 hours).
        """
        self.sessions: Dict[str, Session] = {}
        self.session_expiry_seconds: int = session_expiry_seconds

    def get_session(self, session_id: Optional[str] = None) -> Session:
        """
        Gets a session by ID. If no ID is provided, a new session is created.

        Args:
            session_id (Optional[str], optional): The ID of the session to get. Defaults to None.

        Returns:
            Session: The session object.
        """
        self._cleanup_expired_sessions()

        if not session_id or session_id == "None" or session_id == "null":
            session_id = None

        if session_id and session_id in self.sessions:
            logger.info(f"Reusing existing session: {session_id}")
            self.sessions[session_id].update_activity()
            return self.sessions[session_id]
        else:
            if session_id:
                logger.info(f"Session ID '{session_id}' not found or expired, creating new.")
            
            new_session_id = str(uuid.uuid4())
            logger.info(f"Creating new session: {new_session_id}")
            new_session = Session(new_session_id)
            self.sessions[new_session_id] = new_session
            return new_session

    def _cleanup_expired_sessions(self):
        """
        Cleans up expired sessions.
        """
        current_time = time.time()
        expired_ids = [
            sid for sid, session_obj in self.sessions.items()
            if (current_time - session_obj.last_active) > self.session_expiry_seconds
        ]
        for sid in list(expired_ids):
            if sid in self.sessions:
                logger.info(f"Session {sid} expired, removing.")
                del self.sessions[sid]

    def end_session(self, session_id: str):
        """
        Ends a session.

        Args:
            session_id (str): The ID of the session to end.
        """
        if session_id in self.sessions:
            logger.info(f"Ending session: {session_id}")
            del self.sessions[session_id]
