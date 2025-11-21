"""
Human Escalation Module

Exports the human escalation node for handling cases where automated
responses fail after maximum retry attempts.
"""
from .node import run_human_escalation

__all__ = ["run_human_escalation"]
