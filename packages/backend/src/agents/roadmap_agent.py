"""
Evergreen Multi Agents - Roadmap Agent

Agent that answers questions about the M365 Roadmap using RAG.
"""

import google.genai as genai
from google.genai.types import GenerateContentConfig
from database import search_roadmap, get_roadmap_stats


def search_roadmap_tool(query: str, database_url: str, num_results: int = 5) -> str:
    """
    Search the M365 Roadmap for items matching the query.

    Args:
        query: The search query (e.g., "Teams updates", "Copilot features")
        num_results: Number of results to return (default 5)

    Returns:
        A formatted string with the search results
    """
    results = search_roadmap(query, n_results=num_results, database_url=database_url)

    if not results:
        return "No roadmap items found matching your query."

    output = []
    for i, result in enumerate(results, 1):
        metadata = result.get("metadata", {})
        output.append(f"""
**{i}. {metadata.get("title", "Unknown")}**
- Status: {metadata.get("status", "Unknown")}
- Release Date: {metadata.get("release_date", "TBD")}
- Products: {metadata.get("products", "N/A")}
- Platforms: {metadata.get("platforms", "N/A")}
""")

    return "\n".join(output)


def get_roadmap_statistics() -> str:
    """
    Get statistics about the roadmap database.

    Returns:
        Statistics about the roadmap collection
    """
    stats = get_roadmap_stats()
    return f"The roadmap database contains {stats['total_items']} items."


# Define tools for the Gemini model
ROADMAP_TOOLS = [
    {
        "function_declarations": [
            {
                "name": "search_roadmap",
                "description": "Search the Microsoft 365 Roadmap for features, updates, or changes. Use this to find information about upcoming or released M365 features.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query for finding roadmap items",
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of results to return (default 5)",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_roadmap_statistics",
                "description": "Get statistics about the roadmap database, including the total number of items.",
                "parameters": {"type": "object", "properties": {}},
            },
        ]
    }
]


def handle_tool_call(function_name: str, function_args: dict, database_url: str) -> str:
    """Handle tool calls from the model."""
    if function_name == "search_roadmap":
        return search_roadmap_tool(
            query=function_args.get("query", ""),
            database_url=database_url,
            num_results=function_args.get("num_results", 5),
        )
    elif function_name == "get_roadmap_statistics":
        return get_roadmap_statistics()
    else:
        return f"Unknown function: {function_name}"


class RoadmapAgent:
    """Agent for answering questions about the M365 Roadmap."""

    SYSTEM_PROMPT = """You are a Microsoft 365 Roadmap expert assistant. Your role is to help users find information about upcoming and released features in the Microsoft 365 ecosystem.

You have access to the following tools:
- search_roadmap: Search for roadmap items by query
- get_roadmap_statistics: Get statistics about the roadmap database

When a user asks about M365 features, updates, or the roadmap, use the appropriate tool to find relevant information. Provide clear, helpful summaries of the results.

If you don't find relevant results, suggest alternative search terms or ask the user to clarify their question."""

    def __init__(self, database_url: str, model_name: str = "gemini-2.5-flash"):
        self.database_url = database_url
        self.model_name = model_name
        self.client = genai.Client()
        self.chat = None

    def start_chat(self):
        """Start a new chat session."""
        self.chat = self.client.chats.create(
            model=self.model_name,
            config=GenerateContentConfig(
                tools=ROADMAP_TOOLS,
            ),
        )

    def query(self, user_message: str) -> str:
        """Process a user query and return the response."""
        if self.chat is None:
            self.start_chat()

        response = self.chat.send_message(user_message)

        # Handle tool calls
        while response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]

            if hasattr(part, "function_call") and part.function_call:
                func_call = part.function_call
                func_name = func_call.name
                func_args = dict(func_call.args) if func_call.args else {}

                # Execute the tool
                tool_result = handle_tool_call(func_name, func_args, self.database_url)

                # Send the result back to the model
                response = self.chat.send_message(
                    {
                        "function_response": {
                            "name": func_name,
                            "response": {"result": tool_result},
                        }
                    }
                )
            else:
                # No more function calls, return the text response
                break

        return response.text if hasattr(response, "text") else str(response)
