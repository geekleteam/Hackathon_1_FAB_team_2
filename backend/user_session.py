import json
from typing import Dict, List, Optional

from db_utils import fetch_user_chat_from_db, push_user_chat_to_db


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

    def add_chat(self, user_input, model_output, conn):
        chat_dict = {"user": json.dumps(user_input), "model": json.dumps(model_output)}
        self.chats.append(chat_dict)
        push_user_chat_to_db(self.user_id, self.request_id, chat_dict, conn)

    def populate_chat_from_db(self, user_id, request_id, conn):
        self.chats = fetch_user_chat_from_db(user_id, request_id, conn)
        self.user_id = user_id
        self.request_id = request_id

    def flush(self):
        self.history = self.chats
        self.chats = []
        self.user_id = None
        self.request_id = None
        self.model_id = None
        self.model_kwargs = None

    def str_chat(self) -> str:
        return "\n".join(
            [f"User: {chat['user']}\nBot:{chat['model']}" for chat in self.chats]
        )


class ChatSessionManager:
    def __init__(self, conn):
        self.sessions: Dict[str, ChatSession] = {}
        self.conn = conn

    def get_session(self, user_id: str, request_id: str) -> ChatSession:
        if user_id not in self.sessions:
            self.sessions[user_id] = ChatSession()
            self.sessions[user_id].populate_chat_from_db(user_id, request_id, self.conn)
        return self.sessions[user_id]

    def remove_session(self, user_id: str):
        if user_id in self.sessions:
            del self.sessions[user_id]
