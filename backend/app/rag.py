"""RAG pipeline: SQLite tickets -> Chroma vectors -> relevance gate -> GPT-4o-mini."""
import os
import threading
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from . import db

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

VECTOR_DB_DIR = BACKEND_DIR / "chroma_db"
COLLECTION = "it_tickets"
MAX_TICKETS = int(os.getenv("RAG_MAX_TICKETS", "2000"))
TOP_K = 5
# Tickets scoring below this relevance (0-1) are not trusted as context.
MIN_RELEVANCE = 0.35
NO_MATCH = "No matching technical records found."

SYSTEM_PROMPT = (
    "You are an expert corporate IT Systems Infrastructure Analyst.\n"
    "Answer the user's question using ONLY the historical incident logs below. "
    "Identify overlapping technical problems, common failure modes, or patterns, "
    "and cite tickets by their id like [#123]. "
    f"If the logs do not answer the question, reply exactly: '{NO_MATCH}'\n\n"
    "Historical Logs Context:\n{context}"
)

_store: Optional[Chroma] = None
_lock = threading.Lock()


class NotConfigured(RuntimeError):
    pass


def _check_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise NotConfigured("OPENAI_API_KEY is not set. Add it to backend/.env (see backend/.env.example).")


def get_store() -> Chroma:
    """Open the persisted vector store, embedding tickets on first use."""
    global _store
    with _lock:
        if _store is not None:
            return _store
        _check_key()
        store = Chroma(
            collection_name=COLLECTION,
            embedding_function=OpenAIEmbeddings(model="text-embedding-3-small"),
            persist_directory=str(VECTOR_DB_DIR),
            collection_metadata={"hnsw:space": "cosine"},
        )
        if not store.get(limit=1)["ids"]:
            db.init_db()
            _, rows = db.search_tickets(None, None, MAX_TICKETS, 0)
            print(f"Embedding {len(rows)} tickets into {VECTOR_DB_DIR.name}/ (one-time)...")
            docs = [
                Document(
                    # Truncate very long tickets so each one fits in a single embedding
                    page_content=f"Department: {r['category']} | Log: {r['issue_description'][:2000]}",
                    metadata={"ticket_id": r["id"], "category": r["category"]},
                )
                for r in rows
            ]
            ids = [str(r["id"]) for r in rows]
            for i in range(0, len(docs), 500):
                store.add_documents(docs[i : i + 500], ids=ids[i : i + 500])
            print("Vector store ready.")
        _store = store
        return _store


def ask(question: str) -> dict:
    store = get_store()
    hits = store.similarity_search_with_relevance_scores(question, k=TOP_K)

    # Validation gate: only well-matched tickets reach the LLM
    relevant = [(doc, score) for doc, score in hits if score >= MIN_RELEVANCE]
    if not relevant:
        return {"answer": NO_MATCH, "sources": []}

    context = "\n\n".join(f"[#{d.metadata['ticket_id']}] {d.page_content}" for d, _ in relevant)
    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", "{input}")])
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    answer = (prompt | llm).invoke({"context": context, "input": question}).content

    sources: List[dict] = [
        {
            "id": d.metadata["ticket_id"],
            "category": d.metadata["category"],
            "score": round(score, 3),
        }
        for d, score in relevant
    ]
    return {"answer": answer, "sources": sources}


if __name__ == "__main__":
    # Build the vector store ahead of time: python -m app.rag
    get_store()
