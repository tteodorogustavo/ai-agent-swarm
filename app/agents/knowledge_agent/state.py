"""
Defines the Internal State for the Knowledge Department Sub-Graph.

This is the "Departmental Clipboard" for the Knowledge Agent.
It manages the complex, internal loop of RAG, Grading, and Rewriting.

This state is completely "black-boxed" from the Main Graph.
"""
from typing import Annotated
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from app.agents.main_state import MainState


class KnowledgeState(MainState):
    """
    The internal state for the self-correcting RAG sub-graph.

    Inherits common fields from `MainState`. Adds knowledge-department specific
    loop state and quality-control fields.
    """

    # --- 2. Internal Memory & Loop ---
    context: Annotated[
        List[str],
        'The internal "Evidence Box" (RAG chunks, web results) for the current loop.',
    ]

    tools_called: Annotated[
        List[str],
        "List of tool names that were actually invoked (e.g., ['rag_tool', 'web_search_tool']).",
    ]

    # --- 3. Quality Control (QC) Loop ---
    draft_answer: Annotated[
        Optional[str], "The working 'draft' response ready for grading."
    ]

    # Temporary field for conditional routing (set by Grader, consumed by graph logic)
    grade_decision: Annotated[
        Optional[str],
        "Grader's decision: 'accept', 'reject', or 'escalate'. Used only for conditional edges.",
    ]

    # --- 4. Final Output ---
    final_evidence: Annotated[
        List[Dict[str, Any]],
        "The *final, approved* structured evidence that will be returned to the Main Graph.",
    ]
    final_answer: Annotated[
        Optional[str],
        "The *final, approved* draft answer to be returned to the Main Graph.",
    ]
