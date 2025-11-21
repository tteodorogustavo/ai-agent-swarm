"""Mock tests for Knowledge Agent tools.

NOTE: These tests are deprecated in favor of integration tests.
The actual tool implementations are tested in:
- tests/tools/test_tools_integration_real.py (real integration tests)
- tests/agents/knowledge_agent/test_knowledge_graph.py (graph-level tests)

Keeping this file for backwards compatibility but tests may be removed in future.
"""
import pytest

pytestmark = pytest.mark.skip(reason="Deprecated - use integration tests instead")
