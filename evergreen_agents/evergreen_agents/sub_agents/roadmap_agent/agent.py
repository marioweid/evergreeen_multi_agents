from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

mcp_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(url="http://localhost:8081/mcp"),
)

roadmap_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="roadmap_agent",
    description="I am an expert in Microsoft 365 roadmap and licensing.",
    instruction="You are an expert in Microsoft 365 roadmap and licensing. You help users understand the roadmap and licensing implications of new features.",
    tools=[mcp_toolset],
)
