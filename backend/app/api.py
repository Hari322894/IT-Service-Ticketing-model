"""The web server: API endpoints, plus serving the built React website.

Run from backend/:  uvicorn app.api:app --port 8000
"""
import logging
from typing import List, Optional

import anthropic
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, database, rag

log = logging.getLogger("uvicorn.error")
app = FastAPI(title="IT Ticket Explorer API")


# --- Request and response shapes (FastAPI validates these automatically) ---

class Ticket(BaseModel):
    id: int
    category: str
    issue_description: str


class TicketPage(BaseModel):
    total: int
    items: List[Ticket]


class CategoryCount(BaseModel):
    category: str
    count: int


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class Source(BaseModel):
    id: int
    category: str
    score: float


class Answer(BaseModel):
    answer: str
    sources: List[Source]


# --- Endpoints ---

@app.get("/api/categories", response_model=List[CategoryCount])
def categories():
    return database.category_counts()


@app.get("/api/tickets", response_model=TicketPage)
def tickets(
    q: Optional[str] = Query(None, max_length=200),
    category: Optional[str] = None,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    total, items = database.search_tickets(q, category, limit, offset)
    return {"total": total, "items": items}


@app.get("/api/tickets/{ticket_id}", response_model=Ticket)
def ticket(ticket_id: int):
    found = database.get_ticket(ticket_id)
    if not found:
        raise HTTPException(404, "Ticket not found")
    return found


@app.post("/api/ask", response_model=Answer)
def ask(body: Question):
    try:
        return rag.answer_question(body.question)
    except anthropic.APIError as e:
        log.error("Anthropic API error: %s", e)  # full details in the terminal
        if "credit balance" in str(e):
            raise HTTPException(503, "The Anthropic account is out of API credits.")
        if isinstance(e, anthropic.AuthenticationError):
            raise HTTPException(503, "The Anthropic API key is invalid.")
        raise HTTPException(502, "The AI service had a problem. Check the server terminal for details.")


@app.exception_handler(database.DatabaseError)
def database_error(request: Request, e: database.DatabaseError):
    return JSONResponse(status_code=503, content={"detail": str(e)})


# --- The website (built with `npm run build` in frontend/) ---

if config.FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=config.FRONTEND_DIST / "assets"))

    @app.get("/{path:path}", include_in_schema=False)
    def website(path: str):
        file = (config.FRONTEND_DIST / path).resolve()
        if path and file.is_file() and config.FRONTEND_DIST.resolve() in file.parents:
            return FileResponse(file)  # e.g. favicon.svg
        return FileResponse(config.FRONTEND_DIST / "index.html")
