from typing import Dict, List, Optional


class ChatSession:
    def __init__(
        self,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        model_id: Optional[str] = None,
        model_kwargs: Optional[str] = None,
    ):
        self.user_id = user_id
        self.request_id = request_id
        self.model_id = model_id
        self.model_kwargs = model_kwargs
        self.chats: List[Dict[str, str]] = []
        self.history: List[Dict[str, str]] = []

    def add_chat(self, user_input, model_output):
        self.chats.append({"user": user_input, "model": model_output})

    def flush(self):
        self.history = self.chats
        self.chats = []
        self.user_id = None
        self.request_id = None
        self.model_id = None
        self.model_kwargs = None

    def str_chat(self) -> str:
        return "\n".join(
            [f"User: {chat['user']}\nModel:{chat['model']}" for chat in self.chats]
        )


class ChatSessionManager:
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}

    def get_session(self, user_id: str) -> ChatSession:
        if user_id not in self.sessions:
            self.sessions[user_id] = ChatSession()
        return self.sessions[user_id]

    def remove_session(self, user_id: str):
        if user_id in self.sessions:
            del self.sessions[user_id]
