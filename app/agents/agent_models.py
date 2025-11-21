from typing import Dict

from ..models.agent_model import AgentModel

# Temporary dictionary structure for agents until full OOP refactoring
agents: Dict[str, AgentModel] = {
    "customer_agent": AgentModel(
        name="customer_agent",
        description="Handles customer inquiries related to account status, transactions, and support issues.",
    ),
    "knowledge_agent": AgentModel(
        name="knowledge_agent",
        description="Provides information about InfinitePay products and services from the internal knowledge base and web searches.",
    ),
    "synthesis_agent": AgentModel(
        name="synthesis_agent",
        description="This agent must provide the personality of the responses.",
    ),
}
