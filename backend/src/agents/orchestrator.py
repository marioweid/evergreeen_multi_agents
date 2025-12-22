"""
Evergreen Multi Agents - Orchestrator Agent

Main agent that routes user queries to the appropriate sub-agent.
"""

import google.genai as genai
from google.genai.types import GenerateContentConfig, Tool
from agents.customer_agent import CustomerAgent
from agents.impact_agent import ImpactAgent
from agents.roadmap_agent import RoadmapAgent
from google.genai.chats import Chat

def route_to_roadmap_agent(query: str, database_url: str) -> str:
    """Route query to the Roadmap Agent for M365 roadmap questions."""
    agent = RoadmapAgent(database_url=database_url)
    return agent.query(query)


def route_to_customer_agent(query: str) -> str:
    """Route query to the Customer Agent for customer management."""
    agent = CustomerAgent()
    return agent.query(query)


def route_to_impact_agent(query: str) -> str:
    """Route query to the Impact Agent for impact analysis."""
    agent = ImpactAgent()
    return agent.query(query)


def refresh_roadmap_data() -> str:
    """Refresh the roadmap data from the M365 API."""
    # Ingestion is now a separate service - it runs on a daily schedule
    return "ℹ️ Roadmap data is automatically refreshed daily by the ingestion service. No manual refresh needed."


# Define routing tools for the orchestrator
roadmap_agent_declaration = {
    "name": "route_to_roadmap_agent",
    "description": "Route to the Roadmap Agent for questions about Microsoft 365 roadmap, features, updates, and upcoming changes.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The user's question about the roadmap",
            },
            "database_url": {
                "type": "string",
                "description": "The URL of the database to use for roadmap data",
            },
        },
        "required": ["query", "database_url"],
    },
}
# ORCHESTRATOR_TOOLS = {
#     "function_declarations": [
#         {
#             "name": "route_to_roadmap_agent",
#             "description": "Route to the Roadmap Agent for questions about Microsoft 365 roadmap, features, updates, and upcoming changes.",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "query": {
#                         "type": "string",
#                         "description": "The user's question about the roadmap",
#                     }
#                 },
#                 "required": ["query"],
#             },
#         },
#         {
#             "name": "route_to_customer_agent",
#             "description": "Route to the Customer Agent for managing customers - adding, viewing, updating, or deleting customer records.",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "query": {
#                         "type": "string",
#                         "description": "The user's request about customers",
#                     }
#                 },
#                 "required": ["query"],
#             },
#         },
#         {
#             "name": "route_to_impact_agent",
#             "description": "Route to the Impact Agent for analyzing how roadmap changes affect specific customers or for impact reports.",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "query": {
#                         "type": "string",
#                         "description": "The user's question about impact analysis",
#                     }
#                 },
#                 "required": ["query"],
#             },
#         },
#         {
#             "name": "refresh_roadmap_data",
#             "description": "Refresh the roadmap database by fetching latest data from the M365 API.",
#             "parameters": {"type": "object", "properties": {}},
#         },
#     ]
# }


def handle_tool_call(function_name: str, function_args: dict) -> str:
    """Handle tool calls from the orchestrator."""
    if function_name == "route_to_roadmap_agent" or function_name == "roadmap_agent_declaration":
        query = function_args.get("query", "")
        database_url = function_args.get("database_url", "")
        print(f"PRINT: CALLING FUNCTION WITH {query=} and {database_url=}")
        return route_to_roadmap_agent(
            query=query,
            database_url=database_url,
        )
    elif function_name == "route_to_customer_agent":
        return route_to_customer_agent(function_args.get("query", ""))
    elif function_name == "route_to_impact_agent":
        return route_to_impact_agent(function_args.get("query", ""))
    elif function_name == "refresh_roadmap_data":
        return refresh_roadmap_data()
    else:
        return f"Unknown function: {function_name}"


class OrchestratorAgent:
    """Main orchestrator that routes queries to specialized agents."""

    SYSTEM_PROMPT = """You are the Evergreen Multi-Agent Orchestrator. You help users interact with Microsoft 365 roadmap data and customer information.

You manage three specialized agents:
1. **Roadmap Agent**: For questions about M365 features, updates, and roadmap items
2. **Customer Agent**: For managing customer data (add, view, update, delete customers)
3. **Impact Agent**: For analyzing how roadmap changes affect specific customers

Route user requests to the appropriate agent based on their intent:
- Questions about "what's new in Teams/Copilot/etc" → Roadmap Agent
- "Add customer", "list customers", "update customer" → Customer Agent
- "How does this affect [customer]", "impact analysis" → Impact Agent
- "Refresh/update roadmap data" → Use refresh_roadmap_data

Always pass the complete context of the user's question to the sub-agent. Summarize the sub-agent's response clearly for the user.

If the user's intent is unclear, ask for clarification before routing."""

    def __init__(self, database_url: str, model_name: str = "gemini-2.5-flash"):
        self.database_url = database_url
        self.model_name = model_name
        self.config = GenerateContentConfig(
            tools=[Tool(function_declarations=[roadmap_agent_declaration])],
        )
        self.client = genai.Client()
        self.chat = None

    def start_chat(self):
        """Start a new chat session."""
        self.chat: Chat = self.client.chats.create(
            model=self.model_name,
            config=self.config,
        )

    def query(self, user_message: str) -> str:
        """Process a user query, routing to the appropriate sub-agent."""
        if self.chat is None:
            self.start_chat()

        response = self.chat.send_message(
            message=user_message,
            config=self.config
        )

        # Handle tool calls (routing to sub-agents)
        while response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]

            if hasattr(part, "function_call") and part.function_call:
                func_call = part.function_call
                func_name = func_call.name
                func_args = dict(func_call.args) if func_call.args else {}
                func_args["database_url"] = self.database_url

                # Execute the routing
                tool_result = handle_tool_call(func_name, func_args)

                # Send the sub-agent's response back
                response = self.chat.send_message(
                    {
                        "function_response": {
                            "name": func_name,
                            "response": {"result": tool_result},
                        }
                    }
                )
            else:
                break

        return response.text if hasattr(response, "text") else str(response)
