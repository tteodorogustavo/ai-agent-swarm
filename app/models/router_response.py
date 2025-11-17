from typing import Literal
from pydantic import BaseModel, Field


class RouterResponse(BaseModel):
    """
    The structured response from the Router Agent.
    It indicates which agent(s) should handle the user's query.
    """
    route: Literal["customer_agent", "knowledge_agent"] = Field(description="The agent to which the query should be routed.")