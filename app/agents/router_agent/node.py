from graph.main_state import MainState
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
import logging
from app.models.router_response import RouterResponse
from .prompt import ROUTER_PROMPT
from ..agents import agents


def router_node(state: "MainState") -> dict:
    """
    The main router function.
    This node calls an LLM to fill the `RouterDecision` schema.
    It does *not* enrich the query (e.g., HyDE); it *only* routes.
    """
    logging.info("--- MainGraph: Calling Router (Triage Manager) ---")
    
    # 1. Initialize the "CERTO" LLM (light & fast model)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    structured_llm = llm.with_structured_output(RouterResponse)
    
    # 2. Get the input from the MainState
    messages = state["messages"]
    latest_question = messages[-1].content
    agents_list = "\n".join([f"- `{agent.name}`: {agent.description}" for agent in agents.values()])
    
    # 3. Invoke the "Triage Manager"
    decision: RouterResponse = structured_llm.invoke(
        ROUTER_PROMPT.format_messages(
            messages=messages,
            latest_question=latest_question,
            agents_list=agents_list
        )
    )
    
    logging.info(f"Router Decision: Route='{decision.route}'")
    
    # 4. Return the updates for the "Master Clipboard" (MainState)
    return {
        "route": decision.route,
        "messages": [AIMessage(content=f"[Router Log: Decision made. Routing to: {decision.route}]")]
    }