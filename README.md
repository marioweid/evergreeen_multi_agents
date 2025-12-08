# 🌲 Evergreen Multi Agents

A multi-agent system for tracking the Microsoft 365 Roadmap and analyzing its impact on your customers.

## Features

- **Roadmap Tracking**: Automatically fetches and indexes the M365 Roadmap using vector embeddings
- **Customer Management**: CRUD operations for managing your customer database
- **Impact Analysis**: Analyzes how roadmap changes affect specific customers
- **Weekly Reports**: Generates per-customer impact reports
- **Containerized**: Runs as separate API and ingestion services

## Tech Stack

- **Python 3.12+** with `uv` for dependency management
- **FastAPI** for the REST API
- **Google Gemini** for LLM-powered agents and embeddings
- **PostgreSQL + pgvector** for vector search and data storage
- **Docker Compose** for orchestration

## Quick Start

```bash
# 1. Clone and setup
git clone <repo-url>
cd evergreeen_multi_agents
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# 2. Start all services
docker-compose up -d --build

# 3. Check status
docker-compose logs -f
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/stats` | Database statistics |
| GET | `/customers` | List all customers |
| POST | `/query` | Query the multi-agent system |

### Query Example

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is new in Microsoft Teams?"}'
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   API Service   │     │ Ingestion Worker│
│   (FastAPI)     │     │  (Daily Cron)   │
│  packages/api   │     │packages/ingestion│
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────▼──────┐
              │  PostgreSQL │
              │  + pgvector │
              └─────────────┘
```

## Project Structure

```
evergreeen_multi_agents/
├── packages/
│   ├── api/                 # API Service
│   │   ├── src/
│   │   │   ├── api.py       # FastAPI application
│   │   │   ├── database.py  # PostgreSQL + pgvector
│   │   │   ├── reporting.py # Report generator
│   │   │   └── agents/      # Multi-agent system
│   │   └── pyproject.toml
│   │
│   └── ingestion/           # Ingestion Pipeline
│       ├── src/
│       │   ├── ingestion.py # Daily ingestion worker
│       │   └── database.py  # PostgreSQL + pgvector
│       └── pyproject.toml
│
├── docker-compose.yml       # All services
├── Dockerfile.api           # API container
├── Dockerfile.ingestion     # Ingestion container
└── init.sql                 # Database schema
```

## Local Development

```bash
# Start just the database
docker-compose up -d postgres

# Run API locally
cd packages/api
uv sync
export GOOGLE_API_KEY='your-key'
uv run uvicorn src.api:app --reload

# Run ingestion locally
cd packages/ingestion
uv sync
uv run python -m src.ingestion
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Gemini API key |
| `DATABASE_URL` | No | PostgreSQL connection string |

## License

MIT
