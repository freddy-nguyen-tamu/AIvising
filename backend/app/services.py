from typing import List, Tuple
import httpx

from app.config import settings
from app.db import db
from app.schemas import Citation, Document


def score_documents(query: str, documents: List[Document]) -> List[Tuple[int, Document]]:
    query_terms = [term.lower() for term in query.split() if term.strip()]
    scored: List[Tuple[int, Document]] = []

    for doc in documents:
        text = f"{doc.title} {doc.content}".lower()
        score = sum(text.count(term) for term in query_terms)
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[:3]



def retrieve_citations(query: str) -> List[Citation]:
    docs = db.list_documents()
    scored = score_documents(query, docs)

    if not scored:
        return [
            Citation(
                title="No matching internal document",
                snippet="The system did not find a closely matching policy document. A human advisor should verify this answer.",
                source_type="system",
            )
        ]

    citations: List[Citation] = []
    for _, doc in scored:
        citations.append(
            Citation(
                title=doc.title,
                snippet=doc.content[:220],
                source_type="document",
            )
        )
    return citations


async def generate_answer(query: str, citations: List[Citation]) -> str:
    if settings.llm_provider == "openai_compatible":
        return await generate_openai_compatible_answer(query, citations)

    joined = "\n".join([f"- {c.title}: {c.snippet}" for c in citations])
    return (
        f"Here is a draft answer based on the available advising documents:\n\n"
        f"Question: {query}\n\n"
        f"Relevant information:\n{joined}\n\n"
        f"Suggested response:\n"
        f"Based on the current internal guidance, the user should follow the documented advising procedure and verify any deadline- or program-specific exception with the appropriate academic advisor or department office."
    )


async def generate_openai_compatible_answer(query: str, citations: List[Citation]) -> str:
    if not settings.openai_compatible_base_url or not settings.openai_compatible_model:
        return "LLM provider is set to openai_compatible, but the base URL or model is missing."

    evidence = "\n".join([f"- {c.title}: {c.snippet}" for c in citations])

    payload = {
        "model": settings.openai_compatible_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an advising assistant. Answer only using the provided evidence. "
                    "If the evidence is insufficient, say so clearly."
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
        return f"Failed to call LLM provider: {exc}"
