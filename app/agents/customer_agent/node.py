"""
Customer Agent Sub-Graph Builder

This file builds and compiles the "Customer Department"
as a self-contained StateGraph ("mini-factory").

This is a simple ReAct loop (no QC).
"""
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import AIMessage

from .state import CustomerState
from .prompts import CUSTOMER_AGENT_PROMPT
from app.agents.customer_agent.tools import customer_agent_tools


# --- The Single "Worker" Node ---
def run_investigator(state: CustomerState) -> dict:
    """
    This is the main "ReAct" (Reason + Act) node.
    It runs the agent executor to call tools and get the final answer.
    """
    LLM = ChatOpenAI(model="gpt-4o", temperature=0)
    CUSTOMER_AGENT_RUNNABLE = create_agent(
    model=LLM, 
    tools=customer_agent_tools, 
    system_prompt=CUSTOMER_AGENT_PROMPT
)
    
    # Get inputs from the state
    question = state["original_question"]
    user_id = state["user_id"]
    messages = state["messages"] 
    
    # Invoke the agent
    result = CUSTOMER_AGENT_RUNNABLE.invoke({
        "original_question": question,
        "user_id": user_id,
        "messages": messages,
    })
    
    # Extract evidence (the raw tool outputs)
    evidence = []
    if "intermediate_steps" in result:
        for step in result["intermediate_steps"]:
            evidence.append(str(step[1])) # step[1] is the tool output
    
    # Return the "report" for the "CEO" (MainGraph)
    return {
        "final_answer": result["output"],
        "final_evidence": evidence
    }

# --- Define the Sub-Graph ---
def build_customer_graph() -> StateGraph:
    """
    Builds the complete, compiled "Customer Department" sub-graph.
    """
    builder = StateGraph(CustomerState)

    # 1. Add the "Stations" (Nodes)
    builder.add_node("investigate", run_investigator)

    # 2. Add the "Conveyor Belts" (Edges)
    builder.set_entry_point("investigate")
    
    # This simple agent just runs once and finishes
    builder.add_edge("investigate", END)

    # 3. Compile the "Mini-Factory"
    customer_graph = builder.compile()
    return customer_graph

# We compile it once here so the Main Graph ("CEO") can import it
customer_graph = build_customer_graph()