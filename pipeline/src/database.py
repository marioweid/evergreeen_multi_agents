"""
Evergreen Multi Agents - Database Layer

Handles PostgreSQL with pgvector for both customer data and roadmap vector embeddings.
Uses Google's Gemini embedding API for generating embeddings.
"""

from typing import Optional

import google.genai as genai
from google.genai.types import EmbedContentConfig, EmbedContentResponse
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel

from bootstrap import get_db_connection


class RoadmapItem(BaseModel):
    """Roadmap item model from M365 API."""

    id: int
    title: str
    description: str
    status: str
    public_disclosure_date: Optional[str] = None
    products: list[str] = []
    platforms: list[str] = []
    cloud_instances: list[str] = []
    release_phase: Optional[str] = None


def init_db(database_url: str, embedding_dimensions: int) -> None:
    """Initialize the PostgreSQL database with required tables and extensions."""
    conn = get_db_connection(database_url=database_url)
    cursor = conn.cursor()

    # Enable pgvector extension
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create customers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            products_used TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create roadmap items table with vector embeddings
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS roadmap_items (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT,
            release_date TEXT,
            products TEXT,
            platforms TEXT,
            cloud_instances TEXT,
            release_phase TEXT,
            document TEXT NOT NULL,
            embedding vector({embedding_dimensions}),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def get_embedding(
    text: str,
    genai_client: genai.Client,
    embedding_model: str,
    embedding_dimensions: int,
) -> list[float]:
    """Generate embedding using Gemini's embedding API."""
    result: EmbedContentResponse = genai_client.models.embed_content(
        model=embedding_model,
        contents=[text],
        task_type="retrieval_document",
        config=EmbedContentConfig(output_dimensionality=embedding_dimensions),
    )
    embeddings = result.embeddings[0]  # since input is single str
    return embeddings


def get_query_embedding(
    text: str,
    genai_client: genai.Client,
    embedding_model: str,
    embedding_dimensions: int,
) -> list[float]:
    """Generate embedding for a search query."""
    result: EmbedContentResponse = genai_client.models.embed_content(
        model=embedding_model,
        contents=[text],
        task_type="retrieval_query",
        config=EmbedContentConfig(output_dimensionality=embedding_dimensions),
    )
    embeddings = result.embeddings[0]  # since input is single str
    return embeddings


# Roadmap Vector Operations
def upsert_roadmap_items(
    items: list[RoadmapItem],
    database_url: str,
    genai_client: genai.Client,
    embedding_model: str,
    embedding_dimensions: int,
) -> int:
    """Upsert roadmap items into PostgreSQL with embeddings."""
    conn = get_db_connection(database_url=database_url)
    cursor = conn.cursor()

    count = 0
    for item in items:
        document = (
            f"{item.title}\n\n{item.description}\n\nStatus: {item.status}\n"
            f"Products: {', '.join(item.products)}\n"
            f"Platforms: {', '.join(item.platforms)}"
        )

        # Generate embedding for this document
        embedding = get_embedding(
            text=document, genai_client=genai_client, embedding_model=embedding_model, embedding_dimensions=embedding_dimensions
        )

        cursor.execute(
            """
            INSERT INTO roadmap_items 
                (id, title, description, status, release_date, products, 
                 platforms, cloud_instances, release_phase, document, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                status = EXCLUDED.status,
                release_date = EXCLUDED.release_date,
                products = EXCLUDED.products,
                platforms = EXCLUDED.platforms,
                cloud_instances = EXCLUDED.cloud_instances,
                release_phase = EXCLUDED.release_phase,
                document = EXCLUDED.document,
                embedding = EXCLUDED.embedding,
                updated_at = CURRENT_TIMESTAMP
        """,
            (
                item.id,
                item.title,
                item.description,
                item.status,
                item.public_disclosure_date,
                ",".join(item.products),
                ",".join(item.platforms),
                ",".join(item.cloud_instances),
                item.release_phase,
                document,
                embedding,
            ),
        )
        count += 1

    conn.commit()
    conn.close()
    return count


def search_roadmap(
    query: str,
    genai_client: genai.Client,
    embedding_model: str,
    database_url: str,
    n_results: int = 5,
    filter_products: Optional[list[str]] = None,
) -> list[dict]:
    """Search the roadmap using vector similarity (cosine distance)."""
    conn = get_db_connection(database_url=database_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Generate query embedding
    query_embedding = get_query_embedding(
        text=query, genai_client=genai_client, embedding_model=embedding_model
    )

    # Build query with optional product filter
    if filter_products:
        product_filter = " OR ".join(["products ILIKE %s" for _ in filter_products])
        cursor.execute(
            f"""
            SELECT *, embedding <=> %s::vector AS distance
            FROM roadmap_items
            WHERE ({product_filter})
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """,
            [query_embedding]
            + [f"%{p}%" for p in filter_products]
            + [query_embedding, n_results],
        )
    else:
        cursor.execute(
            """
            SELECT *, embedding <=> %s::vector AS distance
            FROM roadmap_items
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """,
            (query_embedding, query_embedding, n_results),
        )

    rows = cursor.fetchall()
    conn.close()

    items = []
    for row in rows:
        items.append(
            {
                "document": row["document"],
                "metadata": {
                    "id": row["id"],
                    "title": row["title"],
                    "status": row["status"],
                    "release_date": row["release_date"] or "",
                    "products": row["products"] or "",
                    "platforms": row["platforms"] or "",
                },
                "distance": row["distance"],
            }
        )

    return items


def get_roadmap_stats(database_url:str) -> dict:
    """Get statistics about the roadmap table."""
    conn = get_db_connection(database_url=database_url)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM roadmap_items")
    count = cursor.fetchone()[0]
    conn.close()

    return {"total_items": count}
