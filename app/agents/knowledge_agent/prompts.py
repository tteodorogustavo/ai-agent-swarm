"""
Prompts for the Knowledge Agent Sub-Graph.

This file defines the system prompts and Pydantic schemas (forms)
that our agent nodes (Investigator, Grader, Rewriter) will use.
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field
from typing import Literal

# --- 1. Investigation Node (ReAct Agent) Prompt ---
# This prompt uses Chain of Thought ("...step-by-step") and ReAct principles.
# It is designed for the modern `langchain.agents.create_agent` factory.

system_prompt = """You are a "CERTO" (Correct) specialist investigator for InfinitePay.
Your mission is to find the most accurate and up-to-date information.

You have TWO tools:
1. `infinitepay_product_search`: Use this tool FIRST. It searches InfinitePay's internal knowledge base.
   **Crucial: The input for this tool MUST be a dictionary: {{"question": "the user's original question"}}**
2. `web_search`: Use this tool ONLY if `infinitepay_product_search` finds nothing, OR for general knowledge.

**Your Plan (Chain of Thought):**
1.  **Analyze:** Look at the `original_question` and any `CRITICAL_FEEDBACK`.
2.  **Act:** Call the correct tool.
3.  **Observe:** Look at the tool's output.
4.  **Conclude:** Formulate a "Draft Answer" based *only* on the observed context.
5.  **Finalize:** Provide your "Draft Answer" and the `context` (evidence) you gathered.
"""

INVESTIGATOR_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("placeholder", "{messages}"), # Internal memory (for critiques)
        ("human", 
        """
**Original Question:** {original_question}
**Query Analysis (from Router):**
{query_analysis}
        """),
        MessagesPlaceholder(variable_name="agent_scratchpad"), # The ReAct "notepad"
    ]
)

# --- 2. Grader Node (QC Inspector) Prompt & Schema ---

class Grade(BaseModel):
    """The QC Inspector's official grading form."""
    grade: Literal["accept", "reject"] = Field(
        ..., 
        description="The binary 'stamp': 'accept' if the answer is perfect, 'reject' if it has any flaws."
    )
    critique: str = Field(
        ..., 
        description="A mandatory, constructive critique explaining *why* the draft was rejected. (If accepted, write 'N/A')."
    )

GRADER_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system",
        """You are a "CERTO" (Correct) Quality Control (QC) Inspector.
Your job is to validate a 'Draft Answer' against the 'Original Question' and the 'Evidence' (Context).

**Your Rules:**
1.  **Hallucination Check:** The `draft_answer` MUST be 100% grounded in the `context`. If it mentions facts not in the context, it is a "reject".
2.  **Completeness Check:** The `draft_answer` MUST fully and directly answer the `original_question`. If it misses parts of the question, it is a "reject".
3.  **Relevance Check:** The `context` itself MUST be relevant to the `original_question`. If the evidence is irrelevant, the answer is also a "reject".

You must respond *only* by filling the `Grade` JSON schema.
"""),
        ("human",
        """
**Original Question:**
{original_question}

**Evidence (Context) Gathered:**
{context}

**Draft Answer to Grade:**
{draft_answer}
        """)
    ]
)

# --- 3. Rewriter Node (Fault Analyst) Prompt ---
REWRITER_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system",
        """You are a "Fault Analyst". Your job is to take the 'Critique' from the QC Inspector
and format it as a *new instruction* for the Investigator, so he can try again.
Make the feedback encouraging but firm.
"""),
        ("human",
        """
**Original Question:**
{original_question}

**Rejected Draft:**
{draft_answer}

**QC Inspector's Critique:**
{latest_critique}

**Your Instruction for the next attempt (CRITICAL_FEEDBACK):**
(Example: "CRITICAL_FEEDBACK: Your last attempt was rejected. The critique was: 'Information is outdated'. Please try again, but this time, you MUST use the `web_search` tool to find current data.")
        """)
    ]
)