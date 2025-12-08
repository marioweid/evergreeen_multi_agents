"""
Evergreen Multi Agents - M365 Roadmap Ingestion

Fetches data from the Microsoft 365 Roadmap API and stores it in ChromaDB.
"""

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.database import RoadmapItem, upsert_roadmap_items, get_roadmap_stats

console = Console()

# New M365 Roadmap API endpoint (replacing deprecated one after March 2025)
M365_ROADMAP_API_URL = "https://www.microsoft.com/releasecommunications/api/v1/m365"


def fetch_roadmap_items() -> list[dict]:
    """Fetch all roadmap items from the M365 API."""
    console.print("[bold blue]Fetching M365 Roadmap data...[/bold blue]")
    
    try:
        headers = {
            "Accept": "application/json",
            "User-Agent": "Evergreen-Multi-Agents/1.0"
        }
        response = requests.get(M365_ROADMAP_API_URL, timeout=60, headers=headers, allow_redirects=True)
        response.raise_for_status()
        data = response.json()
        console.print(f"[green]✓ Fetched {len(data)} roadmap items[/green]")
        return data
    except requests.RequestException as e:
        console.print(f"[red]Error fetching roadmap: {e}[/red]")
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


def ingest_roadmap() -> dict:
    """Main ingestion function - fetch and store roadmap data."""
    raw_items = fetch_roadmap_items()
    
    if not raw_items:
        return {"success": False, "message": "No items fetched", "count": 0}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Processing roadmap items...", total=None)
        
        items = [parse_roadmap_item(item) for item in raw_items]
        progress.update(task, description="Storing in vector database...")
        
        count = upsert_roadmap_items(items)
        progress.update(task, description="Done!")
    
    stats = get_roadmap_stats()
    console.print(f"[bold green]✓ Ingested {count} items. Total in DB: {stats['total_items']}[/bold green]")
    
    return {
        "success": True,
        "message": f"Successfully ingested {count} roadmap items",
        "count": count,
        "total_in_db": stats["total_items"]
    }


if __name__ == "__main__":
    ingest_roadmap()
