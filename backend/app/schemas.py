from typing import List, Optional
from pydantic import BaseModel


class Citation(BaseModel):
    title: str
    snippet: str
    source_type: str = "document"


class Message(BaseModel):
    role: str
    content: str


class Conversation(BaseModel):
    id: int
    title: str
    role: str
    messages: List[Message]


class ChatRequest(BaseModel):
    conversation_id: Optional[int] = None
    role: str
    message: str


class ChatResponse(BaseModel):
    conversation_id: int
    answer: str
    citations: List[Citation]


class FeedbackRequest(BaseModel):
    conversation_id: int
    message_index: int
    value: int


class FeedbackItem(BaseModel):
    id: int
    conversation_id: int
    message_index: int
    value: int


class IngestRequest(BaseModel):
    role: str
    title: str
    content: str
    category: str = "General"


class Document(BaseModel):
    id: int
    title: str
    content: str
    category: str


class AdminStats(BaseModel):
    total_conversations: int
    total_messages: int
    total_documents: int
    total_feedback: int
    positive_feedback: int


class ProviderStatus(BaseModel):
    provider: str
    model: str
    configured: bool


class RetrievalTrace(BaseModel):
    id: int
    conversation_id: int
    user_message: str
    retrieval_query: str
    provider: str
    model: str
    answer_preview: str
    citations: List[Citation]
