# RAG Service

A backend with two REST APIs built with FastAPI:

1. **Document Ingestion API** — user uploads a PDF/TXT file, its text is extracted and chunked using one of two selectable strategies, embedded, and stored in Pinecone for later retrieval. Processing happens asynchronously in the background, so the upload request returns immediately; a separate status endpoint lets the client poll for completion.
2. **Conversational RAG API** — user asks questions about uploaded documents and gets answers grounded in their content. The chat keeps track of conversation using Redis and allows booking an interview directly from the chat, extracting the name, email, date, and time from the message.

Both APIs require an API key, passed via the `X-API-Key` header.

Built as an assignment for the AI/ML Intern role at Palm Mind Technology.

**Live demo:** https://palmmind-rag-task.onrender.com/docs
*(hosted on Render's free tier — the first request after a period of inactivity may take 30-60 seconds while the instance spins back up)*

-----

## Tech stack

| Piece | Tool | Why |
|---|---|---|
| API framework | FastAPI | async, typed, auto-generates interactive docs |
| Auth | API key via custom header (`X-API-Key`) | simple, stateless protection on both endpoints |
| LLM + embeddings | Google Gemini (`gemini-2.5-flash`, `gemini-embedding-001`) | free tier, no billing setup required |
| Vector DB | Pinecone | as per instructions (FAISS/Chroma were not allowed) |
| Relational DB | SQLite locally / Postgres in production, via SQLAlchemy | zero setup locally; swaps to Postgres in production by changing one env var, no code changes |
| Chat memory | Redis | fast key-value store, automatically expires old sessions via TTL |
| PDF parsing | pypdf | simple, no external dependencies |
| Background processing | FastAPI `BackgroundTasks` | keeps upload requests fast by deferring extraction/embedding until after the response is sent |
| Hosting | Render (free tier) | web service + managed Postgres + managed Redis (Key Value) |

**Note on LLM choice:** the task didn't specify a particular LLM provider. From instruction, a vector DB from the approved list only be used and that no chain library (e.g. `RetrievalQAChain`) be used. I used Gemini's free tier instead of OpenAI to avoid adding a billing requirement while building. Swapping providers only touches `services/embeddings.py`, `services/retrieval.py`, and `services/booking.py` and nothing else in the app talks to the LLM directly.

---

## Architecture

```
app/
├── main.py                  # FastAPI app entrypoint, mounts routers
├── config.py                # typed settings, loaded from .env
├── core/
│   └── security.py          # API key verification dependency
├── db/
│   ├── models.py             # SQLAlchemy tables: Document, ChunkMeta, Booking
│   └── session.py            # DB engine + get_db dependency
├── schemas/
│   ├── ingestion.py          # request/response shapes for ingestion
│   └── chat.py                # request/response shapes for chat
├── services/
│   ├── extraction.py         # PDF/TXT text extraction
│   ├── chunking.py            # fixed_size + recursive_sentence strategies
│   ├── embeddings.py          # embed text (Gemini) + store/search (Pinecone)
│   ├── retrieval.py           # custom RAG: retrieve -> build prompt -> call LLM
│   ├── memory.py               # Redis-backed chat history per session_id
│   └── booking.py              # LLM extracts booking details, validates, saves
└── routers/
    ├── ingestion.py           # POST /documents/upload, GET /documents/{document_id}
    └── chat.py                 # POST /chat
tests/
└── test_ingestion.py          # auth + ingestion logic tests
```

**Why SQL *and* a vector DB:** Structured facts (filenames, upload status, which chunks belong to which document, booking details) live in SQL. The actual chunk text + its embedding vector live in Pinecone, tagged with the same ID used in SQL, so the two stay in sync.

**Why background processing:** Extraction, chunking, embedding, and upserting to Pinecone can take several seconds for larger documents. Rather than blocking the client for that whole duration, `POST /documents/upload` validates the file, saves a `PROCESSING` record, and returns a `202 Accepted` response immediately with the new `document_id`. The actual work runs afterward in a background task using its own database session (since the request-scoped session closes once the response is sent). The client polls `GET /documents/{document_id}` to check when status flips to `READY` (or `FAILED`, with the error logged server-side).

---

## Setup

1. **Clone the repo and create a virtual environment**
   ```bash
   git clone <your-repo-url>
   cd palmmind-rag
   python -m venv venv
   venv\Scripts\activate        # Windows
   # source venv/bin/activate   # macOS/Linux
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**

   Copy `.env.example` to `.env` and fill in your own keys:
   ```bash
   cp .env.example .env
   ```
   You'll need:
   - A free Gemini key from aistudio.google.com
   - A free Pinecone key from pinecone.io
   - An `API_KEY` value of your choosing — this is required on every request via the `X-API-Key` header

4. **Run Redis** (for chat memory)
   ```bash
   docker run -d --name redis-palmmind -p 6379:6379 redis:7-alpine
   ```

5. **Run the app**
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Try it out**

   Go to `http://127.0.0.1:8000/docs`. Click the padlock icon at the top of the page, enter your `API_KEY`, and authorize before calling either endpoint.

---

## API overview

| Endpoint | Method | Description |
|---|---|---|
| `/documents/upload` | POST | Upload a PDF/TXT file for ingestion. Returns `202` immediately with `status: "processing"`. |
| `/documents/{document_id}` | GET | Poll for ingestion status. Returns `"processing"`, `"ready"`, or `"failed"`. |
| `/chat` | POST | Ask a question grounded in uploaded documents, or make a booking request in natural language. |

All endpoints require an `X-API-Key` header matching the server's configured `API_KEY`.

---

## What was tested

- Uploaded a `.txt` file with `recursive_sentence` chunking and a PDF with `fixed_size` — both returned `202`, and polling `GET /documents/{document_id}` showed the document flip from `"processing"` to `"ready"` with the correct chunk count.
- Asked a question through `/chat` about an uploaded file and got an answer genuinely grounded in its content.
- Sent a booking request ("I'd like to book an interview, my name is A, email B, on date C at time D") — all four fields were extracted correctly, saved to the bookings table.
- Sent a follow-up message in the same session ("what questions did i ask?") and it correctly recalled the answer.
- Confirmed unauthenticated requests to both endpoints are rejected (`401`/`403`).
- Verified the same flow end-to-end against the live Render deployment, using the production Postgres and Redis instances.

---

## Can be done

- Hybrid search (semantic + keyword) to catch exact names, numbers, and other proper nouns that pure semantic search misses.

---

## Deployment

Hosted on Render's free tier:
- **Web service** running the FastAPI app (Python 3.12, pinned via the `PYTHON_VERSION` environment variable)
- **Managed Postgres** (free tier) for structured data — swapped in from local SQLite by changing `DATABASE_URL`, no code changes needed
- **Managed Key Value (Redis-compatible)** instance for chat memory

