from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import db, rag


class Ticket(BaseModel):
    id: int
    category: str
    issue_description: str


class TicketPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[Ticket]


class CategoryCount(BaseModel):
    category: str
    count: int


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class Source(BaseModel):
    id: int
    category: str
    score: float


class AskResponse(BaseModel):
    answer: str
    sources: List[Source]


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="IT Ticket Explorer API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/categories", response_model=List[CategoryCount])
def categories():
    return db.category_counts()


@app.get("/api/tickets", response_model=TicketPage)
def tickets(
    q: Optional[str] = Query(None, max_length=200),
    category: Optional[str] = None,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    total, items = db.search_tickets(q, category, limit, offset)
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@app.get("/api/tickets/{ticket_id}", response_model=Ticket)
def ticket(ticket_id: int):
    found = db.get_ticket(ticket_id)
    if not found:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return found


@app.post("/api/ask", response_model=AskResponse)
def ask(body: AskRequest):
    try:
        return rag.ask(body.question)
    except rag.NotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e))
