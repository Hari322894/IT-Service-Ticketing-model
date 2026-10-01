"""RAG pipeline: SQLite tickets -> Chroma vectors -> relevance gate -> Claude."""
import os
import threading
from pathlib import Path
from typing import List, Optional

import anthropic
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from dotenv import load_dotenv

from . import db

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

MODEL = "claude-opus-5-5"
VECTOR_DB_DIR = BACKEND_DIR / "chroma_db"
COLLECTION = "it_tickets"
MAX_TICKETS = int(os.getenv("RAG_MAX_TICKETS", "3000"))
TOP_K = 5
# Tickets scoring below this relevance (0-1) are not trusted as context.
MIN_RELEVANCE = 0.3
NO_MATCH = "No matching technical records found."

SYSTEM_PROMPT = (
    "You are an expert corporate IT Systems Infrastructure Analyst.\n"
    "Answer the user's question using ONLY the historical incident logs inside <tickets>. "
    "Identify overlapping technical problems, common failure modes, or patterns, "
    "and cite tickets by their id like [#123]. The logs are preprocessed text with stop words "
    "removed, so read them for meaning rather than grammar. "
    f"If the logs do not answer the question, reply exactly: '{NO_MATCH}'"
)

_collection = None
_client: Optional[anthropic.Anthropic] = None
_lock = threading.Lock()


class NotConfigured(RuntimeError):
    pass


def get_collection():
    """Open the persisted vector store, embedding tickets on first use.

    Embeddings run locally (all-MiniLM-L6-v2 via ONNX), so no API key is needed
    for retrieval; Anthropic does not offer an embeddings endpoint.
    """
    global _collection
    with _lock:
        if _collection is not None:
            return _collection
        client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
        col = client.get_or_create_collection(
            COLLECTION,
            embedding_function=DefaultEmbeddingFunction(),
            metadata={"hnsw:space": "cosine"},
        )
        if col.count() == 0:
            db.init_db()
            _, rows = db.search_tickets(None, None, MAX_TICKETS, 0)
            print(f"Embedding {len(rows)} tickets into {VECTOR_DB_DIR.name}/ (one-time)...")
            for i in range(0, len(rows), 500):
                batch = rows[i : i + 500]
                col.add(
                    ids=[str(r["id"]) for r in batch],
                    documents=[f"Department: {r['category']} | Log: {r['issue_description']}" for r in batch],
                    metadatas=[{"ticket_id": r["id"], "category": r["category"]} for r in batch],
                )
            print("Vector store ready.")
        _collection = col
        return _collection


def _claude() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise NotConfigured("ANTHROPIC_API_KEY is not set. Add it to backend/.env (see backend/.env.example).")
        # User-level keys (sk-ant-usr-...) must name a workspace on every request
        workspace = os.getenv("ANTHROPIC_WORKSPACE_ID")
        headers = {"anthropic-workspace-id": workspace} if workspace else None
        _client = anthropic.Anthropic(default_headers=headers)
    return _client


def ask(question: str) -> dict:
    # Over-fetch because the HNSW index can return the same ticket more than once
    res = get_collection().query(query_texts=[question], n_results=TOP_K * 2)

    # Validation gate: only well-matched tickets reach the LLM
    relevant, seen = [], set()
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        score = 1 - dist  # cosine distance -> similarity
        if score >= MIN_RELEVANCE and meta["ticket_id"] not in seen:
            seen.add(meta["ticket_id"])
            relevant.append((doc, meta, score))
    relevant = relevant[:TOP_K]
    if not relevant:
        return {"answer": NO_MATCH, "sources": []}

    context = "\n\n".join(f"[#{meta['ticket_id']}] {doc}" for doc, meta, _ in relevant)
    response = _claude().beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"<tickets>\n{context}\n</tickets>\n\nQuestion: {question}"}],
        # If Claude declines, the API retries on Anthropic's recommended fallback model
        betas=["server-side-fallback-2026-07-01"],
        extra_body={"fallbacks": "default", "output_config": {"effort": "medium"}},
    )

    if response.stop_reason == "refusal":
        answer = "Claude declined to answer this question."
    else:
        answer = "".join(b.text for b in response.content if b.type == "text").strip() or NO_MATCH

    sources: List[dict] = [
        {"id": meta["ticket_id"], "category": meta["category"], "score": round(score, 3)}
        for _, meta, score in relevant
    ]
    return {"answer": answer, "sources": sources}


if __name__ == "__main__":
    # Build the SQLite DB and vector store ahead of time: python -m app.rag
    db.init_db()
    get_collection()
