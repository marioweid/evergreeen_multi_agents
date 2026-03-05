"""Root agent for evergreen multi-agent system."""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent

from .sub_agents.roadmap_agent import roadmap_agent


root_agent = Agent(
    model="gemini-2.5-flash",
    name="root_agent",
    description="I orchestrate the work of other agents.",
    sub_agents=[
        roadmap_agent,
    ],
)
