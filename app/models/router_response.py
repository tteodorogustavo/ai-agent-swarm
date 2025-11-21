from typing import Literal

from pydantic import BaseModel
from pydantic import Field


class RouterResponse(BaseModel):
    """
    The structured response from the Router Agent.

    This schema defines the output format for the Router's LLM decision.
    It is NOT the state of the Router Agent (which uses MainState).

    Purpose:
        Used with `llm.with_structured_output(RouterResponse)` to ensure
        the LLM returns a valid routing decision in a structured format.

    Example:
        >>> response = RouterResponse(route="customer_agent")
        >>> print(response.route)
        "customer_agent"
    """

    route: Literal["customer_agent", "knowledge_agent"] = Field(
        description="The agent to which the query should be routed."
    )
