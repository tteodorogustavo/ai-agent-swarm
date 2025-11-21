"""
Investigator Agent for Knowledge Sub-Graph

This module exports the Investigator node, which is responsible for gathering
evidence and formulating draft answers using RAG and Web Search tools.
"""
from .node import run_investigator
from .prompt import INVESTIGATOR_PROMPT

__all__ = ["run_investigator", "INVESTIGATOR_PROMPT"]
