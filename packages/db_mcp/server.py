import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from mcp.server.fastmcp import FastMCP
from pgvector.psycopg2 import register_vector
import google.genai as genai
from google.genai.types import EmbedContentConfig

# Initialize FastMCP server
mcp = FastMCP("Roadmap Database", json_response=True)

# Configuration
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://evergreen:evergreen@localhost:5432/evergreen"
)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
EMBEDDING_MODEL = "models/text-embedding-004"
EMBEDDING_DIMENSIONS = 768


def get_db_connection():
    """Get a connection to the PostgreSQL database."""
    conn = psycopg2.connect(DATABASE_URL)
    register_vector(conn)
    return conn


def get_query_embedding(text: str) -> list[float]:
    """Generate embedding for a search query using Gemini."""
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY environment variable is required for search")

    client = genai.Client(api_key=GOOGLE_API_KEY)
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=EmbedContentConfig(
            task_type="RETRIEVAL_QUERY", output_dimensionality=EMBEDDING_DIMENSIONS
        ),
    )
    # The SDK returns an object where result.embeddings is a list of embeddings
    if not result.embeddings:
        raise ValueError("No embeddings returned from Gemini")
    return result.embeddings[0].values


@mcp.tool()
def search_roadmap(query: str, n_results: int = 5) -> str:
    """
    Search the Microsoft 365 Roadmap using semantic similarity.
    Use this to find features, updates, or upcoming changes.
    """
    try:
        query_embedding = get_query_embedding(query)
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT id, title, description, status, release_date, products, platforms, 
                   embedding <=> %s::vector AS distance
            FROM roadmap_items
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """,
            (query_embedding, query_embedding, n_results),
        )

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "No matching roadmap items found."

        results = []
        for row in rows:
            results.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "status": row["status"],
                    "release_date": row["release_date"],
                    "products": row["products"],
                    "platforms": row["platforms"],
                    "description": row["description"][:500] + "..."
                    if row["description"] and len(row["description"]) > 500
                    else row["description"],
                    "relevance": 1 - row["distance"],
                }
            )

        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error searching roadmap: {str(e)}"


@mcp.tool()
def get_roadmap_item(item_id: int) -> str:
    """
    Get full details of a specific roadmap item by its ID.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("SELECT * FROM roadmap_items WHERE id = %s", (item_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return f"Roadmap item with ID {item_id} not found."

        # Remove embedding from output
        if "embedding" in row:
            del row["embedding"]

        return json.dumps(row, indent=2, default=str)
    except Exception as e:
        return f"Error retrieving roadmap item: {str(e)}"


@mcp.tool()
def list_roadmap_items(
    status: str | None = None, limit: int = 10, offset: int = 0
) -> str:
    """
    List roadmap items with optional filtering by status.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = "SELECT id, title, status, release_date FROM roadmap_items"
        params = []

        if status:
            query += " WHERE status = %s"
            params.append(status)

        query += " ORDER BY updated_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return json.dumps(rows, indent=2, default=str)
    except Exception as e:
        return f"Error listing roadmap items: {str(e)}"


@mcp.tool()
def get_roadmap_stats() -> str:
    """
    Get statistics about the roadmap database.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM roadmap_items")
        total_items = cursor.fetchone()[0]

        cursor.execute("SELECT status, COUNT(*) FROM roadmap_items GROUP BY status")
        status_counts = dict(cursor.fetchall())

        conn.close()

        return json.dumps(
            {"total_items": total_items, "status_breakdown": status_counts}, indent=2
        )
    except Exception as e:
        return f"Error getting roadmap stats: {str(e)}"


def main():
    # mcp.run(transport="http", host="0.0.0.0", port=8000)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
