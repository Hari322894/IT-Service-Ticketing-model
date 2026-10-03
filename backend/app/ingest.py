"""One-time data load: CSV -> Supabase, then compute each ticket's embedding.

Run from backend/:  python -m app.ingest

Safe to re-run: it skips the upload if tickets already exist and only embeds
tickets that don't have an embedding yet, so an interrupted run continues.
"""
import time
import zipfile

import pandas as pd

from . import config, database, rag


def main():
    db = database.connect()
    with db.connection() as conn:
        # 1. Create the table and indexes
        conn.execute(config.SCHEMA_SQL.read_text())
        conn.commit()

        # 2. Upload the tickets (skipped if already done)
        if conn.execute("SELECT COUNT(*) AS n FROM support_tickets").fetchone()["n"] == 0:
            with zipfile.ZipFile(config.TICKETS_ZIP) as zf, zf.open(config.TICKETS_CSV_NAME) as f:
                df = pd.read_csv(f)
            df = df.dropna(subset=["Document", "Topic_group"]).reset_index(drop=True)
            df["id"] = df.index + 1

            print(f"Uploading {len(df)} tickets...")
            # COPY sends all rows in one go: much faster than one INSERT per ticket
            with conn.cursor().copy("COPY support_tickets (id, category, issue_description) FROM STDIN") as copy:
                for row in df[["id", "Topic_group", "Document"]].itertuples(index=False, name=None):
                    copy.write_row(row)
            conn.commit()

        # 3. Embed every ticket that doesn't have an embedding yet
        todo = conn.execute(
            "SELECT id, category, issue_description FROM support_tickets WHERE embedding IS NULL ORDER BY id"
        ).fetchall()
        print(f"Embedding {len(todo)} tickets (about 20 seconds per 1,000)...")
        start = time.time()
        for i in range(0, len(todo), 256):
            batch = todo[i : i + 256]
            embeddings = rag.embed([rag.ticket_text(t) for t in batch])
            conn.cursor().executemany(
                "UPDATE support_tickets SET embedding = %s WHERE id = %s",
                [(e, t["id"]) for e, t in zip(embeddings, batch)],
            )
            conn.commit()  # save progress after every batch
            print(f"  {i + len(batch)}/{len(todo)} ({time.time() - start:.0f}s)")

    print("Ingest complete.")


if __name__ == "__main__":
    try:
        main()
    except database.DatabaseError as e:
        raise SystemExit(f"Error: {e}")
