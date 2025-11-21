import logging
from typing import Any
from typing import Dict
from typing import List
from typing import Type

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool

from .prompt import ROUTER_PROMPT
from app.agents.base import Agent
from app.agents.main_state import MainState
from app.models.router_response import RouterResponse

logger = logging.getLogger(__name__)


class RouterAgent(Agent):
    """Router Agent - Triage Manager for routing user queries."""

    name = "router_agent"
    description = "Routes user questions to the appropriate specialized agent"

    def _build_prompt(self) -> ChatPromptTemplate:
        return ROUTER_PROMPT

    def _build_tools(self) -> List[BaseTool]:
        return []

    def _define_state_schema(self) -> Type:
        return MainState

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        messages = state["messages"]
        latest_question = messages[-1].content if messages else ""

        from app.agents.agent_models import agents

        agents_list = "\n".join(
            [f"- `{agent.name}`: {agent.description}" for agent in agents.values()]
        )

        structured_llm = self.get_llm_with_structure(RouterResponse)
        decision: RouterResponse = structured_llm.invoke(
            self._prompt.format_messages(
                messages=messages,
                latest_question=latest_question,
                agents_list=agents_list,
            )
        )

        logger.info(f"Router Decision: Route='{decision.route}'")

        return {
            "route": decision.route,
            "messages": [
                AIMessage(
                    content=f"[Router Log: Decision made. Routing to: {decision.route}]"
                )
            ],
        }


# Legacy wrapper for backward compatibility
def router_node(state: "MainState") -> dict:
    """Legacy wrapper - use RouterAgent().invoke(state) instead."""
    router = RouterAgent()
    return router.invoke(state)
