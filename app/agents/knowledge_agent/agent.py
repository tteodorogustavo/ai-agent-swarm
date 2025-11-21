"""
Knowledge Agent Implementation

This module implements the KnowledgeAgent class, which handles complex queries
requiring information retrieval and generation, primarily about InfinitePay's
products and services. It extends the base Agent class and implements a
Self-Corrective RAG pattern with a Quality Control (QC) loop.

The KnowledgeAgent is responsible for:
- Answering questions about InfinitePay products using RAG
- Performing web searches for general knowledge questions
- Implementing a self-correction loop to ensure answer quality
- Providing evidence-backed responses

Architecture:
    This agent uses a Sub-Graph pattern with multiple internal nodes:
    - investigate: Gathers evidence using RAG/Web Search tools
    - grade: Quality control check on draft answers (manages retry logic internally)
    - human_escalation: Escalates to human support via Slack after max retries
    - accept: Approves final answer
    - fallback: Safety net when QC loop fails

Integration:
    This agent is designed to be used as a node in the LangGraph orchestration
    system, processing knowledge-related queries within the broader agent swarm.
"""
import logging
from typing import Any
from typing import Dict
from typing import List
from typing import Type

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import END
from langgraph.graph import StateGraph

from .state import KnowledgeState
from .sub_graph import INVESTIGATOR_PROMPT
from .sub_graph import run_grader
from .sub_graph import run_human_escalation
from .sub_graph import run_investigator
from .tools import knowledge_agent_tools
from app.agents.base import Agent

# Configure logging
logger = logging.getLogger(__name__)


class KnowledgeAgent(Agent):
    """
    Knowledge Specialist Agent for InfinitePay.

    This agent specializes in answering complex questions about InfinitePay's
    products, services, and general knowledge using a Self-Corrective RAG
    (Retrieval-Augmented Generation) approach with a Quality Control loop.

    The agent follows a Self-Correction QC Loop pattern:
    1. **Investigate**: Gathers evidence using RAG and Web Search tools
    2. **Grade**: QC inspector evaluates the draft answer quality
    3. **Decision**: Based on grade, either:
       - Accept: Answer is good, return to user
       - Rewrite: Answer is poor, analyze critique and retry (max 2 attempts)
       - Fallback: Loop failed multiple times, return safe error message

    This architecture ensures high-quality answers by:
    - Not returning hallucinated or low-quality drafts
    - Providing structured critique for improvement
    - Having a safety net for edge cases

    Tools Available:
        - infinitepay_product_search: RAG tool for internal knowledge base
        - web_search: Tavily-powered web search for general questions

    State Schema:
        Input:
            - original_question: The user's query
            - messages: Internal conversation history for QC loop

        Output:
            - final_answer: The approved answer
            - final_evidence: Supporting evidence/context used

    Example:
        ```python
        # Initialize the agent
        agent = KnowledgeAgent()

        # Process a knowledge query
        result = agent.invoke({
            "original_question": "What are the fees for InfinitePay's card machine?",
            "messages": [],
            "context": [],
            "draft_answer": "",
            "latest_grade": "",
            "latest_critique": "",
            "rewrite_attempts": 0,
            "final_answer": "",
            "final_evidence": []
        })

        print(result["final_answer"])
        # Output: "The fees for InfinitePay's card machine are: PIX 0%, ..."
        ```

    Architecture Decisions:
        - Uses gpt-4o-mini for speed and cost-effectiveness in QC loop
        - Maximum 2 rewrite attempts (3 total tries) to balance quality vs. latency
        - Structured outputs (Pydantic) for reliable routing decisions
        - Separate nodes for each responsibility (SRP)
    """

    # Class-level attributes
    name = "knowledge_agent"
    description = "Handles complex queries requiring information retrieval about InfinitePay products or general knowledge using RAG and web search with self-correction QC loop."

    def __init__(
        self,
        llm: ChatOpenAI = None,
        temperature: float = 0,
        model: str = "gpt-4o-mini",
        **kwargs,
    ):
        """
        Initialize the KnowledgeAgent.

        Args:
            llm (ChatOpenAI, optional): Pre-configured language model.
                If None, creates a new instance with OPENAI_API_KEY from environment.
            temperature (float): Controls response randomness. Default is 0 for
                deterministic, factual responses.
            model (str): OpenAI model to use. Default is "gpt-4o-mini" for
                cost-effectiveness in the QC loop.
            **kwargs: Additional arguments passed to the base Agent class.
        """
        # Create default LLM with API key if not provided
        if llm is None:
            llm = ChatOpenAI(model=model, temperature=temperature)

        # Initialize base Agent class
        super().__init__(llm=llm, temperature=temperature, model=model, **kwargs)

        # Build the internal sub-graph (self-correction QC loop)
        self._graph = self._build_graph()

    def _build_prompt(self) -> ChatPromptTemplate:
        """
        Build the KnowledgeAgent's investigator prompt template.

        The prompt instructs the agent to:
        - Act as a knowledge specialist for InfinitePay
        - Use RAG and web search tools to gather evidence
        - Base answers solely on retrieved context (no hallucination)
        - Follow structured reasoning process

        Returns:
            ChatPromptTemplate: The configured prompt template for the
                investigate node.
        """
        return INVESTIGATOR_PROMPT

    def _build_tools(self) -> List[BaseTool]:
        """
        Define the tools available to the KnowledgeAgent.

        Returns:
            List[BaseTool]: A list containing:
                - infinitepay_product_search: RAG tool for internal KB
                - web_search: Tavily web search for general knowledge
        """
        return knowledge_agent_tools

    def _define_state_schema(self) -> Type:
        """
        Define the state schema for knowledge processing.

        Returns:
            Type: KnowledgeState TypedDict class defining the structure
                of the internal sub-graph state.
        """
        return KnowledgeState

    def _build_graph(self) -> StateGraph:
        """
        Build the internal Self-Correction QC Loop sub-graph.

        This method constructs the complete state machine for the knowledge
        agent's self-corrective workflow:

        Flow:
            START → investigate → grade → [conditional]
                                           ├→ END (accept)
                                           ├→ investigate (reject, retry loop)
                                           └→ human_escalation → END

        Nodes:
            - investigate: Tool-calling LLM that gathers evidence
            - grade: QC inspector that evaluates draft quality AND formats final evidence on accept
            - human_escalation: Escalates to Slack when max retries reached

        Conditional Logic:
            - If grade == "accept" → go to END (grader already formatted final answer)
            - If grade == "reject" → go to investigate (retry loop)
            - If grade == "escalate" → go to human_escalation → END

        Returns:
            StateGraph: The compiled sub-graph ready for invocation.

        Design Pattern:
            This implements the "Sub-Graph" pattern from LangGraph, allowing
            the KnowledgeAgent to have complex internal logic while presenting
            a simple interface to the main orchestration graph.
        """
        # Initialize the StateGraph with KnowledgeState schema
        builder = StateGraph(KnowledgeState)

        # 1. Add all nodes (stations in the factory)
        builder.add_node("investigate", run_investigator)
        builder.add_node("grade", run_grader)
        builder.add_node("human_escalation", run_human_escalation)

        # 2. Set entry point (where the sub-graph starts)
        builder.set_entry_point("investigate")

        # 3. Add edges (conveyor belts between stations)

        # Investigator always sends draft to Grader
        builder.add_edge("investigate", "grade")

        builder.add_conditional_edges(
            "grade",  # Starting node
            self._should_continue,  # Decision function
            {
                "accept": END,  # Grade passed → finish (grader formatted answer)
                "investigate": "investigate",  # Grade failed, retry
                "human_escalation": "human_escalation",  # Max retries, escalate
            },
        )

        # Terminal nodes (end the sub-graph)
        builder.add_edge("human_escalation", END)

        # 4. Compile the sub-graph
        compiled_graph = builder.compile()

        logger.info("KnowledgeAgent sub-graph compiled successfully")

        return compiled_graph

    def _should_continue(self, state: KnowledgeState) -> str:
        """
        Conditional routing logic based on Grader's decision.

        This is the decision function for the conditional edge after the Grader.
        It reads the `grade_decision` field set by the Grader and routes accordingly.

        Routing Rules (Simplified):
        - "accept": Draft passed quality check → route to END (grader formatted answer)
        - "reject": Draft failed, retries available → route back to investigate
        - "escalate": Max retries reached → route to human_escalation
        - Default: Safety fallback → route to investigate

        Args:
            state (KnowledgeState): Current state with grade_decision

        Returns:
            str: Next node name ("accept", "investigate", or "human_escalation")

        Example:
            ```python
            # Scenario 1: First attempt passed QC
            state = {"grade_decision": "accept"}
            result = self._should_continue(state)
            # Returns: "accept"

            # Scenario 2: First attempt failed, retry available
            state = {"grade_decision": "reject"}
            result = self._should_continue(state)
            # Returns: "investigate"

            # Scenario 3: Max retries reached
            state = {"grade_decision": "escalate"}
            result = self._should_continue(state)
            # Returns: "human_escalation"
            ```
        """
        decision = state.get("grade_decision", "investigate")

        logger.info(f"--- CONDITIONAL ROUTING: grade_decision='{decision}' ---")

        if decision == "accept":
            logger.info("Draft approved → routing to 'accept'")
            return "accept"

        elif decision == "reject":
            logger.info("Draft rejected, retrying → routing to 'investigate'")
            return "investigate"

        elif decision == "escalate":
            logger.info("Max retries reached → routing to 'human_escalation'")
            return "human_escalation"

        else:
            # Safety fallback (should never happen)
            logger.warning(
                f"Unknown grade_decision '{decision}' → defaulting to 'investigate'"
            )
            return "investigate"

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a knowledge query using the Self-Correction QC Loop.

        This method invokes the internal sub-graph, which handles the complete
        self-corrective workflow. The sub-graph will:
        1. Investigate and gather evidence
        2. Grade the draft answer
        3. Loop back for rewrites if needed (up to 2 times)
        4. Return final approved answer or fallback message

        Args:
            state (Dict[str, Any]): Current state containing:
                - original_question (str): The user's query
                - messages (List[Any]): Internal conversation history
                - context (List[str]): Evidence gathered so far
                - draft_answer (str): Current draft answer
                - latest_grade (str): Last QC grade result
                - latest_critique (str): Last QC critique
                - rewrite_attempts (int): Number of retries so far
                - final_answer (str): Approved final answer
                - final_evidence (List[str]): Supporting evidence

        Returns:
            Dict[str, Any]: State updates containing:
                - final_answer (str): The approved answer or fallback message
                - final_evidence (List[str]): Evidence/context used

        Raises:
            KeyError: If required state fields are missing
            ValueError: If state data is invalid

        Example:
            ```python
            result = agent.process({
                "original_question": "What are InfinitePay's card fees?",
                "messages": [],
                "context": [],
                "draft_answer": "",
                "latest_grade": "",
                "latest_critique": "",
                "rewrite_attempts": 0,
                "final_answer": "",
                "final_evidence": []
            })
            # Returns: {
            #     "final_answer": "InfinitePay's card fees are: PIX 0%, ...",
            #     "final_evidence": ["RAG context about fees..."]
            # }
            ```

        Implementation Note:
            This method delegates all processing to the internal sub-graph,
            which encapsulates the complex self-correction logic. The agent
            class acts as a clean OOP wrapper around the graph.
        """
        # Log the start of processing
        logger.info(f"--- {self.name.upper()}: Starting self-correction QC loop ---")
        logger.debug(f"Original question: {state.get('original_question', 'N/A')}")

        # Invoke the internal sub-graph
        # The graph will run through investigate → grade → (loop/accept/fallback)
        result = self._graph.invoke(state)

        # Log completion
        logger.info(f"--- {self.name.upper()}: QC loop completed ---")
        logger.debug(f"Final answer length: {len(result.get('final_answer', ''))}")
        logger.debug(f"Evidence count: {len(result.get('final_evidence', []))}")

        # CRITICAL: Signal to Main Graph that we're done processing
        # This prevents infinite loop by routing to synthesis_agent instead of back to router
        logger.info(f"--- {self.name.upper()}: Processing completed ---")

        # Return the final state updates with route signal
        return {
            "final_answer": result["final_answer"],
            "final_evidence": result["final_evidence"],
            "route": "synthesis_agent",  # Signal: "I'm done, go to synthesis"
        }

    @property
    def graph(self) -> StateGraph:
        """
        Get the compiled internal sub-graph.

        This property provides access to the internal state machine,
        useful for debugging, visualization, or direct invocation.

        Returns:
            StateGraph: The compiled self-correction QC loop graph.

        Example:
            ```python
            agent = KnowledgeAgent()

            # Get graph for visualization
            graph = agent.graph

            # Direct invocation (bypasses process method)
            result = graph.invoke(state)
            ```
        """
        return self._graph
