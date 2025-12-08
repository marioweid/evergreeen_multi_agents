"""
Evergreen Multi Agents - Main CLI

Interactive command-line interface for the multi-agent system.
"""

import os
import sys
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.panel import Panel
import google.generativeai as genai

from src.agents.orchestrator import OrchestratorAgent
from src.ingestion import ingest_roadmap
from src.reporting import generate_weekly_report, save_weekly_report
from src.database import init_db


console = Console()


def configure_api():
    """Configure the Gemini API key."""
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        console.print("[yellow]No API key found in environment.[/yellow]")
        console.print("Please set GOOGLE_API_KEY or GEMINI_API_KEY environment variable.")
        console.print("\nExample:")
        console.print("  export GOOGLE_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    genai.configure(api_key=api_key)
    return True


def print_welcome():
    """Print welcome message."""
    welcome = """
# 🌲 Evergreen Multi Agents

Welcome to the M365 Roadmap Intelligence System!

**Available Commands:**
- Type your question to interact with the agents
- `refresh` - Refresh roadmap data from M365 API
- `report` - Generate weekly customer report
- `help` - Show this help message
- `exit` or `quit` - Exit the application

**Example Questions:**
- "What's new in Microsoft Teams?"
- "Add a customer named Contoso using Teams and SharePoint"
- "List all customers"
- "How do the new Teams features affect Contoso?"
"""
    console.print(Markdown(welcome))


def run_cli():
    """Run the interactive CLI."""
    # Initialize
    init_db()
    configure_api()
    
    # Create orchestrator
    orchestrator = OrchestratorAgent()
    
    print_welcome()
    console.print()
    
    while True:
        try:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
            
            if not user_input.strip():
                continue
            
            # Handle special commands
            lower_input = user_input.lower().strip()
            
            if lower_input in ("exit", "quit", "q"):
                console.print("[yellow]Goodbye![/yellow]")
                break
            
            if lower_input == "help":
                print_welcome()
                continue
            
            if lower_input == "refresh":
                with console.status("[bold green]Refreshing roadmap data..."):
                    result = ingest_roadmap()
                console.print(Panel(f"✓ Refreshed: {result['count']} items", title="Roadmap Update"))
                continue
            
            if lower_input == "report":
                with console.status("[bold green]Generating weekly report..."):
                    report = generate_weekly_report()
                    path = save_weekly_report()
                console.print(Markdown(report))
                console.print(f"\n[dim]{path}[/dim]")
                continue
            
            # Process with orchestrator
            with console.status("[bold blue]Thinking..."):
                response = orchestrator.query(user_input)
            
            console.print()
            console.print(Panel(Markdown(response), title="[bold green]Assistant[/bold green]", border_style="green"))
            console.print()
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    run_cli()
