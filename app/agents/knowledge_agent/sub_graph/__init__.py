"""
Knowledge Agent Sub-Graph

This package contains the modularized sub-graph nodes for the Knowledge Agent,
following the same organizational pattern as the main agents.

Each node (Investigator, Grader, Human Escalation) is implemented
in its own subdirectory with separated concerns (node.py, prompt.py, schema.py).

Architecture Changes (Simplified):
- Removed: Rewriter node (redundant - Grader handles retry logic)
- Removed: Accept and Fallback nodes (trivial - Grader formats final evidence on accept)
- Added: Human Escalation node (Slack notification for human-in-the-loop)
"""
from .grader import Grade
from .grader import GRADER_PROMPT
from .grader import run_grader
from .human_escalation import run_human_escalation
from .investigator import INVESTIGATOR_PROMPT
from .investigator import run_investigator

__all__ = [
    "run_investigator",
    "INVESTIGATOR_PROMPT",
    "run_grader",
    "GRADER_PROMPT",
    "Grade",
    "run_human_escalation",
]
