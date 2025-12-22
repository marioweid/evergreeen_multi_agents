"""
Evergreen Multi Agents - Customer Agent

Agent that manages customer data with CRUD operations.
"""

import google.genai as genai
from database import (
    Customer,
    add_customer,
    delete_customer,
    get_customer,
    get_customer_by_name,
    list_customers,
    update_customer,
)
from google.genai.types import GenerateContentConfig


def add_customer_tool(
    name: str,
    description: str,
    products_used: str,
    priority: str = "medium",
    notes: str = None,
) -> str:
    """
    Add a new customer to the database.

    Args:
        name: Customer name (must be unique)
        description: Description of the customer
        products_used: Comma-separated list of M365 products they use
        priority: Priority level (low, medium, high)
        notes: Additional notes

    Returns:
        Confirmation message with customer ID
    """
    try:
        customer = Customer(
            name=name,
            description=description,
            products_used=products_used,
            priority=priority,
            notes=notes,
        )
        customer_id = add_customer(customer)
        return f"✓ Customer '{name}' added successfully with ID {customer_id}."
    except Exception as e:
        return f"✗ Error adding customer: {e}"


def get_customer_tool(customer_id: int = None, customer_name: str = None) -> str:
    """
    Get customer details by ID or name.

    Args:
        customer_id: The customer's ID
        customer_name: The customer's name (partial match)

    Returns:
        Customer details or error message
    """
    customer = None
    if customer_id:
        customer = get_customer(customer_id)
    elif customer_name:
        customer = get_customer_by_name(customer_name)
    else:
        return "Please provide either customer_id or customer_name."

    if customer:
        return f"""
**Customer: {customer.name}**
- ID: {customer.id}
- Description: {customer.description}
- Products Used: {customer.products_used}
- Priority: {customer.priority}
- Notes: {customer.notes or "None"}
"""
    return "Customer not found."


def list_customers_tool() -> str:
    """
    List all customers in the database.

    Returns:
        Formatted list of all customers
    """
    customers = list_customers()

    if not customers:
        return "No customers in the database."

    output = ["**Customers:**"]
    for c in customers:
        output.append(
            f"- [{c.id}] {c.name} ({c.priority} priority) - Products: {c.products_used}"
        )

    return "\n".join(output)


def update_customer_tool(
    customer_id: int,
    name: str = None,
    description: str = None,
    products_used: str = None,
    priority: str = None,
    notes: str = None,
) -> str:
    """
    Update an existing customer's details.

    Args:
        customer_id: The customer's ID
        name: New name (optional)
        description: New description (optional)
        products_used: New products list (optional)
        priority: New priority (optional)
        notes: New notes (optional)

    Returns:
        Confirmation or error message
    """
    updates = {}
    if name:
        updates["name"] = name
    if description:
        updates["description"] = description
    if products_used:
        updates["products_used"] = products_used
    if priority:
        updates["priority"] = priority
    if notes:
        updates["notes"] = notes

    if not updates:
        return "No updates provided."

    success = update_customer(customer_id, **updates)
    if success:
        return f"✓ Customer {customer_id} updated successfully."
    return f"✗ Customer {customer_id} not found or update failed."


def delete_customer_tool(customer_id: int) -> str:
    """
    Delete a customer from the database.

    Args:
        customer_id: The customer's ID to delete

    Returns:
        Confirmation or error message
    """
    success = delete_customer(customer_id)
    if success:
        return f"✓ Customer {customer_id} deleted successfully."
    return f"✗ Customer {customer_id} not found."


# Define tools for the Gemini model
CUSTOMER_TOOLS = [
    {
        "function_declarations": [
            {
                "name": "add_customer",
                "description": "Add a new customer to the database with their M365 product usage info.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Customer name (unique)",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the customer",
                        },
                        "products_used": {
                            "type": "string",
                            "description": "Comma-separated M365 products",
                        },
                        "priority": {
                            "type": "string",
                            "description": "Priority: low, medium, or high",
                        },
                        "notes": {"type": "string", "description": "Additional notes"},
                    },
                    "required": ["name", "description", "products_used"],
                },
            },
            {
                "name": "get_customer",
                "description": "Get customer details by ID or name.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "integer",
                            "description": "Customer ID",
                        },
                        "customer_name": {
                            "type": "string",
                            "description": "Customer name (partial match)",
                        },
                    },
                },
            },
            {
                "name": "list_customers",
                "description": "List all customers in the database.",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "update_customer",
                "description": "Update a customer's details.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "integer",
                            "description": "Customer ID to update",
                        },
                        "name": {"type": "string", "description": "New name"},
                        "description": {
                            "type": "string",
                            "description": "New description",
                        },
                        "products_used": {
                            "type": "string",
                            "description": "New products list",
                        },
                        "priority": {"type": "string", "description": "New priority"},
                        "notes": {"type": "string", "description": "New notes"},
                    },
                    "required": ["customer_id"],
                },
            },
            {
                "name": "delete_customer",
                "description": "Delete a customer from the database.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "integer",
                            "description": "Customer ID to delete",
                        }
                    },
                    "required": ["customer_id"],
                },
            },
        ]
    }
]


def handle_tool_call(function_name: str, function_args: dict) -> str:
    """Handle tool calls from the model."""
    if function_name == "add_customer":
        return add_customer_tool(**function_args)
    elif function_name == "get_customer":
        return get_customer_tool(**function_args)
    elif function_name == "list_customers":
        return list_customers_tool()
    elif function_name == "update_customer":
        return update_customer_tool(**function_args)
    elif function_name == "delete_customer":
        return delete_customer_tool(**function_args)
    else:
        return f"Unknown function: {function_name}"


class CustomerAgent:
    """Agent for managing customer data."""

    SYSTEM_PROMPT = """You are a customer management assistant. Your role is to help users manage their customer database, including adding, viewing, updating, and deleting customers.

You have access to the following tools:
- add_customer: Add a new customer
- get_customer: Get customer details by ID or name
- list_customers: List all customers
- update_customer: Update customer details
- delete_customer: Delete a customer

Customers have the following attributes:
- name: Unique customer name
- description: Description of the customer
- products_used: Comma-separated list of Microsoft 365 products they use
- priority: low, medium, or high
- notes: Additional notes

Help users manage their customer data efficiently. Confirm actions before making changes when appropriate."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        self.client = genai.Client()
        self.chat = None

    def start_chat(self):
        """Start a new chat session."""
        self.chat = self.client.chats.create(
            model=self.model_name,
            config=GenerateContentConfig(
                tools=CUSTOMER_TOOLS,
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
                tool_result = handle_tool_call(func_name, func_args)

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
                break

        return response.text if hasattr(response, "text") else str(response)
