"""
Main Graph Builder - OOP Orchestrator

This module constructs the main agent orchestration graph using LangGraph.
It assembles all specialized agents (Router, Customer, Knowledge, Synthesis)
into a hierarchical workflow with conditional routing and loops.

Architecture:
    1. Router Agent → Analyzes query and routes to appropriate specialist
    2. Specialist Agents → Process query (Knowledge or Customer)
    3. Loop back to Router → Re-evaluate if more information needed
    4. Synthesis Agent → Generates final polished response
    5. END → Returns final response to user

This implements the "Hierarchical Sub-Graph Orchestrator" pattern where
each agent is a self-contained unit that can be invoked independently.
"""
import logging
from typing import Any
from typing import Dict

from langgraph.graph import END
from langgraph.graph import StateGraph

from app.agents.customer_agent.node import CustomerAgent
from app.agents.knowledge_agent.agent import KnowledgeAgent
from app.agents.main_state import MainState
from app.agents.router_agent.node import RouterAgent
from app.agents.synestesis_agent.node import SynthesisAgent
# Import the main state schema
# Import agent classes (OOP architecture)
# Optional tracing initialization

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# STATE MAPPING WRAPPERS - Map MainState to Agent-specific states
# =============================================================================


def knowledge_node(state: MainState) -> Dict[str, Any]:
    """
    Wrapper for KnowledgeAgent that maps MainState → KnowledgeState.

    Extracts the last user question from messages and maps to original_question.
    """
    # Extract last human message as the question
    messages = state.get("messages", [])
    last_human_message = None
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "human":
            last_human_message = msg.content
            break

    if not last_human_message:
        logger.error("No human message found in state!")
        return {
            "final_answer": "Erro: Nenhuma pergunta foi encontrada.",
            "final_context": [],  # MainState uses final_context, not final_evidence
            "route": "synthesis_agent",
        }

    # Map MainState → KnowledgeState
    knowledge_state = {
        "original_question": last_human_message,
        "user_id": state.get("user_id", ""),
        "messages": [],  # Knowledge agent has its own message history
        "context": [],
        "draft_answer": "",
        "grade_decision": "",
        "tools_called": [],
        "final_answer": "",
        "final_evidence": [],
    }

    logger.info(f"Mapped question to KnowledgeAgent: {last_human_message[:100]}...")

    # Invoke knowledge agent
    result = knowledge_agent.invoke(knowledge_state)

    # Map back to MainState updates
    # CRITICAL: MainState uses "final_context" (with operator.add), not "final_evidence"
    return {
        "final_answer": result.get("final_answer", ""),
        "final_context": result.get(
            "final_evidence", []
        ),  # Map final_evidence → final_context
        "route": result.get("route", "synthesis_agent"),
    }


def customer_node(state: MainState) -> Dict[str, Any]:
    """
    Wrapper for CustomerAgent that maps MainState → CustomerState.

    Extracts the last user question from messages.
    """
    # Extract last human message as the question
    messages = state.get("messages", [])
    last_human_message = None
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "human":
            last_human_message = msg.content
            break

    if not last_human_message:
        logger.error("No human message found in state!")
        return {
            "final_answer": "Erro: Nenhuma pergunta foi encontrada.",
            "final_context": [],  # MainState uses final_context, not final_evidence
            "route": "synthesis_agent",
        }

    # CustomerAgent expects messages directly
    customer_state = {
        "user_id": state.get("user_id", ""),
        "messages": [
            msg for msg in messages if hasattr(msg, "type") and msg.type == "human"
        ],
        "final_evidence": [],
    }

    logger.info(f"Mapped question to CustomerAgent: {last_human_message[:100]}...")

    # Invoke customer agent
    result = customer_agent.invoke(customer_state)

    # Map back to MainState updates
    # CRITICAL: MainState uses "final_context" (with operator.add), not "final_evidence"
    return {
        "final_answer": result.get("final_answer", ""),
        "final_context": result.get(
            "final_evidence", []
        ),  # Map final_evidence → final_context
        "route": result.get("route", "synthesis_agent"),
    }


# =============================================================================
# AGENT INSTANCES
# =============================================================================

# Initialize agent instances once for reuse
# These instances can be used directly as LangGraph nodes since they implement invoke()
router_agent = RouterAgent()
customer_agent = CustomerAgent()
knowledge_agent = KnowledgeAgent()
synthesis_agent = SynthesisAgent()


# =============================================================================
# ROUTING LOGIC - Conditional edge function
# =============================================================================


def main_router_logic(state: MainState) -> str:
    """
    Main routing logic - determines next node based on router decision.

    This function reads the 'route' field from state (set by RouterAgent)
    and directs the graph flow to the appropriate specialist agent.

    Args:
        state: Current main state with route field

    Returns:
        str: Name of next node to execute

    Routing Rules:
        - "knowledge_agent" → knowledge_agent
        - "customer_agent" → customer_agent
        - "synthesis_agent" → synthesis_agent
    """
    route = state.get("route", "synthesis_agent")
    logger.info(f"--- MAIN GRAPH: Routing to {route} ---")

    # Route names match node names directly now
    return route


# =============================================================================
# GRAPH CONSTRUCTION - Build and compile the main orchestration graph
# =============================================================================


def build_main_graph() -> StateGraph:
    """
    Build and compile the main orchestration graph.

    Graph Structure:
        Entry → Router → Conditional Route:
            ├─→ Knowledge → Conditional (back to Router OR go to Synthesis)
            ├─→ Customer → Conditional (back to Router OR go to Synthesis)
            └─→ Synthesis → END

    Returns:
        StateGraph: Compiled graph ready for execution
    """
    logger.info("Building main orchestration graph...")

    # Initialize graph builder with MainState schema
    builder = StateGraph(MainState)

    # Add nodes using wrapper functions for state mapping
    builder.add_node("router_agent", router_agent.invoke)
    builder.add_node("knowledge_agent", knowledge_node)  # Wrapper for state mapping
    builder.add_node("customer_agent", customer_node)  # Wrapper for state mapping
    builder.add_node("synthesis_agent", synthesis_agent.invoke)

    # Set entry point
    builder.set_entry_point("router_agent")

    # Add conditional routing from router
    # Router can ONLY route to specialist agents, never directly to synthesis
    builder.add_conditional_edges(
        "router_agent",
        main_router_logic,
        {"knowledge_agent": "knowledge_agent", "customer_agent": "customer_agent"},
    )

    # CRITICAL FIX: Agents can now signal completion by setting route="synthesis_agent"
    # Add conditional edges from specialist agents (not fixed loops!)
    def after_specialist_logic(state: MainState) -> str:
        """
        Decide what to do after a specialist agent completes.

        If the specialist agent set route="synthesis_agent", go there.
        Otherwise, loop back to router for re-evaluation.
        """
        route = state.get("route", "router_agent")
        if route == "synthesis_agent":
            logger.info("Specialist signaled completion → routing to synthesis")
            return "synthesis_agent"
        else:
            logger.info("Specialist needs more work → routing back to router")
            return "router_agent"

    builder.add_conditional_edges(
        "knowledge_agent",
        after_specialist_logic,
        {"router_agent": "router_agent", "synthesis_agent": "synthesis_agent"},
    )

    builder.add_conditional_edges(
        "customer_agent",
        after_specialist_logic,
        {"router_agent": "router_agent", "synthesis_agent": "synthesis_agent"},
    )

    # Add terminal edge (synthesis is always the final step)
    builder.add_edge("synthesis_agent", END)

    # Compile the graph
    logger.info("Compiling main graph...")
    compiled_graph = builder.compile()
    logger.info("✓ Main graph compiled successfully")

    return compiled_graph


# Build the graph once on module import
app_graph = build_main_graph()
