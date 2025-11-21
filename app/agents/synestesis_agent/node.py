"""Synthesis Agent - OOP Implementation"""
import logging
from typing import Any
from typing import Dict
from typing import List
from typing import Type

from langchain_core.messages import AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool

from .prompt import SYNTHESIS_PROMPT
from app.agents.base import Agent
from app.agents.main_state import MainState

logger = logging.getLogger(__name__)


class SynthesisAgent(Agent):
    """Synthesis Agent - Spokesperson for final response synthesis."""

    name = "synthesis_agent"
    description = "Synthesizes evidence into polished, brand-aligned final responses"

    def _build_prompt(self) -> ChatPromptTemplate:
        return SYNTHESIS_PROMPT

    def _build_tools(self) -> List[BaseTool]:
        return []

    def _define_state_schema(self) -> Type:
        return MainState

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize final response from evidence collected by worker agents.

        The Synthesis Agent acts as a "brand spokesperson" that transforms
        raw, structured data into polished, user-friendly responses. It does
        NOT need to know which tools were called - that information is purely
        for internal logging and auditing purposes.

        Args:
            state: MainState containing messages and final_context

        Returns:
            Updated state with final_response and AIMessage
        """
        messages = state["messages"]
        original_question = state.get("original_question", "")
        final_context_list = state.get("final_context", [])

        # Extract clean content from evidence, discarding metadata
        context_strings = []
        for item in final_context_list:
            if isinstance(item, dict):
                # Extract only the content, ignore tools_called and other metadata
                content = item.get("content", "")
                source = item.get("source", "unknown")

                # Simple format: just source and content
                context_strings.append(f"[{source}]: {content}")

                # Log metadata for auditing (not passed to LLM)
                tools_called = item.get("tools_called", [])
                if tools_called:
                    logger.debug(
                        f"Synthesis: Evidence from {source} (tools used: {', '.join(tools_called)})"
                    )
            elif isinstance(item, str):
                # Legacy string format (backward compatibility)
                context_strings.append(item)
            else:
                logger.warning(f"Unexpected evidence type: {type(item)}")

        # Join all evidence cleanly
        context = "\n---\n".join(context_strings)

        logger.info(
            f"Synthesis: Processing {len(context_strings)} evidence items ({len(context)} chars)"
        )

        # Invoke synthesis chain to add brand personality
        synthesis_chain = self._prompt | self._llm | StrOutputParser()
        final_response = synthesis_chain.invoke(
            {
                "messages": messages,
                "original_question": original_question,
                "context": context,
            }
        )

        logger.info(
            f"Synthesis: Generated final response ({len(final_response)} chars)"
        )

        return {
            "final_response": final_response,
            "messages": [AIMessage(content=final_response)],
        }


# Legacy wrapper for backward compatibility
def synthesis_node(state: MainState) -> dict:
    """Legacy wrapper - use SynthesisAgent().invoke(state) instead."""
    synthesis = SynthesisAgent()
    return synthesis.invoke(state)
