"""
Human Escalation Node

This node handles cases where the Knowledge Agent cannot provide a satisfactory
answer after maximum retry attempts. It notifies human support via configured
notification channels (Slack, Email, etc.) and prepares a user-facing message.

Integration: Uses NotificationService for multi-channel alerting, enabling
human-in-the-loop intervention for complex queries.

Architecture: Follows Dependency Injection pattern - notification logic is
abstracted, making it easy to add/change notification providers.
"""
import logging
from typing import Any
from typing import Dict

from langchain_core.messages import AIMessage

from app.agents.knowledge_agent.state import KnowledgeState
from app.services.notifications import NotificationService

logger = logging.getLogger(__name__)


def run_human_escalation(state: KnowledgeState) -> Dict[str, Any]:
    """
    Escalate conversation to human support via multi-channel notifications.

    Workflow:
    1. Extract conversation context (ID, question, evidence attempts)
    2. Build structured notification message
    3. Send via configured providers (Slack, Email, etc.) with fallback
    4. Return standard user-facing message for Synthesis Agent

    Args:
        state (KnowledgeState): Current state with conversation history

    Returns:
        dict: Updated state with final_answer for user and messages for logging
    """
    logger.warning("--- HUMAN ESCALATION: Notifying support team ---")

    # Extract context from state
    conversation_id = state.get("user_id", "unknown")
    original_question = state.get("original_question", "N/A")
    messages = state.get("messages", [])
    draft_answer = state.get("draft_answer", "No draft generated")
    context = state.get("context", [])
    tools_called = state.get("tools_called", [])

    # Calculate retry attempts
    retry_attempts = sum(1 for m in messages if "QC Feedback" in str(m.content))

    # Extract ALL quality control critiques from message history
    critiques = [
        str(msg.content).replace("QC Feedback: ", "")
        for msg in messages
        if "QC Feedback:" in str(msg.content)
    ]

    # Format critiques for display
    critiques_section = ""
    if critiques:
        critiques_list = "\n".join(
            [f"   {i+1}. {critique}" for i, critique in enumerate(critiques)]
        )
        critiques_section = f"""
**Quality Control Issues Identified:**
{critiques_list}

**Why This Failed:**
The AI attempted to answer {retry_attempts + 1} times but could not meet quality standards.
Each attempt was rejected for the reasons listed above.
"""
    else:
        critiques_section = """
**Quality Control Issues:**
No specific feedback recorded (system error or edge case).
"""

    # Build enhanced notification message
    notification_message = f"""
**Question:** {original_question}

**Attempts Made:** {retry_attempts + 1} (max reached)
**Tools Used:** {', '.join(tools_called) if tools_called else 'None'}

**Last Draft Answer:**
```
{draft_answer[:500]}{'...' if len(draft_answer) > 500 else ''}
```

{critiques_section}

**Evidence Collected:** {len(context)} documents retrieved

**Action Required:**
1. Review the quality issues listed above to understand what's missing or incorrect
2. Access full conversation via dashboard using ID: `{conversation_id}`
3. Provide a personalized, expert response that addresses the identified gaps

**Next Steps:**
The customer is waiting for expert assistance. Please review the question, critiques, and context, then respond through the support portal.
"""

    # Send notification via NotificationService
    notification_service = NotificationService()

    success = notification_service.notify(
        conversation_id=conversation_id,
        title="Human Support Needed - Complex Query",
        message=notification_message,
        priority="high",
        metadata={
            "retry_count": retry_attempts + 1,
            "tools_used": ", ".join(tools_called) if tools_called else "None",
            "evidence_count": len(context),
            "original_question": original_question[:100] + "..."
            if len(original_question) > 100
            else original_question,
        },
    )

    if success:
        logger.info(
            f"Notification sent successfully for conversation {conversation_id}"
        )
    else:
        logger.error(
            f"All notification channels failed for conversation {conversation_id}"
        )

    # Prepare user-facing message
    user_message = (
        "Identificamos que sua pergunta requer atenção especializada. "
        "Nosso time de suporte entrará em contato em breve para resolver sua dúvida diretamente. "
        "Agradecemos sua paciência!"
    )

    logger.info("--- HUMAN ESCALATION: Returning fallback message to user ---")

    # CRITICAL: Signal that we're done (prevents infinite loop back to router)
    return {
        "final_answer": user_message,
        "final_evidence": [
            {
                "type": "human_escalation",
                "conversation_id": conversation_id,
                "status": "escalated_to_support",
                "notification_sent": success,
            }
        ],
        "grade_decision": "escalate",
        "route": "synthesis_agent",  # Signal to Main Graph: "I'm done, go to synthesis"
        "messages": [
            AIMessage(
                content=f"Escalated to human support. Conversation ID: {conversation_id}"
            )
        ],
    }
