"""
Evergreen Multi Agents - FastAPI Application

REST API for querying the M365 Roadmap intelligence system.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agents.orchestrator import OrchestratorAgent
from database import init_db, get_roadmap_stats, list_customers
from settings import Settings

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    database_url = str(settings.database_url)
    embedding_dimensions = settings.embedding_dimensions

    init_db(database_url=database_url, embedding_dimensions=embedding_dimensions)
    yield


app = FastAPI(
    title="Evergreen Multi Agents API",
    description="M365 Roadmap Intelligence System",
    version="1.0.0",
    lifespan=lifespan,
)


# Request/Response models
class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    response: str
    success: bool = True


class StatsResponse(BaseModel):
    roadmap_items: int
    customers: int


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get database statistics."""
    roadmap_stats = get_roadmap_stats()
    customers = list_customers()
    return StatsResponse(
        roadmap_items=roadmap_stats["total_items"], customers=len(customers)
    )


@app.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """
    Send a query to the multi-agent system.

    Examples:
    - "What's new in Microsoft Teams?"
    - "Add a customer named Contoso using Teams and SharePoint"
    - "How do the new Teams features affect Contoso?"
    """
    try:
        orchestrator = OrchestratorAgent(database_url=settings.database_url)
        response = orchestrator.query(request.query)
        return QueryResponse(response=response)
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/customers")
async def get_customers():
    """List all customers."""
    customers = list_customers()
    return [c.model_dump() for c in customers]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
