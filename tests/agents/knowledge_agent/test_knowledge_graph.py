"""
Unit Tests for the Knowledge Agent Sub-Graph Logic.

This file specifically tests the "brain" of our Quality Control (QC) loop:
the conditional logic (`should_continue`) that decides where to route
the workflow based on the Grader's decision.

Updated for simplified architecture (no rewriter node, Grader manages retries).
"""
from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage

from app.agents.knowledge_agent.agent import KnowledgeAgent
from app.agents.knowledge_agent.state import KnowledgeState
# The "Departmental Clipboard" (State) we need to fake
# The "Conditional Logic" (Method) we are testing

# Create instance to access _should_continue method
_agent = KnowledgeAgent()  # --- Test Case 1: The "Happy Path" (Grade is Accepted) ---


def test_should_continue_accept():
    """
    Tests if the logic correctly routes to 'accept' when Grader approves draft.

    Scenario: Grader sets grade_decision="accept"
    Expected: Route to "accept" node
    """
    state = KnowledgeState(
        grade_decision="accept",
        original_question="Test question",
        messages=[AIMessage(content="QC approved. Answer finalized.")],
        context=[],
        tools_called=[],
        draft_answer="Test answer",
        final_evidence=[],
        final_answer="",
        user_id="test_user",
        route="knowledge",
        router_calls=0,
        final_context=[],
    )

    result = _agent._should_continue(state)

    assert result == "accept"


# --- Test Case 2: The "Rejection & Retry" Path ---


def test_should_continue_reject_and_retry():
    """
    Tests if the logic correctly routes back to 'investigate' when rejected.

    Scenario: Grader sets grade_decision="reject" (under retry limit)
    Expected: Route to "investigate" node for retry
    """
    state = KnowledgeState(
        grade_decision="reject",
        original_question="Test question",
        messages=[HumanMessage(content="QC Feedback: Needs more evidence")],
        context=[],
        tools_called=[],
        draft_answer="Incomplete answer",
        final_evidence=[],
        final_answer="",
        user_id="test_user",
        route="knowledge",
        router_calls=0,
        final_context=[],
    )

    result = _agent._should_continue(state)

    assert result == "investigate"


# --- Test Case 3: The "Human Escalation" Path ---


def test_should_continue_escalate():
    """
    Tests if the logic correctly routes to human escalation after max retries.

    Scenario: Grader sets grade_decision="escalate" (max retries reached)
    Expected: Route to "human_escalation" node for Slack notification
    """
    state = KnowledgeState(
        grade_decision="escalate",
        original_question="Complex question requiring expert",
        messages=[
            HumanMessage(content="QC Feedback: Missing key information"),
            HumanMessage(content="QC Feedback: Still incomplete"),
            AIMessage(
                content="QC failed after 3 attempts. Escalating to human support."
            ),
        ],
        context=[],
        tools_called=["rag_tool", "web_search_tool"],
        draft_answer="Best effort answer",
        final_evidence=[],
        final_answer="",
        user_id="test_user_123",
        route="knowledge",
        router_calls=0,
        final_context=[],
    )

    result = _agent._should_continue(state)

    assert result == "human_escalation"


# --- Test Case 4: Default behavior (missing grade_decision) ---


def test_should_continue_default_to_investigate():
    """
    Tests if the logic defaults to 'investigate' when grade_decision is missing.

    Scenario: grade_decision not set in state
    Expected: Default to "investigate" (safe retry behavior)
    """
    state = KnowledgeState(
        # grade_decision deliberately omitted
        original_question="Test question",
        messages=[],
        context=[],
        tools_called=[],
        draft_answer="",
        final_evidence=[],
        final_answer="",
        user_id="test_user",
        route="knowledge",
        router_calls=0,
        final_context=[],
    )

    result = _agent._should_continue(state)

    assert result == "investigate"  # Default to retry
