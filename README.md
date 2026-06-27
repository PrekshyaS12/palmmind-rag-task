# RAG Service 

A backend with two REST APIs built with FastAPI:

1. Document Ingestion API — user uploads a PDF/TXT file, retrieve its text, chunk it into smaller pieces using one of two selectable strategies, embbed the chunks, and store everything in Pinecone for later retrieval.
2. Conversational RAG API — user asks information about uploaded documents and get answers grounded in their content. The chat keeps track of conversation using Redis and allows to book an interview direct from the chat where it picks out the name, email, date, and time from the message.

Built as an assignment for the AI/ML Intern role at Palm Mind Technology.

-----

## Tech stack

| Piece | Tool | Why |
|---|---|---|
| API framework | FastAPI | async, typed, auto-generates interactive docs |
| LLM + embeddings | Google Gemini (`gemini-2.5-flash`, `gemini-embedding-001`) | free tier, no billing setup required |
| Vector DB | Pinecone | as per instructions (FAISS/Chroma were not allowed) |
| Relational DB | SQLite via SQLAlchemy | zero setup locally; flexible as we can swap to Postgres by changing one env var |
| Chat memory | Redis | fast key-value store, automatically expires old sessions via TTL |
| PDF parsing | pypdf | simple, no external dependencies |

**Note on LLM choice:** the task didn't specify a particular LLM provider. From instruction, a vector DB from the approved list only be used and that no chain library (e.g. `RetrievalQAChain`) be used. I used Gemini's free tier instead of OpenAI to avoid adding a billing requirement while building. Swapping providers only touches `services/embeddings.py`, `services/retrieval.py`, and `services/booking.py` and nothing else in the app talks to the LLM directly.

---

## Architecture

```
app/
├── main.py                  # FastAPI app entrypoint, mounts routers
├── config.py                # typed settings, loaded from .env
├── db/
│   ├── models.py            # SQLAlchemy tables: Document, ChunkMeta, Booking
│   └── session.py           # DB engine + get_db dependency
├── schemas/
│   ├── ingestion.py         # request/response shapes for ingestion
│   └── chat.py              # request/response shapes for chat
├── services/
│   ├── extraction.py        # PDF/TXT text extraction
│   ├── chunking.py          # fixed_size + recursive_sentence strategies
│   ├── embeddings.py        # embed text (Gemini) + store/search (Pinecone)
│   ├── retrieval.py         # custom RAG: retrieve -> build prompt -> call LLM
│   ├── memory.py            # Redis-backed chat history per session_id
│   └── booking.py           # LLM extracts booking details, validates, saves
└── routers/
    ├── ingestion.py         # POST /documents/upload
    └── chat.py               # POST /chat
```

**Why SQL *and* a vector DB:** Structured facts (filenames, upload status, which chunks belong to which document, booking details) live in SQL. The actual chunk text + its embedding vector live in Pinecone, tagged with the same ID used in SQL, so the two stay in sync.

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
    Free Gemini key from aistudio.google.com and a free Pinecone key from pinecone.io.

4. **Run Redis** (for chat memory)
   ```bash
   docker run -d --name redis-palmmind -p 6379:6379 redis:7-alpine
   ```

5. **Run the app**
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Try it out**

   Go to `http://127.0.0.1:8000/docs` — where you can try both endpoints.
---

7. **What was tested**

- Uploaded a .txt file with recursive_sentence chunking and pdf with fixed_size — got back a 201, document marked ready.

- Asked a question through /chat about that uploaded file and got an answer genuinely grounded in its content.

- Sent a booking request ("I'd like to book an interview, my name is A, email B, on date C at time D") — all four fields were extracted correctly, saved to the bookings table.

- Sent a follow-up message in the same session ("what questions did i ask ?") and it correctly recalled the answer.

- Run python -c "import sqlite3; conn = sqlite3.connect('app_data.db'); print(conn.execute('SELECT filename, status, chunk_count FROM documents').fetchall())" — every uploaded file showed up with status='ready'.

8. **Can be done**
- Instead of synchronous handling, allow background processing for uploads.
- Basic auth on the endpoints.
- Hybrid search to catch exact names, numbers, and other proper nouns that pure semantic search misses.

