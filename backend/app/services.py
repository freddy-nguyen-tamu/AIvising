from typing import List, Tuple
import asyncio
import re

import httpx

from app.config import settings
from app.db import db
from app.local_llm import generate_local_adapter_answer
from app.schemas import Citation, Document, Message


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def tokenize(text: str) -> List[str]:
    return [token.strip(".,!?():;").lower() for token in text.split() if token.strip()]


def split_into_chunks(document: Document, max_chars: int = 320) -> List[str]:
    sentences = [
        sentence.strip()
        for sentence in document.content.replace("\n", " ").split(". ")
        if sentence.strip()
    ]

    if not sentences:
        return [document.content[:max_chars]]

    chunks: List[str] = []
    current = ""

    for sentence in sentences:
        candidate = f"{current}. {sentence}" if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current.strip())
        current = sentence

    if current:
        chunks.append(current.strip())

    return chunks or [document.content[:max_chars]]


def score_documents(query: str, documents: List[Document]) -> List[Tuple[int, Document, str]]:
    query_terms = tokenize(query)
    scored: List[Tuple[int, Document, str]] = []

    for doc in documents:
        for chunk in split_into_chunks(doc):
            haystack = tokenize(f"{doc.title} {doc.category} {chunk}")
            score = 0
            for term in query_terms:
                score += haystack.count(term)
            if score > 0:
                if query.lower() in chunk.lower():
                    score += 2
                scored.append((score, doc, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[: settings.retrieval_top_k]


def build_retrieval_query(message: str, conversation_messages: List[Message] | None = None) -> str:
    recent_messages = conversation_messages or []
    recent_user_turns = [
        item.content.strip()
        for item in recent_messages[-settings.conversation_context_messages :]
        if item.role == "user" and item.content.strip()
    ]
    combined = " ".join(recent_user_turns[-2:] + [message.strip()])
    return combined.strip() or message.strip()


def retrieve_citations(query: str) -> List[Citation]:
    scored = score_documents(query, db.list_documents())

    if not scored:
        return [
            Citation(
                title="No strong match found",
                snippet="No closely related knowledge base document was found. A team member should verify the answer.",
                source_type="system",
            )
        ]

    citations: List[Citation] = []
    for _, doc, chunk in scored:
        citations.append(
            Citation(
                title=f"{doc.title} ({doc.category})",
                snippet=chunk[:220],
                source_type="document",
            )
        )
    return citations


def build_mock_answer(query: str, citations: List[Citation], conversation_messages: List[Message]) -> str:
    summary_lines = "\n".join([f"- {c.title}: {c.snippet}" for c in citations])
    recent_context = "\n".join(
        f"{message.role.title()}: {message.content}"
        for message in conversation_messages[-settings.conversation_context_messages :]
    )


def get_provider_snapshot() -> tuple[str, str, bool]:
    provider = settings.llm_provider
    model = "mock-template"
    configured = True

    if provider == "groq":
        model = settings.groq_model
        configured = bool(settings.groq_api_key)
    elif provider == "local_adapter":
        model = f"{settings.local_base_model} + {settings.local_adapter_path}"
        configured = bool(settings.local_base_model and settings.local_adapter_path)

    return provider, model, configured

    return (
        f"I found relevant internal guidance for your question.\n\n"
        f"Recent conversation:\n{recent_context or 'No prior context'}\n\n"
        f"Question:\n{query}\n\n"
        f"Relevant sources:\n{summary_lines}\n\n"
        f"Recommended response:\n"
        f"Based on the available documentation, follow the established internal process described in the cited materials. "
        f"If your case involves an exception, approval dependency, or a deadline-sensitive issue, confirm it with the responsible owner before acting."
    )


def parse_retry_after_seconds(response: httpx.Response) -> float:
    retry_after = response.headers.get("retry-after")
    if retry_after:
        try:
            return float(retry_after)
        except ValueError:
            pass

    try:
        payload = response.json()
        message = payload.get("error", {}).get("message", "")
        match = re.search(r"try again in\s+([0-9]*\.?[0-9]+)s", message, re.IGNORECASE)
        if match:
            return float(match.group(1))
    except Exception:
        pass

    return 2.0


def build_evidence_block(citations: List[Citation]) -> str:
    evidence_lines: List[str] = []
    current_chars = 0

    for index, citation in enumerate(citations, start=1):
        line = f"[{index}] {citation.title}: {citation.snippet}"
        if current_chars + len(line) > settings.retrieval_max_context_chars:
            break
        evidence_lines.append(line)
        current_chars += len(line)

    return "\n".join(evidence_lines)


def build_chat_messages(query: str, citations: List[Citation], conversation_messages: List[Message]) -> List[dict]:
    evidence = build_evidence_block(citations)
    recent_turns = conversation_messages[-settings.conversation_context_messages :]
    history_lines = [
        f"{message.role.title()}: {message.content}"
        for message in recent_turns
    ]
    history_text = "\n".join(history_lines) if history_lines else "No prior conversation."

    return [
        {
            "role": "system",
            "content": (
                "You are AIvising, an internal knowledge assistant for workplace policy and process questions. "
                "Answer clearly and professionally using only the retrieved evidence when possible. "
                "If the evidence is incomplete, say that directly and recommend a human follow-up. "
                "Prefer concise, actionable responses with 2-4 short paragraphs or bullets when useful. "
                "Do not claim to have searched documents outside the provided evidence."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Recent conversation:\n{history_text}\n\n"
                f"Latest user question:\n{query}\n\n"
                f"Retrieved evidence:\n{evidence or 'No strong evidence found.'}\n\n"
                "Write a helpful answer grounded in the evidence. "
                "If there is uncertainty, say what is missing."
            ),
        },
    ]


async def generate_groq_answer(
    query: str,
    citations: List[Citation],
    conversation_messages: List[Message],
) -> str:
    if not settings.groq_api_key:
        return "The LLM provider is configured as groq, but GROQ_API_KEY is missing."

    payload = {
        "model": settings.groq_model,
        "messages": build_chat_messages(query, citations, conversation_messages),
        "temperature": settings.llm_temperature,
        "max_tokens": 500,
    }

    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    backoff = 1.0
    max_retries = 8

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(1, max_retries + 1):
            try:
                response = await client.post(
                    GROQ_API_URL,
                    json=payload,
                    headers=headers,
                )
            except httpx.RequestError as exc:
                if attempt == max_retries:
                    return f"Failed to call the Groq API: {exc}"
                await sleep_with_retry(backoff + 0.25)
                backoff = min(backoff * 1.6, 20.0)
                continue

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]

            if response.status_code == 429 and attempt < max_retries:
                wait_seconds = max(parse_retry_after_seconds(response), backoff) + 0.25
                await sleep_with_retry(wait_seconds)
                backoff = min(backoff * 1.6, 20.0)
                continue

            if response.status_code >= 500 and attempt < max_retries:
                await sleep_with_retry(backoff + 0.25)
                backoff = min(backoff * 1.6, 20.0)
                continue

            return f"Groq API error: {response.status_code} {response.text}"

    return "Groq API error: too many retries."


async def sleep_with_retry(seconds: float) -> None:
    await asyncio.sleep(seconds)


async def generate_answer(
    query: str,
    citations: List[Citation],
    conversation_messages: List[Message],
) -> str:
    if settings.llm_provider == "local_adapter":
        try:
            messages = build_chat_messages(query, citations, conversation_messages)
            return generate_local_adapter_answer(messages)
        except Exception as exc:
            return f"Local adapter inference error: {exc}"
    if settings.llm_provider == "groq":
        return await generate_groq_answer(query, citations, conversation_messages)
    return build_mock_answer(query, citations, conversation_messages)
