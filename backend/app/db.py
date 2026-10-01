import sqlite3
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ZIP_FILE = ROOT / "rag" / "all_tickets_processed_improved_v3.csv.zip"
CSV_NAME = "all_tickets_processed_improved_v3.csv"
SQL_SCRIPT = ROOT / "rag" / "rag.sql"
DB_FILE = Path(__file__).resolve().parents[1] / "it_tickets.db"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Build the SQLite database from the zipped CSV on first run."""
    if DB_FILE.exists():
        return

    print(f"Building {DB_FILE.name} from {ZIP_FILE.name}...")
    with zipfile.ZipFile(ZIP_FILE) as zf, zf.open(CSV_NAME) as f:
        df = pd.read_csv(f)
    df = df.dropna(subset=["Document", "Topic_group"])

    conn = connect()
    conn.executescript(SQL_SCRIPT.read_text())
    conn.executemany(
        "INSERT INTO support_tickets (category, issue_description) VALUES (?, ?)",
        df[["Topic_group", "Document"]].itertuples(index=False, name=None),
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON support_tickets(category)")
    conn.commit()
    conn.close()
    print(f"Loaded {len(df)} tickets.")


def _where(q: Optional[str], category: Optional[str]) -> Tuple[str, list]:
    clauses, params = [], []
    if q:
        clauses.append("issue_description LIKE ?")
        params.append(f"%{q}%")
    if category:
        clauses.append("category = ?")
        params.append(category)
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def search_tickets(
    q: Optional[str], category: Optional[str], limit: int, offset: int
) -> Tuple[int, List[dict]]:
    where, params = _where(q, category)
    with connect() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM support_tickets{where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT id, category, issue_description FROM support_tickets{where} "
            "ORDER BY id LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
    return total, [dict(r) for r in rows]


def get_ticket(ticket_id: int) -> Optional[dict]:
    with connect() as conn:
        row = conn.execute(
            "SELECT id, category, issue_description FROM support_tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()
    return dict(row) if row else None


def category_counts() -> List[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT category, COUNT(*) AS count FROM support_tickets "
            "GROUP BY category ORDER BY count DESC"
        ).fetchall()
    return [dict(r) for r in rows]
