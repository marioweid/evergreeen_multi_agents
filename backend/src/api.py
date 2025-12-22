"""
Evergreen Multi Agents - FastAPI Application

REST API for querying the M365 Roadmap intelligence system.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai

from agents.orchestrator import OrchestratorAgent
from database import init_db, get_roadmap_stats, list_customers


# Configure Gemini API
def configure_api():
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable required")
    genai.configure(api_key=api_key)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    configure_api()
    init_db()
    yield


app = FastAPI(
    title="Evergreen Multi Agents API",
    description="M365 Roadmap Intelligence System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


# Global orchestrator instance (lazy initialization)
_orchestrator = None


def get_orchestrator() -> OrchestratorAgent:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = OrchestratorAgent()
    return _orchestrator


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
        roadmap_items=roadmap_stats["total_items"],
        customers=len(customers)
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
        orchestrator = get_orchestrator()
        response = orchestrator.query(request.query)
        return QueryResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/customers")
async def get_customers():
    """List all customers."""
    customers = list_customers()
    return [c.model_dump() for c in customers]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
