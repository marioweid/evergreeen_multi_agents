-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    products_used TEXT NOT NULL,
    priority TEXT DEFAULT 'medium',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Roadmap items table with vector embeddings
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
    embedding vector(768),  -- Using 768 dimensions for Gemini text-embedding-004
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for vector similarity search (created after data is loaded)
-- CREATE INDEX IF NOT EXISTS roadmap_embedding_idx ON roadmap_items 
-- USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
