# Inquix — Multi-modal RAG Platform

A fully dockerized, CPU-only RAG (Retrieval-Augmented Generation) platform supporting text, PDF, image, and audio documents with web search, voice input, TTS, and local AI inference.

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Frontend   │────▶│   Backend    │────▶│  PostgreSQL +   │
│  Next.js 14 │     │  FastAPI     │     │  pgvector       │
│  :3000      │◀────│  :8000       │◀────│  :5432          │
└─────────────┘     └──────┬───────┘     └─────────────────┘
                           │
                    ┌──────┴───────┐     ┌──────────────────┐
                    │   Ollama     │     │   OpenAI API     │
                    │  :11434      │     │  (cloud, when    │
                    │  (fallback)  │     │   configured)    │
                    └──────────────┘     └──────────────────┘
```

Four Docker containers:
- **db** — PostgreSQL 16 + pgvector: stores documents, chunks (with vector embeddings), conversations, messages
- **ollama** — Local AI runtime: LLM (`qwen2.5:3b`), embeddings (`nomic-embed-text`), vision model (`llava-phi3:3.8b`) — used as fallback when cloud APIs unavailable
- **backend** — FastAPI Python server: RAG pipeline, API endpoints, streaming, file processing
- **frontend** — Next.js 14 React app: ChatGPT-style UI with streaming, voice, file previews

---

## Full User Flow

### 1. Knowledge Base

A Knowledge Base (KB) is a named, isolated collection of documents and conversations. Users create KBs from the home screen.

```
Home → Create KB → Name it → Redirects to /kb/{id}
```

Each KB has its own:
- Documents and their vector embeddings
- Conversation history
- Chunk index in pgvector

### 2. Document Upload & Indexing

Users upload files (PDF, images, audio, text) through the Document Panel (slide-out from the right).

**Pipeline:**

```
Upload → Extract → Chunk → Embed → Store
```

#### Extraction (`backend/app/services/extraction.py`)

| File Type | Processing |
|-----------|-----------|
| **PDF** | `pypdf` extracts text page by page |
| **Image** | Tesseract OCR + vision model (`llava-phi3:3.8b`) captioning |
| **Audio** | OpenAI Whisper (`whisper-1`) if `OPENAI_API_KEY` set, else `ffmpeg` → WAV → silence detection → `faster-whisper` (local) |
| **Text** | Read directly |

#### Chunking (`backend/app/services/chunking.py`)

Text is split into overlapping chunks:
- Size: 500 tokens (`chunk_size`)
- Overlap: 50 tokens (`chunk_overlap`)

#### Embedding (`backend/app/services/embedding.py`)

Each chunk is embedded via vector model and stored in pgvector. Priority chain:
1. **OpenAI** (`text-embedding-3-small`, 1536-dim) — if `OPENAI_API_KEY` set
2. **Jina AI** (`jina-embeddings-v2-base-en`, 768-dim) — if `JINA_API_KEY` set
3. **Ollama** (`nomic-embed-text`, 768-dim) — local fallback

#### Startup Model Pull (`ensure_models`)

On backend startup, `ensure_models()` in `embedding.py` checks what cloud providers are configured and only pulls Ollama models that have no cloud alternative:
- If OpenAI key is set → no vision model pull needed (GPT-4o handles images natively)
- If Groq key is set → no LLM model pull needed
- If Jina key is set → no embedding model pull needed
- Only pulls models that are actually needed as fallback

### 3. Chat — The Core RAG Loop

When a user sends a message, the following pipeline executes:

#### Step A: Retrieve Relevant Chunks (`retrieval.py`)

```
User query → embed with nomic-embed-text → pgvector cosine similarity search → top K=5 chunks
```

- Chunks below `similarity_threshold: 0.45` are filtered out
- Only chunks from documents with `status = "ready"` are searched

#### Step B: Web Search (conditional) (`web_search.py`)

- If NO document chunk passes the similarity threshold → trigger web search
- If document chunks ARE relevant → skip web search entirely

**Web search chain (tries each in order until results found):**

1. **DuckDuckGo** (`duckduckgo_search` library) — synchronous, fast
2. **crawl4ai** — scrapes the top DuckDuckGo result URL
3. **Wikipedia API** — fetches summary page
4. Results tagged with `source_type: "web"` and appended to chunk list

#### Step C: Build LLM Context (`generation.py:build_messages()`)

The function constructs a structured message array:

```
SYSTEM MESSAGE:
  Rules:
    1. Use uploaded files ONLY if they contain the specific info requested
    2. If files lack exact details, use general knowledge
    3. When using general knowledge, start with "Based on my general knowledge:"
    4. Cite sources as [1], [2] when using file content
    5. Be helpful and direct

  Context:
    — Document chunks (non-web, with filename + relevance %)
    — Web search results (with source URL)

CHAT HISTORY:
  — Last 6 messages (user/assistant alternation)

USER MESSAGE:
  — Text query
  — If images attached:
      • OpenAI / Groq: multimodal content array [text, image_url parts] (native vision)
      • Ollama: pre-caption text injected into system context
```

#### Step D: LLM Generation

**Provider selection** (tried in order, falls through on failure):

1. **OpenAI** (`gpt-4o-2024-11-20`) — if `OPENAI_API_KEY` set
2. **Groq** (`llama-3.3-70b-versatile`) — if `GROQ_API_KEY` set
3. **Ollama** (`qwen2.5:3b`) — local fallback, always available

**OpenAI mode** (`_generate_openai`):
- Uses OpenAI `/v1/chat/completions` API
- Native multimodal: images sent as base64 `image_url` parts in the content array
- Streams tokens via SSE
- Model: `gpt-4o-2024-11-20` (latest vision-capable, fast, high quality)
- Max tokens: 4096, Temperature: 0.3

**Groq mode** (`_generate_groq`):
- Same OpenAI-compatible format
- Model: `llama-3.3-70b-versatile` (fast, vision-capable)
- Used as fallback when OpenAI is unavailable

**Ollama mode** (`_generate_ollama`):
- Uses `/api/generate` endpoint
- For images: **pre-captioning approach** (not direct vision streaming):
  1. Save image to temp file
  2. Run Tesseract OCR (`--psm 6 --oem 3`) for text extraction
  3. Call `llava-phi3:3.8b` non-streaming with `num_predict: 80` for brief visual description
  4. Inject both OCR text + vision description into the system prompt as context
  5. `qwen2.5:3b` generates the response using that context

**Streaming response format (SSE):**

```
data: {"type": "token", "content": "partial text..."}
data: {"type": "done", "conversation_id": "...", "citations": [...]}
data: {"type": "error", "content": "error message"}
```

#### Step E: Save to Database

- User message saved immediately when request starts
- Full assistant message + cited chunk IDs saved after generation completes
- New conversations created on first message

### 4. Frontend Rendering

**Message display** (`ChatInterface.tsx`):

| Element | User | Assistant |
|---------|------|-----------|
| Alignment | Right | Left |
| Bubble | Dark (`#111827`), rounded | White, border, shadow |
| Avatar | Gray circle with user icon | Indigo-purple gradient with bot icon |
| Content | Plain text | Markdown (react-markdown + GFM) |
| Images | Thumbnail grid (80×80) above text | — |
| Citations | — | Source chips with file name + relevance % |
| TTS | — | Listen button → OpenAI TTS → Kokoro → edge-tts |

**Welcome Screen** (`WelcomeScreen.tsx`):
- Centered logo + app name
- 4 suggestion prompt buttons (grid layout)

**Chat Input** (`ChatInput.tsx`):
- Auto-resizing textarea
- `+` button → file picker (images, audio, PDF, documents)
- File preview chips above input (image thumbnails, file icons)
- Voice button → `MediaRecorder` → `/api/transcribe` → fill input
- Send button (dark, activates only with content)
- Drag-and-drop: files can be dropped directly on the input area (20MB max)

**Sidebar** (`Sidebar.tsx`):
- Dark panel (`#171717`), collapsible
- "New chat" button at top
- Conversation list with title + date + delete button
- Active conversation highlighted
- KB name shown at bottom

**Document Panel** (`DocumentPanel.tsx`):
- Slides in from right on "Documents" header button
- Contains FileUpload (drag-drop zone) + DocumentList (status badges, delete)
- Closes on Escape key

---

## File Reference

### Backend (`backend/app/`)

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app setup, CORS, router registration |
| `config.py` | Pydantic settings from `.env` (all configurable) |
| `schemas.py` | Pydantic models for request/response (ChatRequest, etc.) |
| `models.py` | SQLAlchemy ORM models (KB, Document, Chunk, Conversation, Message) |
| `database.py` | Async SQLAlchemy engine + session with pgvector |
| `routers/chat.py` | Chat streaming endpoint, conversation list/messages |
| `routers/documents.py` | Document upload, list, delete |
| `routers/kb.py` | Knowledge base CRUD |
| `routers/audio.py` | Audio transcription endpoint |
| `routers/tts.py` | Text-to-speech endpoint |
| `routers/health.py` | Health check endpoint |
| `services/generation.py` | `build_messages()`, `_caption_image()`, `_generate_groq()`, `_generate_ollama()` |
| `services/retrieval.py` | pgvector similarity search with threshold filter |
| `services/embedding.py` | Embedding generation, `ensure_models()` startup |
| `services/extraction.py` | PDF, image, audio extraction pipeline |
| `services/web_search.py` | DuckDuckGo + crawl4ai + Wikipedia chain |
| `services/tts.py` | OpenAI TTS, Kokoro, edge-tts providers |
| `services/chunking.py` | Text chunking with overlap |

### Frontend (`frontend/`)

| File | Purpose |
|------|---------|
| `app/page.tsx` | Home page — KB list, create/delete |
| `app/kb/[kbId]/page.tsx` | KB page — sidebar + chat + document panel layout |
| `app/layout.tsx` | Root layout |
| `app/globals.css` | Tailwind + ChatGPT-like theme + markdown styles + animations |
| `components/ChatInterface.tsx` | Message list, streaming, TTS, `ChatMessage` sub-component |
| `components/ChatInput.tsx` | Textarea, file upload, voice, drag-drop, file previews |
| `components/Sidebar.tsx` | Conversation history sidebar |
| `components/WelcomeScreen.tsx` | Empty state with suggestion prompts |
| `components/DocumentPanel.tsx` | Slide-out document management |
| `components/FileUpload.tsx` | Drag-drop zone with `react-dropzone` |
| `components/DocumentList.tsx` | Document list with status badges + icons |
| `types/index.ts` | TypeScript interfaces |
| `lib/api.ts` | API client + `fileToBase64()` utility |

---

## Configuration

All settings via `.env` (loaded by `config.py`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://inquix:inquix@db:5432/inquix` | PostgreSQL connection |
| `OLLAMA_URL` | `http://ollama:11434` | Ollama service URL |
| `LLM_PROVIDER` | `ollama` | `groq` or `ollama` |
| `LLM_MODEL` | `qwen2.5:3b` | Text generation model |
| `OPENAI_API_KEY` | — | OpenAI API key (primary for all services) |
| `OPENAI_LLM_MODEL` | `gpt-4o-2024-11-20` | OpenAI LLM model |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `OPENAI_TTS_MODEL` | `tts-1-hd` | OpenAI TTS model |
| `OPENAI_TTS_VOICE` | `alloy` | OpenAI TTS voice |
| `OPENAI_WHISPER_MODEL` | `whisper-1` | OpenAI transcription model |
| `GROQ_API_KEY` | — | Groq cloud API key (fallback) |
| `VISION_MODEL` | `llava-phi3:3.8b` | Ollama vision model (fallback) |
| `EMBED_PROVIDER` | `ollama` | Embedding provider |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Ollama embedding model (fallback) |
| `JINA_API_KEY` | — | Jina AI embedding key (fallback) |
| `TOP_K` | `5` | Number of chunks to retrieve |
| `SIMILARITY_THRESHOLD` | `0.45` | Minimum chunk relevance |
| `CHUNK_SIZE` | `500` | Chunk token size |
| `CHUNK_OVERLAP` | `50` | Chunk overlap token count |
| `TTS_PROVIDER` | `kokoro` | `kokoro` or `edge-tts` |
| `TTS_VOICE` | `af_heart` | TTS voice identifier |

---

## Key Design Decisions

### Why pre-captioning instead of direct vision streaming (Ollama)?

`llava-phi3:3.8b` on CPU is slow (30-60s per image for streaming). Instead:
1. **Tesseract OCR** extracts text (fast, <1s)
2. **Vision model** generates a short description non-streaming (80 tokens, ~10-15s)
3. Both injected as text context into the fast `qwen2.5:3b` model for the streaming response

This gives accurate text extraction (OCR) + visual understanding (vision model) + fast streaming response (text model).

### Why sequential retrieval (docs first, web second)?

If document chunks are relevant (above `0.45` threshold), web search is skipped entirely. This keeps responses grounded in the user's uploaded data. Web search only fires when no document chunk is relevant enough.

### Why OpenAI + Groq + Ollama (triple fallback)?

**OpenAI** (`gpt-4o`) is the primary LLM — fastest, most capable, native vision. If OpenAI fails (network, rate limit), **Groq** (`llama-3.3-70b-versatile`) serves as a fast cloud fallback. If both cloud providers are unavailable, **Ollama** (`qwen2.5:3b`) runs fully offline on CPU. This ensures the app keeps working even without internet access.

### Why `--psm 6` for Tesseract?

Page Segmentation Mode 6 ("Assume a single uniform block of text") works best for receipts, signs, and documents where text is in a single column/block. Combined with OEM 3 (default LSTM engine) for best accuracy.
