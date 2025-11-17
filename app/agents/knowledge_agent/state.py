"""
Defines the Internal State for the Knowledge Department Sub-Graph.

This is the "Departmental Clipboard" for the Knowledge Agent.
It manages the complex, internal loop of RAG, Grading, and Rewriting.

This state is completely "black-boxed" from the Main Graph.
"""

from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import BaseMessage
import operator

from app.agents.knowledge_agent.query_schema import QueryAnalysis

class KnowledgeState(TypedDict):
    """
    The internal state for the self-correcting RAG sub-graph.
    """
    
    # --- 1. Inputs from "CEO" ---
    original_question: Annotated[str, "The raw user question passed in from the Main Graph."]

    # --- 2. Internal Memory & Loop ---
    messages: Annotated[List[BaseMessage], operator.add, "The *internal* memory for this sub-graph." \
    " Used by the Rewriter to pass critiques back to the Knowledge node."]

    query_analysis: Annotated[Optional[QueryAnalysis],
                              "The \"RAG Analysis Form\" (keywords, hyde, etc.) filled by this department's internal router."]
    
    context: Annotated[List[str], "The internal \"Evidence Box\" (RAG chunks, web results) for the current loop."]

    # --- 3. Quality Control (QC) Loop ---
    draft_answer: Annotated[str, "The working 'draft' response ready for grading."]
    """The working 'draft' response ready for grading."""
    
    latest_grade: Annotated[str, "The \"QC Stamp\" from the Grader (e.g., \"accept\", \"reject\")."]
    
    latest_critique: Annotated[str, "The 'QC Notes' (critique) explaining a rejection."]

    rewrite_attempts: Annotated[int, "The \"circuit breaker\" counter to prevent infinite loops."]

    # --- 4. Final Output to "CEO" ---
    final_evidence: Annotated[List[str], "The *final, approved* evidence that will be returned to the Main Graph."]
    
    final_answer: Annotated[str, "The *final, approved* draft answer to be returned to the Main Graph."]