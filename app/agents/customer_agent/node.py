"""
Customer Agent Implementation

This module implements the CustomerAgent class, which handles customer inquiries
and account-related questions for InfinitePay. It extends the base Agent class
and uses a ReAct (Reasoning + Acting) pattern to retrieve user information using
specialized tools.

The CustomerAgent is responsible for:
- Retrieving user account status
- Checking transfer histories
- Setting reminders for follow-up actions
- Providing factual answers based solely on tool outputs

Integration:
    This agent is designed to be used as a node in the LangGraph orchestration
    system, processing customer-related queries within the broader agent swarm.
"""
import logging
from typing import Any
from typing import Dict
from typing import List
from typing import Type

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from .prompt import CUSTOMER_AGENT_PROMPT
from .state import CustomerState
from .tools import customer_agent_tools
from app.agents.base import Agent

# Configure logging
logger = logging.getLogger(__name__)


class CustomerAgent(Agent):
    """
    Customer Support Agent for InfinitePay.

    This agent specializes in handling customer inquiries related to account
    information, transfer status, and general customer support. It uses a set
    of secure, pre-defined tools to retrieve user data and formulate accurate
    responses.

    The agent follows a ReAct (Reasoning + Acting) pattern:
    1. Analyzes the customer's question
    2. Determines which tools to invoke
    3. Calls appropriate tools with the user_id
    4. Observes tool outputs (facts)
    5. Formulates a final answer based solely on retrieved data

    Tools Available:
        - get_user_status: Fetches account status information
        - check_transfer_status: Retrieves recent transfer history
        - set_reminder: Creates follow-up reminders

    State Schema:
        Input:
            - user_id: The customer's unique identifier
            - original_question: The customer's inquiry
            - messages: Conversation history for context

        Output:
            - final_answer: The agent's response to the customer
            - final_evidence: Raw data retrieved from tools

    Example:
        ```python
        # Initialize the agent
        agent = CustomerAgent()

        # Process a customer inquiry
        result = agent.invoke({
            "user_id": "client789",
            "original_question": "Why did my transfer fail?",
            "messages": [],
            "final_answer": "",
            "final_evidence": []
        })

        print(result["final_answer"])
        # Output: "Your transfer failed due to insufficient funds..."
        ```

    Security Considerations:
        - Uses pre-defined tools to prevent SQL injection
        - No direct database access from prompts
        - User data is never exposed in logs
        - All queries are parameterized and validated
    """

    # Class-level attributes
    name = "customer_agent"
    description = "Handles customer inquiries related to account status, transfers, and personal information about his own account."

    def __init__(
        self,
        llm: ChatOpenAI = None,
        temperature: float = 0.2,
        model: str = "gpt-4o-mini",
        **kwargs,
    ):
        """
        Initialize the CustomerAgent.

        Args:
            llm (ChatOpenAI, optional): Pre-configured language model.
                If None, creates a new instance with OPENAI_API_KEY from environment.
            temperature (float): Controls response randomness. Default is 0 for
                deterministic, factual responses.
            model (str): OpenAI model to use. Default is "gpt-4o-mini".
            **kwargs: Additional arguments passed to the base Agent class.
        """
        # Create default LLM with API key if not provided
        if llm is None:
            llm = ChatOpenAI(
                model=model,
                temperature=temperature,
            )

        # Initialize base Agent class
        super().__init__(llm=llm, temperature=temperature, model=model, **kwargs)

    def _build_prompt(self) -> ChatPromptTemplate:
        """
        Build the CustomerAgent's prompt template.

        The prompt instructs the agent to:
        - Act as a customer support representative
        - Use only the provided tools to retrieve information
        - Follow a structured Chain of Thought process
        - Base answers solely on tool outputs (no hallucination)

        Returns:
            ChatPromptTemplate: The configured prompt template with placeholders
                for messages, original_question, user_id, and agent_scratchpad.
        """
        return CUSTOMER_AGENT_PROMPT

    def _build_tools(self) -> List[BaseTool]:
        """
        Define the tools available to the CustomerAgent.

        Returns:
            List[BaseTool]: A list containing:
                - get_user_status: Retrieves account status
                - check_transfer_status: Checks transfer history
                - set_reminder: Creates follow-up reminders
        """
        return customer_agent_tools

    def _define_state_schema(self) -> Type:
        """
        Define the state schema for customer interactions.

        Returns:
            Type: CustomerState TypedDict class defining the structure
                of input and output data.
        """
        return CustomerState

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a customer inquiry using the ReAct pattern.

        This method:
        1. Extracts user_id, question, and conversation history from state
        2. Prepares the LLM chain with structured output
        3. Invokes the chain with all necessary context
        4. Tracks which tools were actually called
        5. Returns the final answer and supporting evidence with tool metadata

        Args:
            state (Dict[str, Any]): Current state containing:
                - user_id (str): Customer identifier
                - original_question (str): Customer's inquiry
                - messages (List[Any]): Conversation history
                - final_answer (str): Previous answer (if any)
                - final_evidence (List[str]): Previous evidence (if any)

        Returns:
            Dict[str, Any]: State updates containing:
                - final_answer (str): The agent's response
                - final_evidence (List[Dict]): Structured evidence with tool metadata

        Raises:
            KeyError: If required state fields are missing
            ValueError: If state data is invalid

        Example:
            ```python
            result = agent.process({
                "user_id": "client789",
                "original_question": "What is my account status?",
                "messages": [],
                "final_answer": "",
                "final_evidence": []
            })
            # Returns: {
            #     "final_answer": "Your account is Active...",
            #     "final_evidence": [{
            #         "source": "customer_agent",
            #         "tools_called": ["get_user_profile"],
            #         "content": "{'status': 'Active', ...}"
            #     }]
            # }
            ```
        """
        # Extract necessary inputs from state
        user_id = state["user_id"]
        query = state["original_question"]
        messages = state.get("messages", [])

        logger.info(f"CustomerAgent: Processing query for user {user_id}")

        # Bind tools to LLM for ReAct pattern
        llm_with_tools = self._llm.bind_tools(self._tools)

        # Format tools list for prompt
        tools_list_str = "\n".join(
            [f"- {tool.name}: {tool.description}" for tool in self._tools]
        )

        # Build the processing chain (prompt + LLM with tools)
        chain = self._prompt | llm_with_tools

        # Invoke the chain with all required context
        response = chain.invoke(
            {
                "messages": messages,
                "original_question": query,
                "user_id": user_id,
                "tools_list": tools_list_str,
                "agent_scratchpad": [],
                "route": state.get("route", "customer_agent"),
            }
        )

        # Track which tools were called by analyzing the response
        tools_called = []
        tool_outputs = []

        if hasattr(response, "tool_calls") and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name", "unknown")
                tools_called.append(tool_name)
                logger.info(f"CustomerAgent: Tool called: {tool_name}")

                # Execute the tool call
                for tool in self._tools:
                    if tool.name == tool_name:
                        try:
                            tool_args = tool_call.get("args", {})
                            result = tool.invoke(tool_args)
                            tool_outputs.append({tool_name: result})
                            logger.info(
                                f"CustomerAgent: Tool {tool_name} executed successfully"
                            )
                        except Exception as e:
                            logger.error(
                                f"CustomerAgent: Error executing tool {tool_name}: {e}"
                            )
                            tool_outputs.append({tool_name: f"Error: {str(e)}"})
                        break

        # Extract final answer from response
        final_answer = (
            response.content if hasattr(response, "content") else str(response)
        )

        # If tools were called, use their outputs to formulate the answer
        if tool_outputs:
            # Re-invoke LLM with tool outputs to get final answer
            final_response = self._llm.invoke(
                f"Based on these tool outputs: {tool_outputs}\n\n"
                f"Original question: {query}\n\n"
                f"Please provide a concise answer in Brazilian Portuguese."
            )
            final_answer = (
                final_response.content
                if hasattr(final_response, "content")
                else str(final_response)
            )

        # Build structured evidence with tool metadata
        structured_evidence = [
            {
                "source": "customer_agent",
                "tools_called": tools_called,
                "content": str(tool_outputs) if tool_outputs else final_answer,
            }
        ]

        logger.info(f"CustomerAgent: Completed processing with tools: {tools_called}")

        # CRITICAL: Signal to Main Graph that we're done processing
        # This prevents infinite loop by routing to synthesis_agent instead of back to router
        logger.info("--- CUSTOMER_AGENT: Processing completed ---")

        # Return state updates with route signal
        return {
            "final_answer": final_answer,
            "final_evidence": structured_evidence,
            "route": "synthesis_agent",  # Signal: "I'm done, go to synthesis"
        }
