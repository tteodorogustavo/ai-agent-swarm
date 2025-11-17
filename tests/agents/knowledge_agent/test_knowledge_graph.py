"""
Unit Tests for the Knowledge Agent Sub-Graph Logic.

This file specifically tests the "brain" of our Quality Control (QC) loop:
the conditional logic (`should_loop`) that decides where to route
the workflow based on the Grader's output.
"""
import pytest

# The "Departmental Clipboard" (State) we need to fake
from app.agents.knowledge_agent.state import KnowledgeState

# The "Conditional Logic" (Function) we are testing
from app.agents.knowledge_agent.graph import should_loop

# --- Test Case 1: The "Happy Path" (Grade is Accepted) ---

def test_should_loop_accept():
    """
    Tests if the logic correctly routes to 'accept' when the grade is good.
    """
    # 1. Arrange: Create a "fake" clipboard (state)
    # We only need to fill the fields the function *reads*
    state = KnowledgeState(
        latest_grade="accept",
        rewrite_attempts=0,
        # The other fields don't matter for this test
        original_question="", messages=[], query_analysis=None,
        context=[], draft_answer="", latest_critique="",
        final_evidence=[], final_answer=""
    )
    
    # 2. Act: Run the function
    result = should_loop(state)
    
    # 3. Assert: Check the result
    assert result == "accept"

# --- Test Case 2: The "Failure & Retry" Path ---

def test_should_loop_reject_and_retry():
    """
    Tests if the logic correctly routes to 'rewrite' when the grade is bad
    BUT we are still under the attempt limit.
    """
    # 1. Arrange: Create a state that failed once (1 attempt)
    state = KnowledgeState(
        latest_grade="reject",
        rewrite_attempts=1, # We've already tried once
        original_question="", messages=[], query_analysis=None,
        context=[], draft_answer="", latest_critique="Test critique",
        final_evidence=[], final_answer=""
    )
    
    # 2. Act
    result = should_loop(state)
    
    # 3. Assert
    assert result == "rewrite"

# --- Test Case 3: The "Circuit Breaker" Path (Too many failures) ---

@pytest.mark.parametrize("attempts", [2, 3, 100])
def test_should_loop_reject_and_fallback(attempts):
    """
    Tests if the logic correctly routes to 'fallback' (the safety net)
    when the grade is bad AND we have hit our retry limit (>= 2).
    """
    # 1. Arrange: Create a state that has failed too many times
    state = KnowledgeState(
        latest_grade="reject",
        rewrite_attempts=attempts, # Test multiple failure counts
        original_question="", messages=[], query_analysis=None,
        context=[], draft_answer="", latest_critique="Test critique",
        final_evidence=[], final_answer=""
    )
    
    # 2. Act
    result = should_loop(state)
    
    # 3. Assert
    assert result == "fallback"