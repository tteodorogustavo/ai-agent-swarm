"""
Knowledge Agent Sub-Graph Builder

This file builds and compiles the "Knowledge Department"
as a self-contained, self-correcting StateGraph ("mini-factory").
"""
from langgraph.graph import StateGraph, END
from .state import KnowledgeState
from .nodes import (
    run_investigator, 
    run_grader, 
    run_rewriter, 
    run_fallback,
    run_accept
)

# --- QC Loop Conditional Edge ---

def should_loop(state: KnowledgeState) -> str:
    """
    This is the "QC Check" (the conditional branch).
    It reads the 'Prancheta' (state) and decides the next station.
    """
    grade = state["latest_grade"]
    attempts = state["rewrite_attempts"]
    
    # Set the retry limit
    RETRY_LIMIT = 2 # 1 initial attempt + 2 rewrites = 3 total attempts

    if grade == "accept":
        # 1. "Approved!" -> Go to the "accept" node
        return "accept"
    
    if attempts >= RETRY_LIMIT:
        # 2. "Rejected 3x!" -> Go to Fallback
        return "fallback"
    
    # 3. "Rejected" (but < 3 attempts) -> Go to Rewriter
    return "rewrite"

# --- Define the Sub-Graph ---

def build_knowledge_graph() -> StateGraph:
    """
    Builds the complete, compiled "Knowledge Department" sub-graph.
    """
    builder = StateGraph(KnowledgeState)

    # 1. Add the "Stations" (Nodes)
    builder.add_node("investigate", run_investigator)
    builder.add_node("grade", run_grader)
    builder.add_node("rewrite", run_rewriter)
    builder.add_node("fallback", run_fallback)
    builder.add_node("accept", run_accept)

    # 2. Add the "Conveyor Belts" (Edges)
    builder.set_entry_point("investigate")
    
    # The Investigator always sends his draft to the Grader
    builder.add_edge("investigate", "grade")
    
    # The Grader is the conditional junction
    builder.add_conditional_edges(
        "grade",          # Start from the 'grade' station
        should_loop,      # Use our QC function to decide
        {
            "accept": "accept",              # "Approved"
            "rewrite": "rewrite",            # "Rejected, < 2 attempts"
            "fallback": "fallback"           # "Rejected 2x"
        }
    )
    
    # The Rewriter *loops back* to the Investigator
    builder.add_edge("rewrite", "investigate")
    
    # The Fallback and Accept nodes end the graph
    builder.add_edge("fallback", END)
    builder.add_edge("accept", END)

    # 3. Compile the "Mini-Factory"
    knowledge_graph = builder.compile()
    return knowledge_graph

# We compile it once here so the Main Graph ("CEO") can import it
knowledge_graph = build_knowledge_graph()