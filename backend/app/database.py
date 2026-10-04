#python library that speaks postgres and pgvector, with a connection pool
import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from . import config

_pool = None


class DatabaseError(RuntimeError):
    """DATABASE_URL is missing or Supabase rejected the connection."""


def _setup_connection(conn):
    # Teach psycopg the pgvector `vector` type (enabling the extension on a fresh database)
    if conn.execute("SELECT 1 FROM pg_type WHERE typname = 'vector'").fetchone() is None:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.commit()
    register_vector(conn)


def connect() -> ConnectionPool:
    
    global _pool
    if _pool is None:
        if not config.DATABASE_URL:
            raise DatabaseError("DATABASE_URL is not set. Add your Supabase connection string to backend/.env.")
        # Try one connection first: a wrong password then fails once with a clear message,
        # instead of the pool retrying until Supabase blocks logins.
        try:
            psycopg.connect(config.DATABASE_URL, connect_timeout=10).close()
        except psycopg.OperationalError as e:
            raise DatabaseError(f"Could not connect to Supabase: {str(e).splitlines()[0]}") from None
        _pool = ConnectionPool(
            config.DATABASE_URL,
            max_size=5,
            open=True,
            # Supabase's connection pooler doesn't support prepared statements
            kwargs={"row_factory": dict_row, "prepare_threshold": None},
            configure=_setup_connection,
        )
    return _pool


def run(sql, params=()):

    with connect().connection() as conn:
        return conn.execute(sql, params).fetchall()


# --- Browse page ---

def search_tickets(q, category, limit, offset):
    conditions, params = [], []
    if q:
        conditions.append("issue_description ILIKE %s")
        params.append(f"%{q}%")
    if category:
        conditions.append("category = %s")
        params.append(category)
    where = " WHERE " + " AND ".join(conditions) if conditions else ""

    total = run(f"SELECT COUNT(*) AS n FROM support_tickets{where}", params)[0]["n"]
    rows = run(
        f"SELECT id, category, issue_description FROM support_tickets{where} ORDER BY id LIMIT %s OFFSET %s",
        params + [limit, offset],
    )
    return total, rows


def get_ticket(ticket_id):
    rows = run("SELECT id, category, issue_description FROM support_tickets WHERE id = %s", (ticket_id,))
    return rows[0] if rows else None


def category_counts():
    return run("SELECT category, COUNT(*) AS count FROM support_tickets GROUP BY category ORDER BY count DESC")


# ask page given a ticket's embedding, find the k most similar tickets in the database

def find_similar(embedding, k):
    # k is the number of similar tickets to retrieve, and embedding is a list of floats (the ticket's vector embedding)
    # pgvector's <=> operator computes the cosine distance between two vectors, so 1
    # <=> is pgvector's cosine distance (0 = identical), so similarity = 1 - distance
    return run(
        "SELECT id, category, issue_description, 1 - (embedding <=> %s) AS score "
        "FROM support_tickets ORDER BY embedding <=> %s LIMIT %s",
        (embedding, embedding, k),
    )
