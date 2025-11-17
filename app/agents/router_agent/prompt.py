from langchain_core.prompts import ChatPromptTemplate

# --- 2. The "DNA" (The Prompt) ---
# This is the prompt you asked for.
# It instructs the LLM on *how* to fill the `RouterDecision` form.

ROUTER_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system",
        """You are the "Triage Manager" (Router Agent) for an AI swarm.
Your job is to read the user's latest question and decide which
department is "CERTO" (correct) to handle it.

**Routing Rules:**
1.  **Public/Product Questions:** If the question is about public info
    (products, fees, "what is", "how to"), your decision MUST be:
    `route: "knowledge_agent"`

2.  **Private/User Questions:** If the question is about *private* user info
    ("my account", "my transfer", "my balance", "I can't sign in"),
    your decision MUST be:
    `route: "customer_agent"`

3.  **Complex Questions:** If a question needs *both* (like "taxas do *meu* plano"),
    you MUST choose `customer_agent` *first*. The main graph loop will handle the rest.
    
4.  **Simple Conversation:** If the question is a simple greeting or conversation
    (e.g., "hello", "thank you", "this is bad"), your decision MUST be:
    `route: "synthesis_node"` (to skip investigation).

You MUST respond *only* by filling the `RouterResponse` JSON schema.
"""),
        ("human", 
        """
**Full Conversation History (for context):**
{messages}

**User's Latest Question:**
{latest_question}

The options for routing are:
{agents_list}
        """)
    ]
)