import os
from pathlib import Path
# Load environment variables from .env file
from dotenv import load_dotenv

# Load .env file from the backend directory
# 2 because this config.py is in backend/app, and .env is in backend/ therefore this becomes project root if 2
PROJECT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_DIR / "backend" / ".env")

# Database connection string for Supabase Postgres
DATABASE_URL = os.getenv("DATABASE_URL")


# Data files
TICKETS_ZIP = PROJECT_DIR / "data" / "it_support_tickets.csv.zip"
TICKETS_CSV_NAME = "all_tickets_processed_improved_v3.csv" 
SCHEMA_SQL = PROJECT_DIR / "data" / "schema.sql"
FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"

# RAG settings
CLAUDE_MODEL = "claude-opus-5-5"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 384 numbers per text, runs locally
TOP_K = 5  # how many similar tickets to retrieve
MIN_RELEVANCE = 0.3  # tickets less similar than this (0-1) never reach Claude
