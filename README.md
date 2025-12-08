# 🌲 Evergreen Multi Agents

A multi-agent system for tracking the Microsoft 365 Roadmap and analyzing its impact on your customers.

## Features

- **Roadmap Tracking**: Automatically fetches and indexes the M365 Roadmap using vector embeddings
- **Customer Management**: CRUD operations for managing your customer database
- **Impact Analysis**: Analyzes how roadmap changes affect specific customers based on their product usage
- **Weekly Reports**: Generates per-customer impact reports
- **Multi-Agent Architecture**: Orchestrator routes queries to specialized agents (Roadmap, Customer, Impact)

## Tech Stack

- **Python 3.12+** with `uv` for dependency management
- **Google Gemini** for LLM-powered agents with function calling
- **PostgreSQL + pgvector** for vector embeddings and customer data
- **Rich** for CLI interface

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd evergreeen_multi_agents

# Install dependencies with uv
uv sync

# Set up your API key
export GOOGLE_API_KEY='your-gemini-api-key'
```

## Start PostgreSQL

```bash
# Start the database with Docker
docker-compose up -d

# Wait for it to be ready
docker-compose logs -f postgres
```

## Usage

### Start the CLI

```bash
uv run python -m src.main
```

### Ingest Roadmap Data

```bash
uv run python -m src.ingestion
```

### Generate Weekly Report

```bash
uv run python -m src.reporting
```

## Example Commands

Once in the CLI:

- **Roadmap**: "What's new in Microsoft Teams?"
- **Customers**: "Add a customer named Contoso using Teams, SharePoint"
- **Impact**: "How do the new Teams features affect Contoso?"
- **Refresh**: Type `refresh` to update roadmap data
- **Report**: Type `report` to generate a weekly report

## Project Structure

```
evergreeen_multi_agents/
├── src/
│   ├── main.py              # CLI entry point
│   ├── database.py          # PostgreSQL + pgvector operations
│   ├── ingestion.py         # M365 Roadmap API fetcher
│   ├── reporting.py         # Weekly report generator
│   └── agents/
│       ├── orchestrator.py  # Main routing agent
│       ├── roadmap_agent.py # Roadmap Q&A (RAG)
│       ├── customer_agent.py# Customer CRUD
│       └── impact_agent.py  # Impact analysis
├── docker-compose.yml       # PostgreSQL with pgvector
├── init.sql                 # Database schema
└── pyproject.toml
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | - | Gemini API key (required) |
| `DATABASE_URL` | `postgresql://evergreen:evergreen@localhost:5432/evergreen` | PostgreSQL connection string |

## License

MIT
