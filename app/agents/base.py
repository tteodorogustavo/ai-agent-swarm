"""
Base Agent Module

This module defines the abstract base class for all agents in the AI Agent Swarm system.
It establishes a consistent contract and interface that all specialized agents must implement,
ensuring modularity, extensibility, and maintainability across the entire agent ecosystem.

"""
import logging
import os
from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Type

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

load_dotenv()


# Setting module-level logger
logger = logging.getLogger(__name__)


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class Agent(ABC):
    """
    Abstract base class(ABC) for all agents in the AI Agent Swarm system.

    This class defines the contract that all specialized agents must implement,
    providing a consistent interface for agent construction, invocation, and
    state management. It encapsulates common functionality such as LLM integration,
    prompt management, tool handling, and logging.

    The Agent class is designed to work seamlessly with LangGraph's state management
    system while maintaining clean object-oriented design principles. Each agent
    encapsulates its own prompt, tools, and processing logic, making the system
    highly modular and extensible.

    Architecture Pattern:
        - Template Method Pattern: Defines the skeleton of agent processing in `invoke()`
        - Strategy Pattern: Different agents implement different processing strategies
        - Dependency Injection: LLM and configuration can be injected

    Integration with LangGraph:
        Agents are designed to be used as nodes in a LangGraph StateGraph. The `invoke()`
        method serves as the callable interface that LangGraph expects, maintaining
        compatibility while providing object-oriented encapsulation.

    Attributes:
        name (str): Unique identifier for the agent. Should be descriptive and lowercase.
        description (str): Human-readable description of the agent's purpose and capabilities.
        _llm (ChatOpenAI): The language model instance used for processing.
        _prompt (ChatPromptTemplate): The chat prompt template specific to this agent.
        _tools (List[BaseTool]): List of tools/functions available to this agent.
        _state_schema (Type): The TypedDict or Pydantic model defining the agent's state structure.

    Best Practices to instantiate subclasses:
        - Keep agents focused on a single responsibility
        - Use dependency injection for testability
        - Log important decisions and state changes
        - Validate state before and after processing
        - Handle errors gracefully with meaningful messages
        - Use structured outputs for consistency
    """

    # Class-level attributes that must be defined by subclasses
    name: str = "base_agent"
    description: str = "Base agent class"

    def __init__(
        self,
        llm: Optional[ChatOpenAI] = None,
        temperature: float = 0.0,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize the Agent with common components.

        This constructor sets up the core components that all agents need:
        the language model, prompt template, tools, and state schema. It follows
        the principle of dependency injection, allowing external configuration
        while providing sensible defaults.

        The initialization process:
        1. Sets up the LLM (provided or creates default)
        2. Builds the agent-specific prompt template
        3. Initializes the agent's toolset
        4. Defines the state schema for type safety

        Args:
            llm (Optional[ChatOpenAI]): Pre-configured language model instance.
                If None, creates a new ChatOpenAI instance with the specified
                model and temperature. Useful for dependency injection and testing.
            temperature (float): Controls randomness in model responses.
                - 0.0 = Deterministic, focused responses
                - 1.0 = More creative, varied responses
                Default is 0 for consistent, predictable agent behavior.
            model (str): The OpenAI model identifier to use.
                Default is "gpt-4o-mini" for cost-effectiveness.
                Can be overridden for more powerful models like "gpt-4o".
            **kwargs: Additional keyword arguments for future extensibility.
                Can be used to pass custom configuration to specialized agents.

        Raises:
            NotImplementedError: If abstract methods are not implemented by subclass.
            ValueError: If initialization of components fails.

        Example:
            ```python
            # Default initialization
            agent = MyAgent()

            # Custom LLM injection
            custom_llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
            agent = MyAgent(llm=custom_llm)

            # Custom configuration
            agent = MyAgent(temperature=0.5, model="gpt-4o")
            ```
        """
        # Initialize or use provided LLM
        self._llm = llm or ChatOpenAI(
            model=model, temperature=temperature, api_key=api_key or OPENAI_API_KEY
        )

        # Build agent-specific components
        self._prompt = self._build_prompt()
        self._tools = self._build_tools()
        self._state_schema = self._define_state_schema()

        # Log successful initialization
        logger.info(
            f"Initialized {self.name} agent with model={model}, "
            f"temperature={temperature}, tools_count={len(self._tools)}"
        )

    # Abstract methods that must be implemented by subclasses:

    @abstractmethod
    def _build_prompt(self) -> ChatPromptTemplate:
        """
        Construct the prompt template specific to this agent.

        This method defines the conversational structure and instructions that
        guide the agent's behavior. The prompt should include:
        - System message with agent's role and capabilities
        - Placeholders for dynamic content (messages, context, etc.)
        - Instructions for tool usage (if applicable)
        - Output format specifications

        The prompt template is the "DNA" of the agent, defining its personality,
        capabilities, and how it processes information.

        Returns:
            ChatPromptTemplate: A LangChain prompt template configured with
                the appropriate message structure, placeholders, and instructions.

        Example:
            ```python
            def _build_prompt(self) -> ChatPromptTemplate:
                return ChatPromptTemplate.from_messages([
                    ("system", "You are a customer support agent..."),
                    ("placeholder", "{messages}"),
                    ("human", "{original_question}"),
                    MessagesPlaceholder(variable_name="agent_scratchpad")
                ])
            ```

        Design Considerations:
            - Keep system messages clear and focused
            - Use placeholders for all dynamic content
            - Consider token limits when designing prompts
            - Include examples for complex tasks (few-shot learning)
        """
        pass

    @abstractmethod
    def _build_tools(self) -> List[BaseTool]:
        """
        Define and return the list of tools available to this agent.

        Tools extend the agent's capabilities beyond pure language understanding,
        allowing it to interact with external systems, databases, APIs, and services.
        This method should return all tools that the agent needs to accomplish its tasks.

        Tools can include:
        - API clients (e.g., database queries, REST API calls)
        - Utility functions (e.g., calculations, parsing)
        - External service integrations (e.g., email, notifications)
        - Custom business logic functions

        Returns:
            List[BaseTool]: A list of LangChain BaseTool instances that the agent
                can invoke during processing. Return empty list if agent doesn't use tools.

        Example:
            ```python
            def _build_tools(self) -> List[BaseTool]:
                return [
                    get_user_status_tool,
                    check_transfer_status_tool,
                    set_reminder_tool
                ]

            # For agents without tools
            def _build_tools(self) -> List[BaseTool]:
                return []
            ```

        Best Practices:
            - Each tool should have a single, clear purpose
            - Provide detailed docstrings for tools (LLM uses these)
            - Validate tool inputs and handle errors gracefully
            - Consider rate limiting and authentication
            - Test tools independently before integration
        """
        pass

    @abstractmethod
    def _define_state_schema(self) -> Type:
        """
        Define the state schema that this agent expects and produces.

        State schemas define the structure of data flowing through the agent,
        ensuring type safety and clear contracts between agents in the graph.
        This is crucial for LangGraph's state management system.

        The schema typically includes:
        - Input fields: Data the agent needs to process
        - Output fields: Data the agent produces
        - Internal fields: Temporary data used during processing
        - Metadata: Additional context or tracking information

        Returns:
            Type: A TypedDict class defining the state structure.
                Should include all fields the agent reads from or writes to.

        Example:
            ```python
            from typing import TypedDict, List, Annotated

            class CustomerState(TypedDict):
                user_id: str
                original_question: str
                messages: List[Any]
                final_answer: str
                final_evidence: List[str]

            def _define_state_schema(self) -> Type:
                return CustomerState
            ```

        Design Considerations:
            - Use TypedDict for LangGraph compatibility
            - Consider using Annotated for metadata
            - Document each field's purpose
            - Keep state minimal (only necessary data)
            - Consider backward compatibility when modifying
        """
        pass

    @abstractmethod
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the core processing logic of the agent.

        This is the heart of the agent where the actual work happens. It receives
        the current state, performs agent-specific operations (LLM calls, tool usage,
        reasoning, etc.), and returns updates to the state.

        The process method should:
        1. Extract necessary data from the input state
        2. Perform agent-specific operations (LLM inference, tool calls, etc.)
        3. Process and validate results
        4. Return state updates as a dictionary

        This method implements the agent's unique business logic and decision-making
        process. It can involve:
        - Single LLM call
        - ReAct loop (Reasoning + Acting)
        - Quality control loop
        - Multi-step processing pipeline
        - Tool orchestration

        Args:
            state (Dict[str, Any]): The current state dictionary containing all
                necessary input data for the agent. Structure must match the
                schema defined in `_define_state_schema()`.

        Returns:
            Dict[str, Any]: A dictionary containing updates to the state.
                Only modified/new fields need to be returned. LangGraph will
                merge these updates with the existing state.

        Raises:
            KeyError: If required state fields are missing.
            ValueError: If state data is invalid or malformed.
            Exception: For any processing errors (should be caught and handled).

        Example:
            ```python
            def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
                # 1. Extract inputs
                user_id = state["user_id"]
                question = state["original_question"]

                # 2. Prepare chain
                chain = self._prompt | self._llm

                # 3. Invoke LLM
                result = chain.invoke({
                    "user_id": user_id,
                    "original_question": question,
                    "messages": state.get("messages", []),
                })

                # 4. Return updates
                return {
                    "final_answer": result["final_answer"],
                    "final_evidence": result.get("final_evidence", [])
                }
            ```

        Best Practices:
            - Validate inputs before processing
            - Handle errors gracefully
            - Log important decisions
            - Keep processing focused and efficient
            - Return only changed state fields
            - Use structured outputs for consistency
        """
        pass

    # ============================================================================
    # CONCRETE METHODS - Provided with default implementation
    # ============================================================================

    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Public entry point for agent invocation.

        This method serves as the primary interface for invoking the agent,
        whether from LangGraph nodes, direct calls, or testing. It wraps the
        core `process()` method with additional functionality such as logging,
        validation, and error handling.

        The invoke method implements the Template Method pattern:
        1. Pre-processing (logging, validation)
        2. Core processing (calls `process()`)
        3. Post-processing (logging, cleanup)

        This design allows subclasses to focus on their specific logic in `process()`
        while the base class handles cross-cutting concerns.

        Args:
            state (Dict[str, Any]): The current state dictionary to process.
                Must conform to the structure defined by `_define_state_schema()`.

        Returns:
            Dict[str, Any]: Dictionary containing state updates produced by
                the agent's processing logic.

        Raises:
            Exception: Any exception raised during processing is logged and re-raised.
                Calling code should handle exceptions appropriately.

        Example:
            ```python
            # Direct invocation
            agent = CustomerAgent()
            result = agent.invoke({
                "user_id": "user_123",
                "original_question": "What is my balance?",
                "messages": []
            })

            # Usage in LangGraph
            graph.add_node("customer_node", customer_agent.invoke)
            ```

        LangGraph Integration:
            This method is designed to be used directly as a LangGraph node function:
            - Accepts state dictionary
            - Returns state updates
            - Compatible with LangGraph's execution model
        """
        try:
            # Log invocation start
            self._log_invocation(state)

            # Execute core processing logic
            result = self.process(state)

            # Log successful completion
            self._log_result(result)

            return result

        except Exception as e:
            # Log error and re-raise
            logger.error(
                f"Error in {self.name} agent processing: {str(e)}", exc_info=True
            )
            raise

    def _log_invocation(self, state: Dict[str, Any]) -> None:
        """
        Log the start of agent invocation.

        This method is called at the beginning of `invoke()` to log important
        information about the agent's execution. It helps with debugging,
        monitoring, and understanding the flow of data through the agent system.

        The default implementation logs:
        - Agent name
        - Start of processing
        - Key state information (can be customized)

        Args:
            state (Dict[str, Any]): The input state being processed.
                Can be inspected to log relevant context.

        Note:
            Subclasses can override this method to customize logging behavior,
            add more detailed context, or integrate with external monitoring systems.

        Example:
            ```python
            def _log_invocation(self, state: Dict[str, Any]) -> None:
                super()._log_invocation(state)
                logger.debug(f"Processing user: {state.get('user_id')}")
            ```
        """
        logger.info(f"--- {self.name.upper()}: Processing started ---")
        logger.debug(f"{self.name} received state with keys: {list(state.keys())}")

    def _log_result(self, result: Dict[str, Any]) -> None:
        """
        Log the completion of agent processing.

        This method is called after successful execution of `process()` to log
        the results and completion status. It provides visibility into what the
        agent produced and helps with debugging and monitoring.

        The default implementation logs:
        - Agent name
        - Completion status
        - Result keys (what was updated)

        Args:
            result (Dict[str, Any]): The state updates produced by the agent.
                Can be inspected to log relevant output information.

        Note:
            Subclasses can override this method to log specific results,
            track metrics, or integrate with monitoring systems.

        Example:
            ```python
            def _log_result(self, result: Dict[str, Any]) -> None:
                super()._log_result(result)
                if "final_answer" in result:
                    logger.debug(f"Answer length: {len(result['final_answer'])}")
            ```
        """
        logger.info(f"--- {self.name.upper()}: Processing completed ---")
        logger.debug(f"{self.name} returned updates for keys: {list(result.keys())}")

    def get_llm_with_structure(self, schema: Type[BaseModel]) -> ChatOpenAI:
        """
        Get a language model instance configured with structured output.

        This helper method returns a version of the agent's LLM that is configured
        to return structured output conforming to a specific Pydantic schema.
        This is useful when you need the LLM to return data in a specific format
        (e.g., for validation, routing decisions, or structured data extraction).

        LangChain's `with_structured_output()` ensures that the LLM's response
        is parsed and validated against the provided schema, returning a Pydantic
        model instance instead of raw text.

        Args:
            schema (Type[BaseModel]): A Pydantic BaseModel class defining the
                expected structure of the LLM's output. The model should have
                clear field definitions and validation rules.

        Returns:
            ChatOpenAI: A configured LLM instance that will return structured
                output matching the provided schema.

        Raises:
            ValidationError: If the LLM's output doesn't conform to the schema.

        Example:
            ```python
            from pydantic import BaseModel, Field

            class RouteDecision(BaseModel):
                route: str = Field(description="The selected route")
                confidence: float = Field(description="Confidence score")

            # In your agent's process method
            def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
                structured_llm = self.get_llm_with_structure(RouteDecision)
                chain = self._prompt | structured_llm

                result = chain.invoke(state)
                # result is a RouteDecision instance
                return {"route": result.route}
            ```

        Use Cases:
            - Routing decisions (which agent to call next)
            - Data extraction (pulling specific fields from text)
            - Quality control (structured evaluation results)
            - Classification tasks (categorizing inputs)
        """
        return self._llm.with_structured_output(schema)

    # ============================================================================
    # PROPERTY ACCESSORS - Read-only access to internal state
    # ============================================================================

    @property
    def llm(self) -> ChatOpenAI:
        """
        Get the language model instance used by this agent.

        Returns:
            ChatOpenAI: The configured LLM instance.
        """
        return self._llm

    @property
    def prompt(self) -> ChatPromptTemplate:
        """
        Get the prompt template used by this agent.

        Returns:
            ChatPromptTemplate: The configured prompt template.
        """
        return self._prompt

    @property
    def tools(self) -> List[BaseTool]:
        """
        Get the list of tools available to this agent.

        Returns:
            List[BaseTool]: The configured tools.
        """
        return self._tools

    @property
    def state_schema(self) -> Type:
        """
        Get the state schema definition for this agent.

        Returns:
            Type: The state schema class.
        """
        return self._state_schema

    def __repr__(self) -> str:
        """
        Return a string representation of the agent.

        Returns:
            str: A readable representation including name and description.
        """
        return f"{self.__class__.__name__}(name='{self.name}', description='{self.description}')"
