from google.adk.agents.llm_agent import Agent
from sub_agents.roadmap_agent.agent import roadmap_agent
# roadmap_agent = LlmAgent(
#     model="gemini-2.5-flash",
#     name="roadmap_agent",
#     description="I am an expert in Microsoft 365 roadmap and licensing.",
#     instruction="You are an expert in Microsoft 365 roadmap and licensing. You help users understand the roadmap and licensing implications of new features.",
# )

# licensing_agent = LlmAgent(
#     model="gemini-2.5-flash",
#     name="licensing_agent",
#     description="I am an expert in Microsoft 365 licensing.",
#     instruction="You are an expert in Microsoft 365 licensing. You help users understand the licensing implications of new features.",
# )

root_agent = Agent(
    model="gemini-2.5-flash",
    name="root_agent",
    description="I orchestrate the work of other agents.",
    sub_agents=[
        roadmap_agent,
        # licensing_agent,
    ],
)
