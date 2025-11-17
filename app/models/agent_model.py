from pydantic import BaseModel, Field

class AgentModel(BaseModel):
   name: str = Field(..., description="The name of the agent")
   description: str = Field(..., description="A brief description of the agent")