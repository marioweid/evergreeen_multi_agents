from google.adk.agents import LlmAgent

roadmap_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="roadmap_agent",
    description="I am an expert in Microsoft 365 roadmap and licensing.",
    instruction="You are an expert in Microsoft 365 roadmap and licensing. You help users understand the roadmap and licensing implications of new features.",
)
