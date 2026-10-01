import os
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Deque, Dict, List, Optional

import anthropic
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db, rag

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

# The site is public and every question costs Anthropic credit, so cap usage.
ASK_PER_MINUTE = int(os.getenv("ASK_PER_MINUTE", "5"))
ASK_PER_DAY = int(os.getenv("ASK_PER_DAY", "300"))


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


class RateLimiter:
    """In-memory limits: per client IP per minute, plus a global daily total."""

    def __init__(self, per_minute: int, per_day: int):
        self.per_minute = per_minute
        self.per_day = per_day
        self.recent: Dict[str, Deque[float]] = defaultdict(deque)
        self.day = time.strftime("%Y-%m-%d")
        self.day_count = 0
        self.lock = threading.Lock()

    def check(self, ip: str) -> None:
        now = time.time()
        with self.lock:
            today = time.strftime("%Y-%m-%d")
            if today != self.day:
                self.day, self.day_count = today, 0
                self.recent.clear()
            if self.day_count >= self.per_day:
                raise HTTPException(429, "Daily question limit reached. Try again tomorrow.")
            hits = self.recent[ip]
            while hits and now - hits[0] > 60:
                hits.popleft()
            if len(hits) >= self.per_minute:
                raise HTTPException(429, "Too many questions. Wait a minute and try again.")
            hits.append(now)
            self.day_count += 1


limiter = RateLimiter(ASK_PER_MINUTE, ASK_PER_DAY)


def client_ip(request: Request) -> str:
    # Render (and most hosts) put the real client IP first in X-Forwarded-For
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="IT Ticket Explorer API", lifespan=lifespan)
# Only needed when the Vite dev server runs on a different port
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
def ask(body: AskRequest, request: Request):
    limiter.check(client_ip(request))
    try:
        return rag.ask(body.question)
    except rag.NotConfigured as e:
        raise HTTPException(503, str(e))
    except anthropic.AuthenticationError:
        raise HTTPException(503, "The server's Anthropic API key is invalid.")
    except anthropic.RateLimitError:
        raise HTTPException(429, "The AI service is busy. Try again in a moment.")
    except (anthropic.APIStatusError, anthropic.APIConnectionError):
        raise HTTPException(502, "The AI service is unavailable right now. Try again later.")


# Serve the built React app (frontend/dist) from the same server in production
if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        file = (FRONTEND_DIST / path).resolve()
        if path and file.is_file() and FRONTEND_DIST.resolve() in file.parents:
            return FileResponse(file)
        return FileResponse(FRONTEND_DIST / "index.html")
