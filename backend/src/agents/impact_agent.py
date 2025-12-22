"""
Evergreen Multi Agents - Impact Analysis Agent

Agent that analyzes the impact of M365 roadmap changes on specific customers.
"""

import google.generativeai as genai
from src.database import (
    get_customer, get_customer_by_name, list_customers,
    search_roadmap
)


def analyze_customer_impact(customer_id: int = None, customer_name: str = None) -> str:
    """
    Analyze how upcoming M365 changes might impact a customer.
    
    Args:
        customer_id: The customer's ID
        customer_name: The customer's name
    
    Returns:
        Analysis of roadmap items relevant to the customer
    """
    # Get customer
    customer = None
    if customer_id:
        customer = get_customer(customer_id)
    elif customer_name:
        customer = get_customer_by_name(customer_name)
    
    if not customer:
        return "Customer not found. Please provide a valid customer ID or name."
    
    # Parse customer's products
    products = [p.strip() for p in customer.products_used.split(",")]
    
    # Search roadmap for each product
    all_impacts = []
    for product in products:
        results = search_roadmap(product, n_results=3)
        for result in results:
            metadata = result.get("metadata", {})
            all_impacts.append({
                "product": product,
                "title": metadata.get("title", "Unknown"),
                "status": metadata.get("status", "Unknown"),
                "release_date": metadata.get("release_date", "TBD"),
                "description": result.get("document", "")[:200]
            })
    
    if not all_impacts:
        return f"No upcoming changes found affecting {customer.name}'s products ({customer.products_used})."
    
    # Format output
    output = [f"## Impact Analysis for {customer.name}\n"]
    output.append(f"**Products Used:** {customer.products_used}")
    output.append(f"**Priority:** {customer.priority}\n")
    output.append("### Relevant Roadmap Changes:\n")
    
    for i, impact in enumerate(all_impacts, 1):
        output.append(f"""**{i}. {impact['title']}**
- Related Product: {impact['product']}
- Status: {impact['status']}
- Expected: {impact['release_date']}
""")
    
    return "\n".join(output)


def get_high_impact_changes() -> str:
    """
    Get roadmap changes that might have high impact across all customers.
    
    Returns:
        Summary of high-impact changes and affected customers
    """
    customers = list_customers()
    if not customers:
        return "No customers in the database to analyze."
    
    # Collect all products used by high-priority customers
    high_priority_products = set()
    for customer in customers:
        if customer.priority == "high":
            products = [p.strip() for p in customer.products_used.split(",")]
            high_priority_products.update(products)
    
    if not high_priority_products:
        # Fall back to all products if no high priority customers
        for customer in customers:
            products = [p.strip() for p in customer.products_used.split(",")]
            high_priority_products.update(products)
    
    # Search for changes in these products
    output = ["## High Impact Changes Overview\n"]
    
    for product in list(high_priority_products)[:5]:  # Limit to top 5
        results = search_roadmap(product, n_results=2)
        if results:
            output.append(f"### {product}")
            for result in results:
                metadata = result.get("metadata", {})
                output.append(f"- {metadata.get('title', 'Unknown')} ({metadata.get('status', 'Unknown')})")
            output.append("")
    
    return "\n".join(output)


# Define tools for the Gemini model
IMPACT_TOOLS = [
    {
        "function_declarations": [
            {
                "name": "analyze_customer_impact",
                "description": "Analyze how upcoming M365 roadmap changes affect a specific customer based on their product usage.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {"type": "integer", "description": "Customer ID"},
                        "customer_name": {"type": "string", "description": "Customer name"}
                    }
                }
            },
            {
                "name": "get_high_impact_changes",
                "description": "Get an overview of high-impact roadmap changes across all customers.",
                "parameters": {"type": "object", "properties": {}}
            }
        ]
    }
]


def handle_tool_call(function_name: str, function_args: dict) -> str:
    """Handle tool calls from the model."""
    if function_name == "analyze_customer_impact":
        return analyze_customer_impact(**function_args)
    elif function_name == "get_high_impact_changes":
        return get_high_impact_changes()
    else:
        return f"Unknown function: {function_name}"


class ImpactAgent:
    """Agent for analyzing roadmap impact on customers."""
    
    SYSTEM_PROMPT = """You are an impact analysis specialist for Microsoft 365 roadmap changes. Your role is to help users understand how upcoming M365 features and changes will affect their customers.

You have access to the following tools:
- analyze_customer_impact: Analyze impact for a specific customer
- get_high_impact_changes: Get overview of high-impact changes across all customers

When analyzing impact:
1. Consider the customer's current product usage
2. Identify relevant upcoming changes
3. Explain the potential impact (positive and negative)
4. Suggest preparation steps if needed

Help users prioritize their attention on the most impactful changes for their customer base."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=self.SYSTEM_PROMPT,
            tools=IMPACT_TOOLS
        )
        self.chat = None
    
    def start_chat(self):
        """Start a new chat session."""
        self.chat = self.model.start_chat()
    
    def query(self, user_message: str) -> str:
        """Process a user query and return the response."""
        if self.chat is None:
            self.start_chat()
        
        response = self.chat.send_message(user_message)
        
        # Handle tool calls
        while response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            
            if hasattr(part, 'function_call') and part.function_call:
                func_call = part.function_call
                func_name = func_call.name
                func_args = dict(func_call.args) if func_call.args else {}
                
                tool_result = handle_tool_call(func_name, func_args)
                
                response = self.chat.send_message({
                    "function_response": {
                        "name": func_name,
                        "response": {"result": tool_result}
                    }
                })
            else:
                break
        
        return response.text if hasattr(response, 'text') else str(response)
