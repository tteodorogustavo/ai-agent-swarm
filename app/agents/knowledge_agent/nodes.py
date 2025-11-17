"""
Node Functions for the Knowledge Department Sub-Graph.
"""
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

# Import prompts & schemas
from .prompts import INVESTIGATOR_PROMPT, GRADER_PROMPT, REWRITER_PROMPT, Grade
from .state import KnowledgeState

# Import the "Toolbox"
from app.agents.knowledge_agent.tools import knowledge_agent_tools

# --- 1. Investigate Node (The "Worker") ---

def run_investigator(state: KnowledgeState) -> dict:
    """
    This node runs the correct (modern) `create_agent` runnable
    inside an AgentExecutor.
    """
    
    LLM = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    INVESTIGATOR_AGENT_RUNNABLE = create_agent(
        LLM, 
        knowledge_agent_tools, 
        INVESTIGATOR_PROMPT
    )

    
    # Get the inputs from the state
    question = state["original_question"]
    q_analysis = state.get("query_analysis")
    # The internal memory messages contains the critique/instructions from prior loops
    messages = state["messages"] 
    
    # Invoke the agent
    result = INVESTIGATOR_AGENT_RUNNABLE.invoke({
        "original_question": question,
        "query_analysis": q_analysis,
        "messages": messages,
    })
    
    # Extract evidence
    evidence = []
    if "intermediate_steps" in result:
        for step in result["intermediate_steps"]:
            # step[0] is the tool call, step[1] is the tool output (evidence)
            evidence.append(str(step[1])) 
    
    # Update the state with the findings
    return {
        "context": evidence, 
        "draft_answer": result["output"],
        # We add an AI message to the *internal* memory for clarity
        "messages": [AIMessage(content="Drafting complete. Sending to QC.")],
    }

# --- 2. Grader Node (The "QC Inspector") ---
def run_grader(state: KnowledgeState) -> dict:
    """
    This node inspects the draft from the Investigator.
    It uses a Pydantic schema (`Grade`) for reliable "accept"/"reject" output.
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # Force the LLM to use our Pydantic "Grade" schema
    grader_llm = llm.with_structured_output(Grade)
    
    # Get the inputs from the state
    question = state["original_question"]
    context = state["context"]
    draft = state["draft_answer"]
    
    # Invoke the Grader
    grade: Grade = grader_llm.invoke(
        GRADER_PROMPT.format_messages(
            original_question=question,
            context=context,
            draft_answer=draft
        )
    )
    
    # Update the state with the QC results
    return {
        "latest_grade": grade.grade,
        "latest_critique": grade.critique,
    }

# --- 3. Rewriter Node (The "Fault Analyst") ---
def run_rewriter(state: KnowledgeState) -> dict:
    """
    This node prepares the *next* loop by formatting the critique
    and incrementing the attempt counter.
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # Get inputs from the state
    question = state["original_question"]
    draft = state["draft_answer"]
    critique = state["latest_critique"]
    attempts = state["rewrite_attempts"]
    
    # Use the LLM to format the critique into a new instruction
    new_instruction_msg = llm.invoke(
        REWRITER_PROMPT.format_messages(
            original_question=question,
            draft_answer=draft,
            latest_critique=critique
        )
    )
    
    # Update the state for the *next* loop
    return {
        # Pass the critique to the Investigator's memory
        "messages": [SystemMessage(content=new_instruction_msg.content)], 
        "rewrite_attempts": attempts + 1
    }

# --- 4. Fallback Node (The "Safety Net") ---
def run_fallback(state: KnowledgeState) -> dict:
    """
    This node runs if the QC loop fails (e.g., 3 times).
    It provides a "CERTO" (safe) response to the user.
    """
    critique = state["latest_critique"]
    
    # The final answer is a polite failure message
    fallback_answer = (
        f"I apologize, but I am having trouble finding a "
        f"satisfactory answer. My last attempt was rejected: '{critique}'"
    )
    
    # This prepares the *final* output for the "CEO" (MainGraph)
    return {
        "final_answer": fallback_answer,
        "final_evidence": state["context"] # Return the failed evidence for logging
    }

# --- 5. Accept Node (The "Approval") ---
def run_accept(state: KnowledgeState) -> dict:
    """
    This node runs if the grade is "accept".
    It just moves the draft/context to the *final* state fields
    to be returned to the "CEO" (MainGraph).
    """
    return {
        "final_answer": state["draft_answer"],
        "final_evidence": state["context"]
    }