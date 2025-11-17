"""
The "Toolbox" for the Knowledge Department.

This file defines all tools that the Knowledge Agent (Investigator)
can use. It imports the pre-built RAG retriever from the RAG service
and initializes the Tavily web search tool.

This keeps our agent logic clean and decoupled from tool implementation.
"""
from langchain_tavily import TavilySearch
from langchain_core.tools import Tool

# 1. Import the "Librarian" (RAG Retriever) from our service
# This function (`create_rag_retriever`) returns the *entire*
# advanced LCEL chain we built (Query Constructor + Retriever).
from app.services.rag_service import create_rag_retriever

# --- Tool 1: The "Internal Library" (RAG) ---

# We initialize our RAG "Librarian" *once* when this module loads.
rag_retriever_chain = create_rag_retriever()

# We must wrap our LCEL chain in a `Tool` object so the agent can use it.
# The `name` and `description` are *critical* for the agent's LLM
# to make the "CERTO" (correct) decision.
rag_tool = Tool(
    name="infinitepay_product_search",
    # The `func` of the agent now calls our chain's `invoke` method.
    func=rag_retriever_chain.invoke, 
    description=(
        "Use this tool FIRST. It is an expert on InfinitePay's products, "
        "services, fees, and internal knowledge. "
        "The input *must* be a dictionary, e.g.: {'question': 'user question here'}"
    )
)


# --- Tool 2: The "External Investigator" (Web Search) ---
tavily_tool = TavilySearch(max_results=5)
tavily_tool.name = "web_search"
tavily_tool.description = (
    "Use this tool ONLY if `infinitepay_product_search` finds no relevant "
    "information OR if the user asks for general-purpose knowledge "
    "(e.g., 'latest soccer game', 'news', 'weather')."
)


# --- The Final Toolbox ---
# This is the list our Knowledge Agent's AgentExecutor will use.
knowledge_agent_tools = [rag_tool, tavily_tool]