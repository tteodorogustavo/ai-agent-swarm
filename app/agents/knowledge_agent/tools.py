"""
The "Toolbox" for the Knowledge Department.

This file defines all tools that the Knowledge Agent (Investigator)
can use. It imports the pre-built RAG retriever from the RAG service
and initializes the Tavily web search tool.

This keeps our agent logic clean and decoupled from tool implementation.
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any
from typing import Dict

from langchain_core.tools import Tool
from langchain_tavily import TavilySearch

from app.services.rag.rag_service import create_rag_retriever
# 1. Import the RAG Retriever from our service
# This function (`create_rag_retriever`) returns the *entire*
# advanced LCEL chain we built (Query Constructor + Retriever).

# --- Tool 1: RAG ---

# We initialize our RAG *once* when this module loads.
rag_retriever_chain = create_rag_retriever()


# Wrapper with validation and timeout for the RAG retriever
def _rag_tool_func(payload: Any, timeout: float = 10.0) -> Dict[str, Any]:
    """Safe wrapper around the RAG chain invocation.

    Accepts either:
    - A dict with key `question` (str): {"question": "..."}
    - A string directly (the question)

    Returns chain result or a friendly error dict on validation/timeout/exception.
    """
    logging.debug(
        "_rag_tool_func called with payload type: %s, value: %s",
        type(payload).__name__,
        payload,
    )

    # Handle string input (direct question)
    if isinstance(payload, str):
        question = payload
    elif isinstance(payload, dict):
        # Extract question from dict
        question = payload.get("question")
        if not question or not isinstance(question, str):
            logging.error("Invalid or missing 'question' key: %s", question)
            return {
                "error": "invalid_input",
                "message": "'question' must be a non-empty string",
            }
    else:
        logging.error("Invalid payload type: %s", type(payload))
        return {
            "error": "invalid_input",
            "message": f"payload must be a dict or string, got {type(payload).__name__}",
        }

    try:
        logging.info(f"RAG tool executing query: {question[:100]}...")
        with ThreadPoolExecutor(max_workers=1) as ex:
            # The retriever expects a STRING, not a dict
            fut = ex.submit(lambda: rag_retriever_chain.invoke(question))
            result = fut.result(timeout=timeout)
            logging.info(
                f"RAG tool completed successfully, retrieved {len(result)} documents"
            )

            # Format documents as a readable string for the LLM
            context = "\n\n---\n\n".join(
                [
                    f"Source: {doc.metadata.get('source', 'Unknown')}\n{doc.page_content}"
                    for doc in result
                ]
            )

            return {"context": context, "num_docs": len(result)}
    except FuturesTimeoutError:
        logging.exception("RAG tool timed out")
        return {"error": "timeout", "message": "RAG retriever timed out"}
    except Exception as e:
        logging.exception("RAG tool error: %s", str(e))
        return {"error": "internal_error", "message": f"RAG retriever failed: {str(e)}"}


# We must wrap our LCEL chain in a `Tool` object so the agent can use it.
rag_tool = Tool(
    name="infinitepay_product_search",
    func=_rag_tool_func,
    description=(
        "ONLY for InfinitePay-specific questions (maquininha, conta digital, cartões, PIX via InfinitePay). "
        "DO NOT use for general knowledge questions (e.g., 'What is Open Banking?'). "
        "Input can be: (1) a dict like {'question': '...'} OR (2) a string with the question directly. "
        "Returns dict with answer or error info."
    ),
)


# --- Tool 2: Web Search ---
_tavily = TavilySearch(max_results=5)


def _web_search_func(query: Any, timeout: float = 5.0) -> Dict[str, Any]:
    """Safe wrapper around TavilySearch.

    Accepts either:
    - A string directly (the query)
    - A dict with key `query` (str): {"query": "..."}

    Returns dict with results or friendly error.
    """
    logging.debug(
        "_web_search_func called with type: %s, value: %s", type(query).__name__, query
    )

    # Handle dict input (extract query string)
    if isinstance(query, dict):
        query = query.get("query", "")

    # Validate it's now a string
    if not isinstance(query, str) or not query.strip():
        logging.error("Invalid query after normalization: %s", query)
        return {"error": "invalid_input", "message": "query must be a non-empty string"}

    try:
        logging.info(f"Web search executing query: {query[:100]}...")
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(lambda: _tavily.run(query))
            result = fut.result(timeout=timeout)
            logging.info("Web search completed successfully")
            return {"results": result}
    except FuturesTimeoutError:
        logging.exception("web_search timed out")
        return {"error": "timeout", "message": "web search timed out"}
    except Exception as e:
        logging.exception("web_search error: %s", str(e))
        return {"error": "internal_error", "message": f"web search failed: {str(e)}"}


web_search_tool = Tool(
    name="web_search",
    func=_web_search_func,
    description=(
        "Use this tool for GENERAL knowledge questions or when you need external information. "
        "This should be your PRIMARY tool for non-InfinitePay-specific questions. "
        "Input can be: (1) a string query directly OR (2) a dict like {'query': '...'}. "
        "Returns dict with search results or error info."
    ),
)


# --- The Final Toolbox ---
# This is the list our Knowledge Agent's AgentExecutor will use.
knowledge_agent_tools = [rag_tool, web_search_tool]
