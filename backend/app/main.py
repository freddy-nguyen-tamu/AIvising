from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import db
from app.schemas import (
    AdminStats,
    ChatRequest,
    ChatResponse,
    Conversation,
    FeedbackItem,
    FeedbackRequest,
    IngestRequest,
    ProviderStatus,
)
from app.services import build_retrieval_query, generate_answer, retrieve_citations

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    db.seed()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/conversations", response_model=list[Conversation])
def list_conversations():
    return db.list_conversations()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    if payload.conversation_id is None:
        conversation = db.create_conversation(role=payload.role, first_user_message=message)
        conversation_id = conversation.id
    else:
        if payload.conversation_id not in db.conversations:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        conversation_id = payload.conversation_id
        db.add_message(conversation_id, "user", message)

    conversation = db.get_conversation(conversation_id)
    retrieval_query = build_retrieval_query(message, conversation.messages)

    citations = retrieve_citations(retrieval_query)
    answer = await generate_answer(message, citations, conversation.messages)
    db.add_message(conversation_id, "assistant", answer)

    return ChatResponse(
        conversation_id=conversation_id,
        answer=answer,
        citations=citations,
    )


@app.post("/api/feedback", response_model=FeedbackItem)
def submit_feedback(payload: FeedbackRequest):
    if payload.conversation_id not in db.conversations:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    if payload.value not in (1, -1):
        raise HTTPException(status_code=400, detail="Feedback value must be 1 or -1.")

    return db.add_feedback(
        conversation_id=payload.conversation_id,
        message_index=payload.message_index,
        value=payload.value,
    )


@app.get("/api/documents")
def list_documents():
    return db.list_documents()


@app.post("/api/documents")
def add_document(payload: IngestRequest):
    if payload.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can add documents.")

    title = payload.title.strip()
    content = payload.content.strip()
    category = payload.category.strip() or "General"

    if not title or not content:
        raise HTTPException(status_code=400, detail="Title and content are required.")

    return db.add_document(title=title, content=content, category=category)


@app.get("/api/admin/stats", response_model=AdminStats)
def admin_stats():
    conversations = db.list_conversations()
    feedback = db.list_feedback()
    documents = db.list_documents()

    total_messages = sum(len(c.messages) for c in conversations)
    positive_feedback = sum(1 for item in feedback if item.value == 1)

    return AdminStats(
        total_conversations=len(conversations),
        total_messages=total_messages,
        total_documents=len(documents),
        total_feedback=len(feedback),
        positive_feedback=positive_feedback,
    )


@app.get("/api/admin/feedback", response_model=list[FeedbackItem])
def admin_feedback():
    return db.list_feedback()


@app.get("/api/admin/provider-status", response_model=ProviderStatus)
def provider_status():
    provider = settings.llm_provider
    model = "mock-template"
    configured = True

    if provider == "groq":
        model = settings.groq_model
        configured = bool(settings.groq_api_key)
    elif provider == "local_adapter":
        model = f"{settings.local_base_model} + {settings.local_adapter_path}"
        configured = bool(settings.local_base_model and settings.local_adapter_path)

    return ProviderStatus(
        provider=provider,
        model=model,
        configured=configured,
    )
