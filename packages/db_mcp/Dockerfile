FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy pyproject.toml and install dependencies
COPY pyproject.toml .
RUN uv pip install --system .

# Copy source code
COPY server.py .

# Environment variables
ENV PYTHONUNBUFFERED=1

# Run the server
CMD ["python", "server.py"]
