import psycopg2
from psycopg2 import extensions
import google.genai as genai
from pgvector.psycopg2 import register_vector


def get_db_connection(database_url: str) -> extensions.connection:
    """Get a connection to the PostgreSQL database."""
    conn = psycopg2.connect(database_url)
    register_vector(conn)
    return conn


def get_genai_client(api_key: str) -> genai.Client:
    """Configure Gemini API for embeddings."""
    if not api_key:
        print("ERROR: GOOGLE_API_KEY or GEMINI_API_KEY environment variable required")
        raise ValueError("API key not found")
    return genai.Client(api_key=api_key)
