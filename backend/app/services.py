from typing import List, Tuple
import httpx

from app.config import settings
from app.db import db
from app.schemas import Citation, Document


def tokenize(text: str) -> List[str]:
    return [token.strip(".,!?():;").lower() for token in text.split() if token.strip()]


def score_documents(query: str, documents: List[Document]) -> List[Tuple[int, Document]]:
    query_terms = tokenize(query)
    scored: List[Tuple[int, Document]] = []

    for doc in documents:
        haystack = tokenize(f"{doc.title} {doc.category} {doc.content}")
        score = 0
        for term in query_terms:
            score += haystack.count(term)
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:4]


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
    for _, doc in scored:
        citations.append(
            Citation(
                title=f"{doc.title} ({doc.category})",
                snippet=doc.content[:220],
                source_type="document",
            )
        )
    return citations


def build_mock_answer(query: str, citations: List[Citation]) -> str:
    summary_lines = "\n".join([f"- {c.title}: {c.snippet}" for c in citations])

    return (
        f"I found relevant internal guidance for your question.\n\n"
        f"Question:\n{query}\n\n"
        f"Relevant sources:\n{summary_lines}\n\n"
        f"Recommended response:\n"
        f"Based on the available documentation, follow the established internal process described in the cited materials. "
        f"If your case involves an exception, approval dependency, or a deadline-sensitive issue, confirm it with the responsible owner before acting."
    )


async def generate_openai_compatible_answer(query: str, citations: List[Citation]) -> str:
    if not settings.openai_compatible_base_url or not settings.openai_compatible_model:
        return "The LLM provider is configured as openai_compatible, but the base URL or model is missing."

    evidence = "\n".join([f"- {c.title}: {c.snippet}" for c in citations])

    payload = {
        "model": settings.openai_compatible_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an internal knowledge assistant. "
                    "Use only the provided evidence. "
                    "If evidence is weak or incomplete, say so clearly."
                ),
            },
            {
                "role": "user",
                "content": f"Question: {query}\n\nEvidence:\n{evidence}",
            },
        ],
        "temperature": 0.2,
    }

    headers = {"Content-Type": "application/json"}
    if settings.openai_compatible_api_key:
        headers["Authorization"] = f"Bearer {settings.openai_compatible_api_key}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.openai_compatible_base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as exc:
        return f"Failed to call the LLM provider: {exc}"


async def generate_answer(query: str, citations: List[Citation]) -> str:
    if settings.llm_provider == "openai_compatible":
        return await generate_openai_compatible_answer(query, citations)
    return build_mock_answer(query, citations)
