# AIvising

AIvising is a polished internal knowledge assistant demo built to showcase the kind of UI/UX, full-stack, and LLM integration work expected in an AI-assisted advising or policy-support tool.

It combines a React frontend, FastAPI backend, retrieval-style document lookup, admin document ingestion, feedback capture, and Groq-hosted Llama inference behind a clean chat experience.

## What It Demonstrates
- Product-style UI/UX with a dark, gradient-driven interface
- React + TypeScript frontend work in a realistic internal-tool layout
- FastAPI backend APIs for chat, admin analytics, feedback, and document ingestion
- Retrieval-augmented generation patterns using selective context instead of sending the full knowledge base each turn
- Groq-hosted Llama chat inference through a production-style API integration
- Admin-only knowledge base updates for adding new documents into the system

## Current Stack
- React + Vite + TypeScript
- FastAPI
- In-memory document store for demo data
- Chunk-based retrieval over internal documents
- Groq API using `llama-3.1-8b-instant`
- Admin dashboard and feedback tracking

## Current Features
- Branded AIvising chat interface
- Conversation history sidebar
- Role toggle for `member` and `admin`
- Source citations returned with answers
- Admin dashboard metrics
- Admin-only document ingestion
- Feedback capture on assistant responses
- Scroll-reactive animated background treatment

## How Answering Works
1. A user asks a question in the chat UI.
2. The backend builds a retrieval query using the latest user prompt plus recent conversation context.
3. The app scores document chunks and selects only the top relevant snippets.
4. Those snippets are passed to Groq along with a prompt wrapper and recent conversation history.
5. The model generates a grounded response, and the UI displays both the answer and citations.

This keeps the system closer to a real RAG pipeline than a toy chatbot and avoids sending the entire document set on every request.

## Run With Docker
Create `backend/.env` first:

```env
APP_NAME=AIvising API
ENV=dev
CORS_ORIGINS=http://localhost:5173
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_key_here
GROQ_MODEL=llama-3.1-8b-instant
RETRIEVAL_TOP_K=4
RETRIEVAL_MAX_CONTEXT_CHARS=1800
CONVERSATION_CONTEXT_MESSAGES=6
LLM_TEMPERATURE=0.2
```

Then run:

```bash
docker compose up --build
```

Frontend: [http://localhost:5173](http://localhost:5173)  
Backend docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Run Locally Without Docker
Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# add your GROQ_API_KEY and set LLM_PROVIDER=groq
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Admin Workflow
- Switch the role selector to `Admin`
- Open `Admin Dashboard`
- Add a document through the ingestion form
- The new document is immediately available to retrieval

At the moment, documents are stored in memory, so restarting the backend resets the knowledge base.

## Current Limitations
- No persistent database yet
- No authentication or SSO
- No external vector database yet
- Retrieval is lexical and chunk-based rather than embedding-based
- No file upload ingestion pipeline yet

## Strong Next Steps
- Replace in-memory storage with SQLite + SQLAlchemy
- Add embedding-based retrieval with Pinecone or pgvector
- Add provider status / health visibility in the UI
- Add authentication and role enforcement beyond client-selected demo roles
- Expand ingestion from text entry to file, web, or Drive sources

## Why This Repo Is Positioned This Way
This project is intentionally framed as a realistic internal AI assistant rather than a generic chatbot. It is designed to highlight:
- user-centered UI decisions
- admin tooling
- backend ownership
- retrieval and prompt-wrapper thinking
- practical AI product integration using hosted inference

That makes it a stronger portfolio piece for roles involving AI-assisted advising, policy guidance, internal support tooling, or similar human-centered LLM products.
