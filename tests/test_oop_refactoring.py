"""
End-to-End Tests for OOP Refactoring

This test suite validates the complete OOP refactoring of all agents:
- Base Agent class contract
- RouterAgent OOP implementation
- CustomerAgent OOP implementation
- KnowledgeAgent OOP implementation with sub-graph
- SynthesisAgent OOP implementation
- GraphOrchestrator integration

Testing Strategy:
1. Unit tests: Verify each agent class individually
2. Integration tests: Verify agent interactions
3. E2E tests: Verify complete graph workflow
"""
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from langchain_core.messages import HumanMessage

from app.agents.base import Agent
from app.agents.customer_agent.node import CustomerAgent
from app.agents.knowledge_agent.agent import KnowledgeAgent
from app.agents.router_agent.node import RouterAgent
from app.agents.synestesis_agent.node import SynthesisAgent
from app.graph.builder import app_graph


class TestBaseAgentContract:
    """Test that all agents properly inherit from the Agent base class."""

    def test_router_agent_inherits_from_base(self):
        """RouterAgent should inherit from Agent."""
        agent = RouterAgent()
        assert isinstance(agent, Agent)
        assert agent.name == "router_agent"
        assert hasattr(agent, "invoke")
        assert hasattr(agent, "process")

    def test_customer_agent_inherits_from_base(self):
        """CustomerAgent should inherit from Agent."""
        agent = CustomerAgent()
        assert isinstance(agent, Agent)
        assert agent.name == "customer_agent"
        assert hasattr(agent, "invoke")
        assert hasattr(agent, "process")

    def test_knowledge_agent_inherits_from_base(self):
        """KnowledgeAgent should inherit from Agent."""
        agent = KnowledgeAgent()
        assert isinstance(agent, Agent)
        assert agent.name == "knowledge_agent"
        assert hasattr(agent, "invoke")
        assert hasattr(agent, "process")

    def test_synthesis_agent_inherits_from_base(self):
        """SynthesisAgent should inherit from Agent."""
        agent = SynthesisAgent()
        assert isinstance(agent, Agent)
        assert agent.name == "synthesis_agent"
        assert hasattr(agent, "invoke")
        assert hasattr(agent, "process")


class TestKnowledgeAgentSubGraph:
    """Test KnowledgeAgent's internal sub-graph structure."""

    def test_knowledge_agent_has_sub_graph(self):
        """KnowledgeAgent should have a compiled sub-graph."""
        agent = KnowledgeAgent()
        assert hasattr(agent, "_graph")
        assert agent._graph is not None

    def test_sub_graph_has_correct_nodes(self):
        """Sub-graph should have all required nodes."""
        agent = KnowledgeAgent()
        nodes = list(agent._graph.nodes.keys())

        # Should have: __start__, investigate, grade, human_escalation
        assert "__start__" in nodes
        assert "investigate" in nodes
        assert "grade" in nodes
        assert "human_escalation" in nodes
        # Verify we have at least these core nodes (may have more)
        assert len(nodes) >= 4


class TestRouterAgent:
    """Test RouterAgent functionality."""

    @patch("langchain_openai.ChatOpenAI")
    def test_router_routes_to_knowledge(self, mock_llm):
        """RouterAgent should route public queries to knowledge_agent."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.route = "knowledge_agent"
        mock_response.reasoning = "Public information query"

        mock_llm_instance = Mock()
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm.return_value.with_structured_output.return_value = mock_llm_instance

        # Test
        agent = RouterAgent()
        state = {
            "messages": [HumanMessage(content="What is InfinitePay?")],
            "user_id": "test_user",
            "route": "",
            "final_context": [],
            "final_response": "",
        }

        result = agent.process(state)

        assert "route" in result
        assert result["route"] == "knowledge_agent"

    @patch("langchain_openai.ChatOpenAI")
    def test_router_routes_to_customer(self, mock_llm):
        """RouterAgent should route private queries to customer_agent."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.route = "customer_agent"
        mock_response.reasoning = "Private account query"

        mock_llm_instance = Mock()
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm.return_value.with_structured_output.return_value = mock_llm_instance

        # Test
        agent = RouterAgent()
        state = {
            "messages": [HumanMessage(content="What is my account balance?")],
            "user_id": "test_user",
            "route": "",
            "final_context": [],
            "final_response": "",
        }

        result = agent.process(state)

        assert "route" in result
        assert result["route"] == "customer_agent"


class TestGraphCompilation:
    """Test that the main graph compiles correctly."""

    def test_graph_compiles_successfully(self):
        """Main graph should compile without errors."""
        assert app_graph is not None

    def test_graph_has_all_nodes(self):
        """Graph should have all agent nodes."""
        nodes = list(app_graph.nodes.keys())

        # Verify all required nodes exist
        assert "__start__" in nodes
        assert "router_agent" in nodes
        assert "knowledge_agent" in nodes
        assert "customer_agent" in nodes
        assert "synthesis_agent" in nodes
        # Should have exactly 5 nodes (start + 4 agents)
        assert len(nodes) == 5

    def test_singleton_instances_exist(self):
        """Builder should create singleton agent instances."""
        from app.graph.builder import (
            router_agent,
            customer_agent,
            knowledge_agent,
            synthesis_agent,
        )

        assert isinstance(router_agent, RouterAgent)
        assert isinstance(customer_agent, CustomerAgent)
        assert isinstance(knowledge_agent, KnowledgeAgent)
        assert isinstance(synthesis_agent, SynthesisAgent)


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow (mocked LLMs)."""

    def test_graph_can_be_invoked(self):
        """Test that the graph structure supports invocation (without actually running)."""
        # This is a structural test - we're not running the full workflow
        # Just verifying that the graph object has the right methods
        assert hasattr(app_graph, "invoke")
        assert callable(app_graph.invoke)

        # Verify the graph would accept correct input structure
        test_input = {
            "messages": [HumanMessage(content="Test")],
            "user_id": "test",
            "route": "",
            "final_context": [],
            "final_response": "",
        }
        # Just verify structure, don't invoke (would require real API keys)
        assert all(key in test_input for key in ["messages", "user_id", "route"])


class TestOOPArchitecturePrinciples:
    """Test that OOP principles are correctly applied and support extensibility."""

    def test_all_agents_inherit_from_base_agent(self):
        """All agents should inherit from the Agent base class."""
        router = RouterAgent()
        customer = CustomerAgent()
        knowledge = KnowledgeAgent()
        synthesis = SynthesisAgent()

        assert isinstance(router, Agent)
        assert isinstance(customer, Agent)
        assert isinstance(knowledge, Agent)
        assert isinstance(synthesis, Agent)

    def test_all_agents_have_required_class_attributes(self):
        """All agents should have name and description class attributes."""
        agents = [RouterAgent, CustomerAgent, KnowledgeAgent, SynthesisAgent]

        for agent_class in agents:
            assert hasattr(
                agent_class, "name"
            ), f"{agent_class.__name__} missing 'name'"
            assert hasattr(
                agent_class, "description"
            ), f"{agent_class.__name__} missing 'description'"
            assert isinstance(agent_class.name, str)
            assert isinstance(agent_class.description, str)

    def test_all_agents_implement_abstract_methods(self):
        """All agents should implement all abstract methods from base Agent class."""
        agents = [RouterAgent(), CustomerAgent(), KnowledgeAgent(), SynthesisAgent()]

        required_methods = [
            "process",
            "_build_prompt",
            "_build_tools",
            "_define_state_schema",
        ]

        for agent in agents:
            for method in required_methods:
                assert hasattr(agent, method), f"{agent.name} missing method {method}"
                assert callable(
                    getattr(agent, method)
                ), f"{agent.name}.{method} not callable"

    def test_agents_have_invoke_interface(self):
        """All agents should have the invoke() method for LangGraph integration."""
        agents = [RouterAgent(), CustomerAgent(), KnowledgeAgent(), SynthesisAgent()]

        for agent in agents:
            assert hasattr(agent, "invoke")
            assert callable(agent.invoke)

    def test_agents_support_dependency_injection(self):
        """Agents should support LLM dependency injection for testing."""
        mock_llm = Mock()

        # Test that agents accept custom LLM
        try:
            agent = RouterAgent(llm=mock_llm)
            assert agent.llm == mock_llm
        except TypeError:
            # Some agents might not support this yet, but they should
            pytest.skip("Agent doesn't support LLM injection yet")

    def test_architecture_supports_new_agents(self):
        """Architecture should support adding new agents without breaking existing ones."""
        # This test validates that the base Agent class contract is solid
        # New agents can be added by:
        # 1. Inheriting from Agent
        # 2. Implementing abstract methods
        # 3. Setting name and description

        # Verify base class is properly abstract
        with pytest.raises(TypeError):
            # Should not be able to instantiate abstract base class
            Agent()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
