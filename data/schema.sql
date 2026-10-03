-- Supabase (Postgres) schema. Applied automatically by `python -m app.ingest`,
-- or paste it into Supabase -> SQL Editor.

-- pgvector adds the `vector` column type and similarity operators
create extension if not exists vector;

create table if not exists support_tickets (
    id                bigint primary key,
    category          text   not null,
    issue_description text   not null,
    -- 384 numbers from all-MiniLM-L6-v2; null until the ticket is embedded
    embedding         vector(384)
);

-- Fast category filter for the Browse page
create index if not exists support_tickets_category_idx
    on support_tickets (category);

-- HNSW index makes nearest-neighbour search by cosine distance (<=>) fast
create index if not exists support_tickets_embedding_idx
    on support_tickets using hnsw (embedding vector_cosine_ops);
