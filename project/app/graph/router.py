"""
RouterAgent is responsible for serving as the primary entry point for user messages.
It analyzes incoming messages, determines the most suitable specialized agent(s) 
to handle each request, and orchestrates the workflow and data flow between agents accordingly.

Tools:
1. Message Analyzer: Evaluates the content and context of incoming messages to identify user intent.
2. Agent Selector: Chooses the appropriate specialized agent(s) based on the analyzed message.
3. Workflow Orchestrator: Manages the sequence of interactions between the RouterAgent and specialized agents to ensure coherent and efficient responses.
4. Data Flow Manager: Facilitates the transfer of relevant data between agents to maintain context and accuracy in responses.
"""