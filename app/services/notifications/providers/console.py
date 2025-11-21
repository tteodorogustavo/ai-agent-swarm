"""
Console Notification Provider

Prints notifications to console/logs (useful for development and testing).

This provider is always configured and never fails, making it perfect for:
- Local development
- CI/CD pipelines
- Testing without external dependencies
"""
import logging

from app.services.notifications.base import NotificationPayload
from app.services.notifications.base import NotificationProvider

logger = logging.getLogger(__name__)


class ConsoleProvider(NotificationProvider):
    """
    Console notification provider for development and testing.

    Logs notifications to console with formatted output.
    Always configured, never fails (returns True).
    """

    def is_configured(self) -> bool:
        """Console provider is always configured."""
        return True

    def send(self, payload: NotificationPayload) -> bool:
        """
        Print notification to console/logs.

        Args:
            payload: Notification data

        Returns:
            bool: Always True (never fails)
        """
        try:
            separator = "=" * 80

            # Build formatted output
            output = f"\n{separator}\n"
            output += f"📢 NOTIFICATION [{payload.priority.upper()}]\n"
            output += f"{separator}\n"
            output += f"Title: {payload.title}\n"
            output += f"Conversation ID: {payload.conversation_id}\n"
            output += f"{separator}\n"
            output += f"{payload.message}\n"

            if payload.metadata:
                output += f"{separator}\n"
                output += "Metadata:\n"
                for key, value in payload.metadata.items():
                    formatted_key = key.replace("_", " ").title()
                    output += f"  • {formatted_key}: {value}\n"

            output += f"{separator}\n"

            # Log at appropriate level based on priority
            if payload.priority == "urgent":
                logger.critical(output)
            elif payload.priority == "high":
                logger.error(output)
            elif payload.priority == "normal":
                logger.warning(output)
            else:  # low
                logger.info(output)

            return True

        except Exception as e:
            # Even if formatting fails, log error and return True (fail safely)
            logger.error(f"ConsoleProvider: Error formatting message - {str(e)}")
            return True
