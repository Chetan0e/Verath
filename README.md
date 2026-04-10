# 🧠 SecondBrain
### Augmented Human Intelligence & Personal Knowledge Ecosystem

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Ollama](https://img.shields.io/badge/LLM-Ollama-blue.svg)](https://ollama.ai/)
[![Whisper](https://img.shields.io/badge/STT-Whisper-black.svg)](https://github.com/openai/whisper)
[![React Native](https://img.shields.io/badge/Mobile-React%20Native-61DAFB.svg?style=flat&logo=react&logoColor=white)](https://reactnative.dev/)

**SecondBrain** is an advanced, high-performance personal memory system designed to record, transcribe, and intelligently index every aspect of your daily life. It uses local AI to provide a searchable "cognitive ledger" that allows you to recall conversations, generate daily summaries, and query your own experiences with natural language.


---

## 🚀 Strategic Deployment & Setup

### 1. Neural Engine Initialization
SecondBrain requires [Ollama](https://ollama.ai/) for local LLM and embedding inference.
```bash
# Pull essential model weights
ollama pull mistral
ollama pull nomic-embed-text
```

### 2. Environment Configuration
Initialize your local environment variables:
```bash
cp .env.example .env
```
*Modify `.env` to point to your Ollama instance and preferred model thresholds.*

### 3. Backend Orchestration
It is recommended to use a virtual environment for the Python backend:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

### 4. Background Acoustic Listener
To enable always-on memory capture, start the listener in a dedicated process:
```bash
cd backend
python run_listener.py
```

### 5. Mobile & Web Access
*   **Mobile (Expo)**: `cd mobile && npm install && npx expo start`
*   **Web Console**: Accessible via `http://localhost:8000/web/index.html` once the backend is running.

---

## 🏗️ Project Architecture & Hierarchy

The system follows a three-tier architecture (Mobile/Web Client, FastAPI Server, AI In-Process Pipelines) with a "Local-First" data sovereignty model.

```
secondbrain/
├── backend/                  # Orchestration Layer (Python)
│   ├── app/                  # Core Application Logic
│   │   ├── models/           # Pydantic data schemas & Database models
│   │   ├── routes/           # Domain-specific REST Controllers
│   │   ├── services/         # Granular business logic modules
│   │   ├── utils/            # Specialized helpers (Formatting, Time, IO)
│   │   └── config.py         # Global configuration engine
│   ├── run.py                # Main Web Server entry point
│   └── run_listener.py       # Background recording process entry point
├── mobile/                   # User Interface - Mobile (React Native/Expo)
│   ├── screens/              # View components (Home, Ask, Timeline)
│   ├── components/           # Reusable Atomic UI units
│   └── services/              # Logic for calling the Backend APIs
├── web/                      # Monitoring Dashboard (FastAPI-served)
│   ├── index.html            # Real-time monitoring entry
│   └── app.js                # Stats visualization logic
├── data/                     # Persistent Storage
│   ├── vector_db/            # FAISS indices
│   └── recordings/           # Temporary raw audio chunks (Auto-purged)
└── docker-compose.yml        # Orchestration for containerized deployments
```

---

## 🛠️ Comprehensive Library Rationale

| Library | Role in System | Rationale |
| :--- | :--- | :--- |
| **FastAPI** | High-performance Web Engine | Asynchronous request handling allows for non-blocking I/O during heavy LLM inference. |
| **FAISS** | Neural Vector Indexing | Provided by Meta, it allows for O(log n) similarity searches across millions of memory vectors. |
| **Faster-Whisper** | STT Inference | Optimized Whisper implementation that runs up to 4x faster with lower memory overhead. |
| **Ollama** | Local LLM Orchestration | Standardized interface for running Mistral, Llama, and embedding models without cloud dependency. |
| **Pyannote.audio** | Speaker Diarization | State-of-the-art speaker recognition to categorize "who said what" in multi-person meetings. |
| **Motor (MongoDB)** | Metadata Storage | Asynchronous driver for storing non-vector metadata (timestamps, speakers, importance scores). |
| **React Native** | Cross-Platform UI | Unified codebase for iOS/Android ensuring consistent memory access on the go. |

---

## ⚙️ Detailed Module Breakdown

### 🐍 Backend Services (`backend/app/services/`)
*   **`pipeline.py`**: The "Central Nervous System." Orchestrates the flow from Audio Input → Transcription → Embedding → Scoring → Storage.
*   **`audio.py`**: Handles PCM stream processing, silence trimming, and normalization.
*   **`transcription.py`**: Manages the life cycle of the `faster-whisper` model and yields text from audio buffers.
*   **`embedding.py`**: Converts text strings into high-dimensional vectors for semantic search.
*   **`importance.py`**: Uses a lightweight NLP pass to assign a score (0.0 - 1.0) to every memory for smart filtering.
*   **`memory_store.py`**: Low-level interface for the FAISS index and MongoDB metadata.
*   **`query_engine.py`**: The RAG implementation. Gathers context from the vector DB and feeds it to the LLM for grounded answers.
*   **`speaker.py`**: Manages voice profiles and diarization results.
*   **`summarizer.py`**: Leverages the LLM to distill thousands of words into concise daily/weekly summaries.
*   **`memory_graph.py`**: Extracts concepts and builds a graph of connections between related memories (Topic → Correlation).

### 📡 API Controllers (`backend/app/routes/`)
*   **`record.py`**: Endpoints for manual audio triggers and real-time processing status.
*   **`query.py`**: The main natural language interface for "Ask your Brain" functionality.
*   **`advanced.py`**: Endpoints for data-heavy operations like timeline generation and insight extraction.
*   **`auth.py`**: JWT-based security controllers for multiple user accounts.
*   **`privacy.py`**: Controls for hardware recording status and data erasure.

### 📱 Mobile Ecosystem (`mobile/screens/`)
*   **`HomeScreen.js`**: Real-time visualization of current memory recording and system health.
*   **`AskScreen.js`**: Chat interface powered by the RAG backend for querying the memory history.
*   **`TimelineScreen.js`**: Chronological feed of summarized events with importance-based highlighting.
*   **`SettingsScreen.js`**: Configuration for on-device storage, speaker profiles, and privacy rules.

---

## 🧠 The Memory Processing Lifecycle (Deep-Dive)

1.  **Ingestion**: `run_listener.py` monitors the hardware input. When silence is broken, it buffers audio.
2.  **Featurization**: `transcription.py` converts audio to text. Simultaneously, `speaker.py` identifies the speaker via voice fingerprinting.
3.  **Vectorization**: `embedding.py` maps the text to a vector space where similar meanings are geographically close.
4.  **Semantic Storage**: `memory_store.py` saves the vector to FAISS and metadata to MongoDB.
5.  **Intelligence Pass**: `importance.py` scores the memory. If it passes a threshold, it's flagged as an "Insight."
6.  **Retrieval (Query)**: When a user asks a question, the `query_engine.py` finds the closest vectors, builds a prompt context, and asks the local LLM to generate an answer.

---

## 🔧 Extended Configuration (`.env`)

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `OLLAMA_URL` | `http://localhost:11434` | Endpoint for LLM/Embedding inference. |
| `MODEL_NAME` | `mistral` | The primary reasoning model. |
| `EMBED_MODEL` | `nomic-embed-text` | Model used for vector generations. |
| `WHISPER_MODEL` | `base` | Accuracy vs Speed toggle (tiny, base, small, medium, large). |
| `DEFAULT_RECORD_SECONDS` | `10` | The lookahead duration for background silence detection. |
| `IMPORTANCE_THRESHOLD` | `0.4` | Minimum score required for a memory to appear in the "Key Insights" list. |


---

## 💾 Database & Persistence Layers

SecondBrain employs a hybrid persistence strategy to balance rapid semantic retrieval with relational metadata integrity.

| Storage Layer | Engine | Data Responsibility |
| :--- | :--- | :--- |
| **Vector DB** | FAISS | In-memory indexing of embeddings for $O(\log n)$ semantic similarity. |
| **Document DB** | MongoDB / Motor | Persistent storage of raw transcripts, speaker labels, time-offsets, and Importance Scores. |
| **Object Store**| File System | Temporary staging for raw `.wav` recordings and permanent storage for refined voice profiles. |

---

## 🛡️ Data Privacy & Compliance

SecondBrain is built on the principle of **Zero-Cloud Interdependency**.
*   **Local Inference**: No audio or text is sent to external APIs (OpenAI, Google) unless explicitly configured.
*   **In-Memory Buffering**: Raw audio is processed in memory and deleted after transcription by default.
*   **Encrypted Storage**: Metadata can be AES-encrypted before being committed to the database (see `security.md`).

---

*“Forgetfulness is no longer a biological constraint; it's a technical setting.”* 🚀
#   s e c o n d B r a i n  
 #   s e c o n d B r a i n  
 