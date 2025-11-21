"""
Defines the Internal State for the Customer Department Sub-Graph.

This is the "Departmental Clipboard" for the Customer Agent.
Its job is to orchestrate tool calls to fetch private user data.
"""
from typing import Annotated
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from app.agents.main_state import MainState


class CustomerState(MainState):
    """
    The internal state for the customer tool-calling sub-graph.

    Inherits common fields from `MainState`. Adds department-specific
    transient scratchpad and structured evidence that will be deposited into
    `MainState.final_context` for the Synthesis Agent to use.
    """

    # Transient ReAct scratchpad for the CURRENT iteration; cleared after turn.
    agent_scratchpad: Annotated[
        List[Any],
        "Transient ReAct scratchpad for the current iteration; cleared after turn.",
    ]

    # `final_answer` is the factual, structured report produced by this department
    # (this is what will be consumed by the Synthesis Agent). Keep optional
    # because not every run produces a final answer.
    final_answer: Annotated[
        Optional[str],
        "Final structured answer (report) to be passed to MainGraph / Synthesis Agent.",
    ] = None

    # `final_evidence` should be structured objects (dicts) containing raw
    # tool outputs, metadata and optional citations — not plain strings.
    # The CustomerAgent is expected to append these objects into
    # `MainState.final_context` at the end of its run.
    final_evidence: Annotated[
        List[Dict[str, Any]],
        "Structured evidence (tool outputs) produced by CustomerAgent.",
    ]
