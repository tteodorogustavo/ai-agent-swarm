from pydantic import BaseModel
from pydantic import Field


class AgentModel(BaseModel):
    """
    Metadata model for representing agent information.

    This model provides a lightweight representation of an agent's identity
    and purpose, useful for API responses, documentation, or agent discovery.

    Attributes:
        name (str): The unique identifier of the agent (e.g., "router_agent", "customer_agent")
        description (str): A human-readable description of the agent's role and capabilities

    Example:
        >>> agent_info = AgentModel(
        ...     name="customer_agent",
        ...     description="Handles private user queries about accounts and transactions"
        ... )
        >>> print(agent_info.name)
        "customer_agent"
    """

    name: str = Field(..., description="The name of the agent")
    description: str = Field(..., description="A brief description of the agent")
