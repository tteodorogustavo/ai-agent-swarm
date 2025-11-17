"""
The Synthesis Node (The "Spokesperson").

This node is the final step in the MainGraph.
Its job is to take all the collected evidence (`final_context`)
and the conversation history (`messages`) and use the SYNTHESIS_PROMPT
to generate the final, polished response for the user.
"""
import logging
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage

from app.graph.main_state import MainState
from .prompt import SYNTHESIS_PROMPT

def synthesis_node(state: MainState) -> dict:
    """
    The main synthesis function.
    Calls an LLM to generate the final, polished response.
    """
    logging.info("--- MainGraph: Calling Synthesis Node (Spokesperson) ---")

    # 1. Initialize the "CERTO" LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

    # 2. Build the "Spokesperson" Chain
    synthesis_chain = SYNTHESIS_PROMPT | llm | StrOutputParser()
    
    # 3. Get the inputs from the "Master Clipboard" (MainState)
    messages = state["messages"]
    context = "\n---\n".join(state["final_context"]) # Join all evidence into one block
    
    # 4. Invoke the "Spokesperson"
    final_response = synthesis_chain.invoke({
        "messages": messages,
        "context": context
    })
    
    logging.info(f"Synthesis Node: Generated final response.")

    # 5. Return the final updates for the "Master Clipboard" (MainState)
    return {
        "final_response": final_response,
        # We also add the final answer to the *master* memory,
        # so the *next* turn of the conversation sees it.
        "messages": [AIMessage(content=final_response)]
    }