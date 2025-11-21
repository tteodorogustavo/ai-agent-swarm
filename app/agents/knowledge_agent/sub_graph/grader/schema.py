"""
Grader Schema

Pydantic schema for the QC Inspector's grading form.
Simplified: binary accept/reject only (escalation logic handled in node).
"""
from typing import Literal

from pydantic import BaseModel
from pydantic import Field


class Grade(BaseModel):
    """
    The QC Inspector's official grading form.

    Returns binary decision (accept/reject). The node function handles
    retry counting and escalation logic.
    """

    grade: Literal["accept", "reject"] = Field(
        ...,
        description="The binary 'stamp': 'accept' if the answer is perfect, 'reject' if it has any flaws.",
    )
    critique: str = Field(
        ...,
        description="A mandatory, constructive critique explaining *why* the draft was rejected. (If accepted, write 'N/A').",
    )
