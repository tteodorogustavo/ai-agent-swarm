from ..models.agent_model import AgentModel
from typing import List


agents = List[
        AgentModel(
            name='customer_agent',
            description='Handles customer inquiries related to account status, transactions, and support issues.'),
        AgentModel(
            name='knowledge_agent',
            description='Provides information about InfinitePay products and services from the internal knowledge base and web searches.'),
        AgentModel(
            name='synthesis_agent',
            description='This agent must provide the personality of the responses.')
            ]