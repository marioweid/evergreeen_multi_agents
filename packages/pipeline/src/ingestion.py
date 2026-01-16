"""
Evergreen Multi Agents - Ingestion Worker

Standalone script for daily M365 Roadmap ingestion with incremental updates.
Designed to run as a scheduled job (cron or container).
"""

import time
import requests
from datetime import datetime


from database import (
    RoadmapItem, upsert_roadmap_items, get_db_connection, init_db
)
from bootstrap import get_genai_client


def get_last_ingestion_time(database_url: str) -> datetime | None:
    """Get the timestamp of the last ingested item."""
    conn = get_db_connection(database_url=database_url)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(updated_at) FROM roadmap_items")
    result = cursor.fetchone()[0]
    conn.close()
    
    if result:
        if isinstance(result, str):
            return datetime.fromisoformat(result.replace("Z", "+00:00"))
        return result
    return None


def fetch_roadmap_items(m365_roadmap_url: str) -> list[dict]:
    """Fetch all roadmap items from the M365 API."""
    print(f"[{datetime.now().isoformat()}] Fetching M365 Roadmap data...")
    
    try:
        headers = {
            "Accept": "application/json",
            "User-Agent": "Evergreen-Multi-Agents/1.0"
        }
        response = requests.get(m365_roadmap_url, timeout=60, headers=headers, allow_redirects=True)
        response.raise_for_status()
        data = response.json()
        print(f"[{datetime.now().isoformat()}] Fetched {len(data)} total roadmap items")
        return data
    except requests.RequestException as e:
        print(f"[{datetime.now().isoformat()}] Error fetching roadmap: {e}")
        return []


def parse_roadmap_item(raw_item: dict) -> RoadmapItem:
    """Parse a raw API response item into a RoadmapItem model."""
    tags_container = raw_item.get("tagsContainer", {})
    
    products = [t.get("tagName", "") for t in tags_container.get("products", [])]
    platforms = [t.get("tagName", "") for t in tags_container.get("platforms", [])]
    cloud_instances = [t.get("tagName", "") for t in tags_container.get("cloudInstances", [])]
    release_phases = [t.get("tagName", "") for t in tags_container.get("releasePhase", [])]
    
    return RoadmapItem(
        id=raw_item.get("id", 0),
        title=raw_item.get("title", ""),
        description=raw_item.get("description", ""),
        status=raw_item.get("status", ""),
        public_disclosure_date=raw_item.get("publicDisclosureAvailabilityDate"),
        products=products,
        platforms=platforms,
        cloud_instances=cloud_instances,
        release_phase=release_phases[0] if release_phases else None
    )


def filter_new_items(raw_items: list[dict], since: datetime | None) -> list[dict]:
    """Filter items that have been modified since the last ingestion."""
    if since is None:
        print(f"[{datetime.now().isoformat()}] No previous ingestion found, processing all items")
        return raw_items
    
    new_items = []
    for item in raw_items:
        modified_str = item.get("modified") or item.get("created")
        if modified_str:
            try:
                modified = datetime.fromisoformat(modified_str.replace("Z", "+00:00"))
                if modified.tzinfo:
                    modified = modified.replace(tzinfo=None)
                if since.tzinfo:
                    since = since.replace(tzinfo=None)
                if modified > since:
                    new_items.append(item)
            except (ValueError, TypeError):
                # If we can't parse the date, include it to be safe
                new_items.append(item)
    
    return new_items


def run_ingestion(database_url: str, google_api_key: str, full_sync: bool = False, embedding_model: str = "models/text-embedding-004", embedding_dimensions: int = 768, m365_roadmap_api_url: str = "https://www.microsoft.com/releasecommunications/api/v1/m365"):
    """Run the ingestion process."""
    print(f"\n{'='*60}")
    print(f"[{datetime.now().isoformat()}] Starting Evergreen Ingestion Worker")
    print(f"{'='*60}")
    
    # Initialize
    init_db(database_url=database_url, embedding_dimensions=embedding_dimensions)
    genai_client = get_genai_client(api_key=google_api_key)
    
    # Get last ingestion time for incremental updates
    last_ingestion = None if full_sync else get_last_ingestion_time(database_url=database_url)
    
    if last_ingestion:
        print(f"[{datetime.now().isoformat()}] Last ingestion: {last_ingestion.isoformat()}")
    
    # Fetch data
    raw_items = fetch_roadmap_items(m365_roadmap_url=m365_roadmap_api_url)
    if not raw_items:
        print(f"[{datetime.now().isoformat()}] No items fetched, exiting")
        return
    
    # Filter for new/updated items
    items_to_process = filter_new_items(raw_items, last_ingestion)
    print(f"[{datetime.now().isoformat()}] {len(items_to_process)} items to process (new/updated)")
    
    if not items_to_process:
        print(f"[{datetime.now().isoformat()}] No new items to ingest")
        return
    
    # Parse and upsert
    parsed_items = [parse_roadmap_item(item) for item in items_to_process]
    
    # Process in batches to avoid rate limits
    batch_size = 10
    total_ingested = 0
    
    for i in range(0, len(parsed_items), batch_size):
        batch = parsed_items[i:i + batch_size]
        count = upsert_roadmap_items(items=batch, database_url=database_url, genai_client=genai_client, embedding_model=embedding_model, embedding_dimensions=embedding_dimensions)
        total_ingested += count
        print(f"[{datetime.now().isoformat()}] Ingested batch {i//batch_size + 1}: {count} items")
        
        # Small delay to avoid rate limits on embedding API
        if i + batch_size < len(parsed_items):
            time.sleep(1)
    
    print(f"\n[{datetime.now().isoformat()}] ✓ Ingestion complete: {total_ingested} items processed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import os
    
    # Read ENV
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("ERROR: DATABASE_URL environment variable required")

    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("ERROR: GOOGLE_API_KEY environment variable required")

    full_sync = bool(os.environ.get("FULL_SYNC"))

    embedding_model = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
    embedding_dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", 768))

    # M365 Roadmap API
    m365_roadmap_api_url = os.getenv("M365_ROADMAP_API_URL", "https://www.microsoft.com/releasecommunications/api/v1/m365")

    run_ingestion(database_url=database_url, google_api_key=google_api_key, full_sync=full_sync, m365_roadmap_api_url=m365_roadmap_api_url)
