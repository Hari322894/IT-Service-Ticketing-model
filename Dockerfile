# --- Stage 1: build the React frontend ---
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Python API that also serves the built frontend ---
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY rag/rag.sql rag/all_tickets_processed_improved_v3.csv.zip rag/
COPY backend/app backend/app
COPY --from=web /web/dist frontend/dist

# Build the SQLite DB and vector index into the image so the server starts fast.
# Embeddings run locally here, so no API key is needed at build time.
ARG RAG_MAX_TICKETS=3000
WORKDIR /app/backend
RUN RAG_MAX_TICKETS=${RAG_MAX_TICKETS} python -m app.rag

# Render sets $PORT; default to 8000 elsewhere
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
