"""
Pydantic Schemas for RAG Query Construction (The "Digital Form")

This file defines the *advanced* schemas that the Router LLM
will be forced to fill to perform "Query Enrichment".

These schemas are the core of our "Query Construction" logic, ensuring
reliable and structured output from the LLM.
"""

from pydantic import BaseModel, Field
from typing import Optional, List

class QueryFilter(BaseModel):
    """
    The specific metadata filter (the 'exact address').
    The LLM will fill this only if a topic is explicitly mentioned.
    """
    topic: str = Field(
        ..., 
        description="The topic to filter on (e.g., 'maquininha', 'pix', 'cartao')."
    )

class QueryAnalysis(BaseModel):
    """
    The main "Analysis Form" the Router fills.
    It contains all the "ammunition" for the Knowledge Agent.
    """
    
    rewritten_query: str = Field(
        ...,
        description=(
            "A standalone, keyword-rich semantic search query. "
            "This query is optimized for vector search (RAG)."
        )
    )
    
    filter: Optional[QueryFilter] = Field(
        None,
        description=(
            "The metadata filter. Must be used *only* if the user's query "
            "explicitly narrows the scope to a specific topic."
        )
    )
    
    keywords: List[str] = Field(
        default_factory=list,
        description="A list of 3-5 critical keywords extracted from the query."
    )
    
    hyde_query: str = Field(
        ...,
        description=(
            "A hypothetical document (HyDE). A short paragraph generated from "
            "the query that represents a *perfect* answer, used to find "
            "semantically similar documents."
        )
    )

    summary: str = Field(
        ...,
        description="A one-sentence summary of the user's core intent."
    )