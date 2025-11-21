"""
Investigator Node Implementation

This node runs a tool-calling LLM to gather evidence and formulate a draft answer.

Design Pattern: Custom ReAct-style implementation without deprecated APIs
"""
import logging
from datetime import datetime
from datetime import timezone

from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from .prompt import INVESTIGATOR_PROMPT
from app.agents.knowledge_agent.state import KnowledgeState
from app.agents.knowledge_agent.tools import knowledge_agent_tools
from app.agents.knowledge_agent.tools import rag_tool
from app.agents.knowledge_agent.tools import web_search_tool

# Configure logging
logger = logging.getLogger(__name__)


def run_investigator(state: KnowledgeState) -> dict:
    """
    This node runs a tool-calling LLM to gather evidence and formulate a draft answer.

    Instead of using deprecated create_react_agent(), we directly use the LLM
    with tool binding, which is the modern LangChain approach.

    Args:
        state (KnowledgeState): The current state containing the question and messages

    Returns:
        dict: Updated state with context (evidence) and draft_answer
    """

    LLM = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # Bind tools to LLM (modern approach)
    llm_with_tools = LLM.bind_tools(knowledge_agent_tools)

    # Get the inputs from the state
    question = state["original_question"]
    # The internal memory messages contains the critique/instructions from prior loops
    messages = state["messages"]

    # Get current date/time for the prompt
    current_datetime = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Build the message sequence for the LLM
    prompt_messages = INVESTIGATOR_PROMPT.format_messages(
        original_question=question,
        messages=messages,
        current_datetime=current_datetime,
        agent_scratchpad=[],  # Empty for initial call
    )

    # Invoke the LLM with tools
    # The LLM will decide which tools to call based on the prompt
    response = llm_with_tools.invoke(prompt_messages)

    # Extract tool calls if any
    evidence = []
    tools_called = []  # Track which tools were actually invoked
    if hasattr(response, "tool_calls") and response.tool_calls:
        # Execute tool calls
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # Find and execute the matching tool
            for tool in knowledge_agent_tools:
                if tool.name == tool_name:
                    try:
                        result = tool.invoke(tool_args)
                        evidence.append(str(result))
                        tools_called.append(tool_name)  # Register tool call
                        logger.info(
                            f"KnowledgeAgent: Called tool '{tool_name}' with args {tool_args}"
                        )
                    except Exception as e:
                        evidence.append(f"Error calling {tool_name}: {str(e)}")
                        tools_called.append(
                            f"{tool_name}_failed"
                        )  # Register failed call
                        logger.error(
                            f"KnowledgeAgent: Tool '{tool_name}' failed: {str(e)}"
                        )
                    break

        # After executing tools, generate final answer
        # Re-invoke LLM with tool results
        tool_messages = [AIMessage(content=str(f'"""{response.content}"""'))]
        for i, ev in enumerate(evidence):
            tool_messages.append(HumanMessage(content=f"Tool {i+1} result: {ev}"))

        final_response = LLM.invoke(
            prompt_messages
            + tool_messages
            + [
                HumanMessage(
                    content="Based on the tool results between triple quotes, provide a concise, "
                    "objective final answer that directly addresses the user's original question."
                )
            ]
        )
        draft = final_response.content
    else:
        # No tool calls, use LLM response directly
        draft = response.content if hasattr(response, "content") else str(response)

    # Update the state with the findings
    # If evidence is empty or contains only errors, try a deterministic fallback:
    # 1) call the RAG tool directly with a properly formatted payload
    # 2) if RAG returns nothing or an error, call web_search
    if not evidence or all(
        (isinstance(e, dict) and e.get("error"))
        or (isinstance(e, str) and e.strip().lower().startswith("error"))
        for e in evidence
    ):
        try:
            logging.debug("Investigator fallback: calling rag_tool directly")
            # CRITICAL: Use original_question from state, not the processed question
            original_q = state.get("original_question", question)
            rag_res = rag_tool.invoke({"question": original_q})
            # If rag_res is an error-like dict, try web_search
            if isinstance(rag_res, dict) and rag_res.get("error"):
                logging.debug("RAG returned error, trying web_search")
                web_res = web_search_tool.invoke(original_q)
                tools_called.append("web_search_tool")  # Register fallback tool
                logger.info("KnowledgeAgent: Fallback to web_search_tool")
                # Normalize web_res
                if isinstance(web_res, dict) and web_res.get("results"):
                    evidence.append(str(web_res.get("results")))
                else:
                    evidence.append(str(web_res))
            else:
                tools_called.append("rag_tool")  # Register fallback tool
                logger.info("KnowledgeAgent: Fallback to rag_tool")
                evidence.append(str(rag_res))

            # Re-generate the draft using the tool results appended to evidence
            tool_messages = [AIMessage(content=str(response.content))]
            for i, ev in enumerate(evidence):
                tool_messages.append(HumanMessage(content=f"Tool {i+1} result: {ev}"))

            final_response = LLM.invoke(
                prompt_messages
                + tool_messages
                + [
                    HumanMessage(
                        content="Based on the tool results above, provide your final draft answer."
                    )
                ]
            )
            draft = final_response.content
        except Exception:
            logging.exception("Investigator fallback failed")

    return {
        "context": evidence,
        "draft_answer": draft,
        "tools_called": tools_called,  # Pass tools called to state
        # We add an AI message to the *internal* memory for clarity
        "messages": [AIMessage(content="Drafting complete. Sending to QC.")],
    }
