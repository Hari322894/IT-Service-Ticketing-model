 # Enterprise IT Service RAG Model

An enterprise-grade **Retrieval-Augmented Generation (RAG)** pipeline designed to ingest, process, and audit massive technical incident data streams. The system automates corporate infrastructure audits by converting **40,000+ raw, unstructured tech-support records** into structured relational tables and semantic vectors, using strict context validation gates to eliminate Large Language Model (LLM) hallucinations.

---

## Business Problem & Core Objectives
Enterprise IT departments struggle to surface actionable insights from years of messy, high-volume ticketing logs. Manual technical audits are time-consuming, prone to oversight, and cost thousands of engineering hours. 

This project solves that bottleneck by providing:
1. **Automated Structured Ingestion:** Normalizing 40K+ messy technical support records into structured SQL entities.
2. **Context-Aware Analytics:** Using cutting-edge LLMs to instantly identify structural infrastructure vulnerabilities and recurring system incident trends.
3. **Rigorous Context Governance:** Enforcing definitive input/output validation boundaries to guarantee that automated audit decisions are derived *only* from verified organizational data.

---

## 🛠️ Tech Stack & System Architecture

* **Backend Orchestration:** `Python`, `LangChain`
* **Data Manipulation & Ingestion:** `Pandas`
* **Relational Storage:** `MySQL` (Structured operational data & incident fields)
* **Vector Embeddings Storage:** `ChromaDB` (High-dimensional semantic indices)
* **Language Model Intelligence:** OpenAI `GPT-4o-mini` API

![alt text](RagModelidea.png)

```text
                           [ 40K+ Records ]
                                  │
                                  ▼ (Pandas ETL Pipeline)
                          [ MySQL Database ]
                         ╱                ╲
 (Relational Extraction)╱                  ╲ (Semantic Text Chunking)
                       ▼                    ▼
               [ LangChain ] ──────► [ ChromaDB Vector Store ]
                       │                    │
                       ├────────────────────┤
                       ▼                    ▼
            [ Input Validation Gate / Context Bounds ]
                       │
                       ▼
               [ OpenAI GPT-4o-mini ]
                       │
                       ▼
         [ Verified Audit Reports / Analytics ]


---

## 🌐 Web App: IT Ticket Explorer

A full-stack site with two tabs:

* **Ask:** ask questions about the ticket history. The RAG pipeline retrieves the most similar tickets from ChromaDB and drops any that score below a relevance threshold (the validation gate). Claude (`claude-opus-5-5`) answers using only the tickets that pass, and the site shows those tickets as clickable sources.
* **Browse:** search and filter all tickets by category.

* **Backend:** `FastAPI` + `SQLite` + `ChromaDB` + Anthropic `Claude` (`backend/`). Embeddings are computed locally with Chroma's built-in `all-MiniLM-L6-v2` model, so retrieval needs no API key. Only answer generation calls Claude.
* **Frontend:** `React` + `TypeScript` + `Vite` (`frontend/`). In production the backend serves the built frontend, so the whole site is a single service.
* **Cost guard:** `/api/ask` is rate-limited per visitor (`ASK_PER_MINUTE`, default 5) and globally per day (`ASK_PER_DAY`, default 300).

### Deploy to Render

1. Push the repo to GitHub.
2. In Render, choose **New → Blueprint** and select the repo. Render reads `render.yaml` and builds the `Dockerfile`.
3. When prompted, paste your `ANTHROPIC_API_KEY`.
4. The site goes live at `https://it-ticket-explorer.onrender.com` (or a similar URL). Every push to `main` redeploys it.

The Docker build embeds the first `RAG_MAX_TICKETS` (default 3000) tickets into the image, so the server starts ready.

### Run locally

```bash
To run the webstie first I did this, I will implement a backend api later
# Terminal 1: API on http://localhost:8000 (docs at /docs)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2: website on http://localhost:5173
cd frontend
npm install
npm run dev
```

### API

| Endpoint | Description |
| --- | --- |
| `GET /api/categories` | Ticket counts per category |
| `GET /api/tickets?q=&category=&limit=&offset=` | Search and filter tickets (paginated) |
| `GET /api/tickets/{id}` | A single ticket |
| `POST /api/ask` `{"question": "..."}` | RAG answer plus source tickets |
