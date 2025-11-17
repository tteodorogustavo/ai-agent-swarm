"""
This module is responsible for constructing the agent system structure according to LangGraph concepts.
It defines and organizes the components, relationships, and workflows that enable agent-based interactions,
ensuring modularity, scalability, and clear communication between agents within the system.
"""

"""
The Main Graph Builder (The "CEO" / "Chief Architect")

This file assembles the "MainGraph" (Agent 1: The Orchestrator).
It does not contain any agent logic itself.
Instead, it *imports* all the compiled Sub-Graphs (the "Departments")
and connects them together.

This implements our "CERTO" (correct) architecture:
A Hierarchical, Looping, Sub-Graph Orchestrator.
"""

import logging
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, BaseMessage

# Import the "Master Clipboard"
from app.graph.main_state import MainState

# --- 1. Import all "Departments" (Compiled Sub-Graphs) ---
# We import the *compiled graph* from each department's .graph file.
from app.agents.router_agent.graph import router_graph
from app.agents.knowledge_agent.graph import knowledge_graph
from app.agents.customer_agent.graph import customer_graph
from app.agents.synthesis_agent.graph import synthesis_graph


# --- 2. Define the "Wrapper Nodes" ---
# These nodes are the "Directors" that know how to "invoke" (call)
# the "Departments" (Sub-Graphs) and map their I/O to the MainState.

def router_node(state: MainState) -> dict:
    """
    The "Super-Manager" node (Agent 1: The Brain).
    This node calls the RouterAgent Sub-Graph.
    
    Input: MainState.messages
    Output (writes to MainState): route, query_analysis
    """
    logging.info("--- MAIN GRAPH: Calling Router (Sub-Graph) ---")
    
    # 1. Prepare the *input* for the Router Sub-Graph
    # It only needs the main message history
    sub_graph_input = {"messages": state["messages"]}
    
    # 2. Invoke the Sub-Graph
    # This runs the Router's internal graph (which fills RouterDecision)
    sub_graph_output = router_graph.invoke(sub_graph_input)
    
    # 3. Return the *updates* for the MainState (the "Master Clipboard")
    # We add its final_answer (its "log") to our main memory
    return {
        "route": sub_graph_output["route"],
        "query_analysis": sub_graph_output["query_analysis"],
        "messages": [AIMessage(content=sub_graph_output["final_answer"])]
    }

def knowledge_node(state: MainState) -> dict:
    """
    The "Knowledge Department" node.
    This node calls the KnowledgeAgent Sub-Graph (the QC loop).
    
    Input: MainState.messages, MainState.query_analysis
    Output (writes to MainState): final_context
    """
    logging.info("--- MAIN GRAPH: Calling Knowledge Dept (Sub-Graph) ---")
    
    # 1. Prepare the *input* for the Knowledge Sub-Graph
    sub_graph_input = {
        "original_question": state["messages"][-1].content,
        "query_analysis": state["query_analysis"],
        "rewrite_attempts": 0 # Always start the QC loop counter at 0
    }
    
    # 2. Invoke the Sub-Graph (This runs the entire QC loop)
    sub_graph_output = knowledge_graph.invoke(sub_graph_input)
    
    # 3. Return the *updates* for the MainState
    return {
        "final_context": sub_graph_output["final_evidence"],
        "messages": [AIMessage(content=sub_graph_output["final_answer"])]
    }

def customer_node(state: MainState) -> dict:
    """
    The "Customer Department" node.
    This node calls the CustomerAgent Sub-Graph (the ReAct loop).
    
    Input: MainState.user_id, MainState.messages
    Output (writes to MainState): final_context
    """
    logging.info("--- MAIN GRAPH: Calling Customer Dept (Sub-Graph) ---")
    
    # 1. Prepare the *input* for the Customer Sub-Graph
    sub_graph_input = {
        "original_question": state["messages"][-1].content,
        "user_id": state["user_id"],
        "messages": [] # Give it a clean internal memory for its ReAct loop
    }
    
    # 2. Invoke the Sub-Graph
    sub_graph_output = customer_graph.invoke(sub_graph_input)

    # 3. Return the *updates* for the MainState
    return {
        "final_context": sub_graph_output["final_evidence"],
        "messages": [AIMessage(content=sub_graph_output["final_answer"])]
    }

def synthesis_node(state: MainState) -> dict:
    """
    The "Spokesperson" node.
    This node calls the SynthesisAgent Sub-Graph.
    
    Input: MainState.messages, MainState.final_context
    Output (writes to MainState): final_response
    """
    logging.info("--- MAIN GRAPH: Calling Synthesis Dept (Sub-Graph) ---")
    
    # 1. Prepare the *input* for the Synthesis Sub-Graph
    sub_graph_input = {
        "messages": state["messages"],
        "context": state["final_context"]
    }
    
    # 2. Invoke the Sub-Graph
    sub_graph_output = synthesis_graph.invoke(sub_graph_input)

    # 3. Return the *final* updates for the MainState
    # This is the end of the line.
    return {
        "final_response": sub_graph_output["final_answer"],
        "messages": [AIMessage(content=sub_graph_output["final_answer"])]
    }

# --- 3. Define the "Conditional Edge" (The "Esteira") ---

def main_router_logic(state: MainState) -> str:
    """
    This is the "brain" of the CEO. It reads the `route`
    from the "Master Clipboard" (MainState) and tells the
    graph which "Department" to go to next.
    """
    logging.info(f"--- MAIN GRAPH: Routing. Decision: {state['route']} ---")
    return state["route"] # The route is a string: "knowledge_department", etc.


# --- 4. Build the Graph (The "Factory Assembly") ---

# Initialize the "Factory" with the "Master Clipboard"
builder = StateGraph(MainState)

# 1. Add all the "Stations" (The Departments + The CEO's Brain)
builder.add_node("router_node", router_node)
builder.add_node("knowledge_department", knowledge_node)
builder.add_node("customer_department", customer_node)
builder.add_node("synthesis_node", synthesis_node)

# 2. Define the Entry Point
builder.set_entry_point("router_node")

# 3. Define the "Conditional Conveyor Belt"
builder.add_conditional_edges(
    "router_node",      # The "Esteira" *starts* at the Router
    main_router_logic,  # It *uses* this function to read the 'route'
    {
        # This is the "map"
        "knowledge_department": "knowledge_department",
        "customer_department": "customer_department",
        "synthesis_node": "synthesis_node"
    }
)

# 4. Define the "Loops" (The "CERTO" part)
# After a "worker" finishes, it goes BACK to the "Gerente" (Router)
# to re-evaluate the plan.
builder.add_edge("knowledge_department", "router_node")
builder.add_edge("customer_department", "router_node")

# 5. Define the "Exit"
# Only the "Spokesperson" (Synthesis) can end the process.
builder.add_edge("synthesis_node", END)

# 6. Compile the "Factory"
logging.info("Compiling the MainGraph...")
app_graph = builder.compile()
logging.info("MainGraph compiled successfully.")