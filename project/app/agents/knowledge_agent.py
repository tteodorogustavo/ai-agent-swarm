"""
Knowledge Agent responsible for handling queries that require information retrieval
and generation, primarily about InfinitePay's products and services.
Utilizes a Retrieval Augmented Generation (RAG) approach to ensure responses
are grounded in content sourced from the company's website (https://www.infinitepay.io 
and its subpages). Supports both internal and external information retrieval, 
including web search for general-purpose questions, 
leveraging a curated set of official webpages as the knowledge base.
Tools:
1. RAG Tool: Implements Retrieval Augmented Generation to fetch and generate responses
   based on the knowledge base derived from InfinitePay's official website.
2. Web Search Tool: Enables the agent to perform web searches for answering general-purpose questions.
3. Content Summarizer: Summarizes lengthy documents or web pages to provide concise answers.
4. RAG Administrator: Manages and updates the knowledge base to ensure the information remains current and relevant.
"""