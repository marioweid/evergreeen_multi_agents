"""
Evergreen Multi Agents - Database Layer

Handles PostgreSQL with pgvector for both customer data and roadmap vector embeddings.
Uses Google's Gemini embedding API for generating embeddings.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel
from datetime import datetime
import google.genai as genai
from pgvector.psycopg2 import register_vector
from google.genai.types import EmbedContentConfig

# Database connection settings
DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://evergreen:evergreen@localhost:5432/evergreen"
)

# Embedding model - Gemini's text-embedding-004 outputs 768 dimensions
EMBEDDING_MODEL = "models/text-embedding-004"
EMBEDDING_DIMENSIONS = 768


class Customer(BaseModel):
    """Customer model for the database."""
    id: int | None = None
    name: str
    description: str
    products_used: str  # Comma-separated list of M365 products
    priority: str = "medium"  # low, medium, high
    notes: str | None = None
    created_at: datetime| None = None
    updated_at: datetime| None = None


class RoadmapItem(BaseModel):
    """Roadmap item model from M365 API."""
    id: int
    title: str
    description: str
    status: str
    public_disclosure_date: str | None = None
    products: list[str] = []
    platforms: list[str] = []
    cloud_instances: list[str] = []
    release_phase: str | None = None


def get_db_connection(database_url: str):
    """Get a connection to the PostgreSQL database."""
    conn = psycopg2.connect(database_url)
    register_vector(conn)
    return conn


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


def get_embedding(text: str, genai_client: genai.Client, embedding_model: str, embedding_dimensions: int) -> list[float]:
    """Generate embedding using Gemini's embedding API."""

    result = genai_client.models.embed_content(
        model=embedding_model,
        content=text,
        task_type="retrieval_document",
        config=EmbedContentConfig(output_dimensionality=embedding_dimensions),
    )
    return result['embedding']


def get_query_embedding(text: str, genai_client: genai.Client, embedding_model: str, embedding_dimensions: int) -> list[float]:
    """Generate embedding for a search query."""
    result = genai_client.models.embed_content(
        model=embedding_model,
        content=text,
        task_type="retrieval_query",
        config=EmbedContentConfig(output_dimensionality=embedding_dimensions),
    )
    embeddings = result.embeddings[0]  # since input is single str
    return embeddings


# Customer CRUD Operations
def add_customer(customer: Customer, database_url: str) -> int:
    """Add a new customer to the database."""
    conn = get_db_connection(database_url=database_url)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO customers (name, description, products_used, priority, notes)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (customer.name, customer.description, customer.products_used, 
          customer.priority, customer.notes))
    
    customer_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return customer_id


def get_customer(customer_id: int, database_url: str) -> Customer | None:
    """Get a customer by ID."""
    conn = get_db_connection(database_url=database_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("SELECT * FROM customers WHERE id = %s", (customer_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return Customer(**row)
    return None


def get_customer_by_name(name: str, database_url: str) -> Customer | None:
    """Get a customer by name."""
    conn = get_db_connection(database_url=database_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("SELECT * FROM customers WHERE name ILIKE %s", (f"%{name}%",))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return Customer(**row)
    return None


def list_customers(database_url: str) -> list[Customer]:
    """List all customers."""
    conn = get_db_connection(database_url=database_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("SELECT * FROM customers ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    
    return [Customer(**row) for row in rows]


def update_customer(customer_id: int, database_url: str, **kwargs) -> bool:
    """Update a customer's fields."""
    if not kwargs:
        return False
    
    conn = get_db_connection(database_url=database_url)
    cursor = conn.cursor()
    
    set_clause = ", ".join(f"{k} = %s" for k in kwargs.keys())
    values = list(kwargs.values()) + [customer_id]
    
    cursor.execute(f"""
        UPDATE customers 
        SET {set_clause}, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """, values)
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def delete_customer(customer_id: int) -> bool:
    """Delete a customer by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM customers WHERE id = %s", (customer_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def search_roadmap(query: str, database_url: str, n_results: int = 5, filter_products: list[str] | None = None) -> list[dict]:
    """Search the roadmap using vector similarity (cosine distance)."""
    conn = get_db_connection(database_url=database_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Generate query embedding
    query_embedding = get_query_embedding(query)
    
    # Build query with optional product filter
    if filter_products:
        product_filter = " OR ".join(["products ILIKE %s" for _ in filter_products])
        cursor.execute(f"""
            SELECT *, embedding <=> %s::vector AS distance
            FROM roadmap_items
            WHERE ({product_filter})
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, [query_embedding] + [f"%{p}%" for p in filter_products] + [query_embedding, n_results])
    else:
        cursor.execute("""
            SELECT *, embedding <=> %s::vector AS distance
            FROM roadmap_items
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, n_results))
    
    rows = cursor.fetchall()
    conn.close()
    
    items = []
    for row in rows:
        items.append({
            "document": row["document"],
            "metadata": {
                "id": row["id"],
                "title": row["title"],
                "status": row["status"],
                "release_date": row["release_date"] or "",
                "products": row["products"] or "",
                "platforms": row["platforms"] or "",
            },
            "distance": row["distance"]
        })
    
    return items


def get_roadmap_stats(database_url: str) -> dict:
    """Get statistics about the roadmap table."""
    conn = get_db_connection(database_url=database_url)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM roadmap_items")
    count = cursor.fetchone()[0]
    conn.close()
    
    return {"total_items": count}
