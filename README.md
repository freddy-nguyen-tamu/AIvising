# Knowledge Assistant

A polished MVP chatbot for internal knowledge retrieval.

## Stack
- React + Vite + TypeScript
- FastAPI
- In-memory document store for demo
- Retrieval-ready service abstraction
- Admin dashboard
- Feedback collection

## Features
- Professional chat UI
- Conversations sidebar
- Role toggle (member/admin)
- Document ingestion
- Answer citations
- Feedback tracking
- Admin analytics

## Run backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

## Run frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend: [http://localhost:5173](http://localhost:5173)
Backend docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Notes

This is a clean MVP:

* no SSO
* no external vector DB yet
* no persistent DB yet

It is intentionally designed to be easy to demo and extend into:

* Pinecone / pgvector
* OpenAI-compatible or local LLM endpoint
* AWS deployment
* auth / permissions
