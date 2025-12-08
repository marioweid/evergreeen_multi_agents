"""
Evergreen Multi Agents - Orchestrator Agent

Main agent that routes user queries to the appropriate sub-agent.
"""

import google.generativeai as genai
from src.agents.roadmap_agent import RoadmapAgent
from src.agents.customer_agent import CustomerAgent
from src.agents.impact_agent import ImpactAgent
from src.ingestion import ingest_roadmap


def route_to_roadmap_agent(query: str) -> str:
    """Route query to the Roadmap Agent for M365 roadmap questions."""
    agent = RoadmapAgent()
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
    result = ingest_roadmap()
    if result["success"]:
        return f"✓ Roadmap data refreshed. {result['count']} items ingested."
    return f"✗ Failed to refresh roadmap data: {result['message']}"


# Define routing tools for the orchestrator
ORCHESTRATOR_TOOLS = [
    {
        "function_declarations": [
            {
                "name": "route_to_roadmap_agent",
                "description": "Route to the Roadmap Agent for questions about Microsoft 365 roadmap, features, updates, and upcoming changes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The user's question about the roadmap"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "route_to_customer_agent",
                "description": "Route to the Customer Agent for managing customers - adding, viewing, updating, or deleting customer records.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The user's request about customers"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "route_to_impact_agent",
                "description": "Route to the Impact Agent for analyzing how roadmap changes affect specific customers or for impact reports.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The user's question about impact analysis"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "refresh_roadmap_data",
                "description": "Refresh the roadmap database by fetching latest data from the M365 API.",
                "parameters": {"type": "object", "properties": {}}
            }
        ]
    }
]


def handle_tool_call(function_name: str, function_args: dict) -> str:
    """Handle tool calls from the orchestrator."""
    if function_name == "route_to_roadmap_agent":
        return route_to_roadmap_agent(function_args.get("query", ""))
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

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=self.SYSTEM_PROMPT,
            tools=ORCHESTRATOR_TOOLS
        )
        self.chat = None
    
    def start_chat(self):
        """Start a new chat session."""
        self.chat = self.model.start_chat()
    
    def query(self, user_message: str) -> str:
        """Process a user query, routing to the appropriate sub-agent."""
        if self.chat is None:
            self.start_chat()
        
        response = self.chat.send_message(user_message)
        
        # Handle tool calls (routing to sub-agents)
        while response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            
            if hasattr(part, 'function_call') and part.function_call:
                func_call = part.function_call
                func_name = func_call.name
                func_args = dict(func_call.args) if func_call.args else {}
                
                # Execute the routing
                tool_result = handle_tool_call(func_name, func_args)
                
                # Send the sub-agent's response back
                response = self.chat.send_message({
                    "function_response": {
                        "name": func_name,
                        "response": {"result": tool_result}
                    }
                })
            else:
                break
        
        return response.text if hasattr(response, 'text') else str(response)
