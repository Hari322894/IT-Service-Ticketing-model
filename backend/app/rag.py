#The RAG pipeline: Retrieve -> Validate -> Generate.
import anthropic
from fastembed import TextEmbedding

from . import config, database

NO_MATCH = "Please ask another question that relates to the tickets."

SYSTEM_PROMPT = (
    "You are an expert corporate IT Systems Infrastructure Analyst.\n"
    "Answer the user's question using ONLY the historical incident logs inside <tickets>. "
    "Identify overlapping technical problems, common failure modes, or patterns, "
    "and cite tickets by their id like [#123]. The logs are preprocessed text with stop words "
    "removed, so read them for meaning rather than grammar. "
    "Write plain text for a chat window: short paragraphs or simple '-' bullet points, "
    "with no Markdown headings, bold, or tables. "
    f"If the logs do not answer the question, reply exactly: '{NO_MATCH}'"
)

_embedder = None
_claude = None


def embed(texts):
    """Turn texts into embeddings (384 numbers each) with a local model. Free, no API key."""
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedding(config.EMBEDDING_MODEL)  # downloads ~90 MB on first use
    return list(_embedder.embed(texts))


def ticket_text(ticket):
    """The text that represents a ticket, both when embedding it and when showing it to Claude."""
    return f"Department: {ticket['category']} | Log: {ticket['issue_description']}"


def answer_question(question):
    global _claude

    # 1. Retrieve
    [question_embedding] = embed([question])
    tickets = database.find_similar(question_embedding, config.TOP_K)

    # 2. Validate
    tickets = [t for t in tickets if t["score"] >= config.MIN_RELEVANCE]
    if not tickets:
        return {"answer": NO_MATCH, "sources": []}

    # 3. Generate
    context = "\n\n".join(f"[#{t['id']}] {ticket_text(t)}" for t in tickets)
    if _claude is None:
        _claude = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    response = _claude.beta.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"<tickets>\n{context}\n</tickets>\n\nQuestion: {question}"}],
        # If Claude declines a question, Anthropic retries it on a fallback model
        betas=["server-side-fallback-2026-07-01"],
        extra_body={"fallbacks": "default", "output_config": {"effort": "medium"}},
    )

    if response.stop_reason == "refusal":
        answer = "Claude declined to answer this question."
    else:
        answer = "".join(block.text for block in response.content if block.type == "text").strip()

    sources = [{"id": t["id"], "category": t["category"], "score": round(t["score"], 3)} for t in tickets]
    return {"answer": answer or NO_MATCH, "sources": sources}
