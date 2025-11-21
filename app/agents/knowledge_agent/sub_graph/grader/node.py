"""
Grader Node Implementation

This node inspects the draft from the Investigator and manages retry logic.

Key Changes (Architecture Simplification):
- Manages internal retry counter (via message history analysis)
- Returns 'accept', 'reject', or 'escalate' decision
- Critique goes directly to messages (no intermediate state)
- Resets retry count on acceptance
"""
import logging

from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from .prompt import GRADER_PROMPT
from .schema import Grade
from app.agents.knowledge_agent.state import KnowledgeState

logger = logging.getLogger(__name__)

# Retry limit: max rejections before human escalation
RETRY_LIMIT = 2  # 3 total attempts (1 initial + 2 retries)


def run_grader(state: KnowledgeState) -> dict:
    """
    QC Inspector with internal retry management.

    Logic:
    1. Counts rejection attempts (via "QC Feedback" markers in messages)
    2. Evaluates draft answer quality
    3. Returns decision:
       - "accept": Draft approved, proceed to accept node
       - "reject": Draft rejected, send critique to investigator for retry
       - "escalate": Max retries reached, escalate to human via Slack

    Args:
        state (KnowledgeState): Current state with draft_answer and context

    Returns:
        dict: Updated state with grade_decision and messages
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    grader_llm = llm.with_structured_output(Grade)

    # Count previous rejections (retry attempts)
    messages = state.get("messages", [])
    retry_count = sum(
        1
        for msg in messages
        if isinstance(msg, HumanMessage) and "QC Feedback:" in msg.content
    )

    logger.info(f"--- GRADER: Current retry count: {retry_count}/{RETRY_LIMIT} ---")

    # Get inputs from state
    question = state["original_question"]
    context = state.get("context", [])
    draft = state.get("draft_answer", "")

    # Invoke QC evaluation
    grade: Grade = grader_llm.invoke(
        GRADER_PROMPT.format_messages(
            original_question=question, context=context, draft_answer=draft
        )
    )

    logger.info(f"--- GRADER: Decision = {grade.grade} ---")

    # Decision logic based on grade and retry count
    if grade.grade == "accept":
        logger.info("--- GRADER: Draft ACCEPTED ---")

        # Format evidence (moved from accept node)
        final_evidence = _format_evidence(state)

        return {
            "grade_decision": "accept",
            "final_answer": state["draft_answer"],
            "final_evidence": final_evidence,
            "messages": [AIMessage(content="QC approved. Answer finalized.")],
        }

    # Draft rejected - check if we should retry or escalate
    elif retry_count >= RETRY_LIMIT:
        logger.warning(
            f"--- GRADER: Max retries ({RETRY_LIMIT}) reached. Escalating to human. ---"
        )
        return {
            "grade_decision": "escalate",
            "messages": [
                AIMessage(
                    content=f"QC failed after {retry_count + 1} attempts. Escalating to human support."
                )
            ],
        }

    else:
        # Reject with feedback for retry
        logger.info(
            f"--- GRADER: Draft REJECTED (attempt {retry_count + 1}/{RETRY_LIMIT + 1}) ---"
        )
        logger.debug(f"Critique: {grade.critique}")

        return {
            "grade_decision": "reject",
            "messages": [HumanMessage(content=f"QC Feedback: {grade.critique}")],
        }


def _format_evidence(state: KnowledgeState) -> list:
    """
    Format context into structured evidence format.

    Helper function moved from accept node to keep all finalization
    logic in grader (Single Responsibility Principle).

    Args:
        state (KnowledgeState): Current state with context and tools_called

    Returns:
        list: Structured evidence dictionaries
    """
    tools_called = state.get("tools_called", [])
    context = state.get("context", [])

    structured_evidence = [
        {"source": "knowledge_agent", "tools_called": tools_called, "content": ctx}
        for ctx in context
    ]

    logger.info(
        f"KnowledgeAgent: Formatted {len(structured_evidence)} evidence items (tools: {tools_called})"
    )

    return structured_evidence
