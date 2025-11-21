"""
Slack Notification Provider

Sends notifications to Slack channels via incoming webhooks.

Configuration (via environment variables):
- SLACK_WEBHOOK_URL: Webhook URL from Slack (required)

Setup Instructions:
1. Go to https://api.slack.com/apps
2. Create new app → "Incoming Webhooks"
3. Activate webhooks and add to workspace
4. Copy webhook URL to .env as SLACK_WEBHOOK_URL
"""
import logging
import os
from typing import Any
from typing import Dict
from typing import Optional

import requests

from app.services.notifications.base import NotificationPayload
from app.services.notifications.base import NotificationProvider

logger = logging.getLogger(__name__)


class SlackProvider(NotificationProvider):
    """
    Slack notification provider using incoming webhooks.

    Converts NotificationPayload to Slack-formatted message with:
    - Title as bold header
    - Priority emoji (🔵 low, ⚪ normal, 🟡 high, 🔴 urgent)
    - Markdown-formatted message body
    - Metadata as structured fields
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Slack provider.

        Args:
            config: Optional config dict. If not provided, loads from environment:
                - webhook_url: Slack webhook URL (or SLACK_WEBHOOK_URL env var)
        """
        super().__init__(config)
        self.webhook_url = self.config.get(
            "webhook_url", os.getenv("SLACK_WEBHOOK_URL", "")
        )

    def is_configured(self) -> bool:
        """Check if Slack webhook URL is configured."""
        return bool(
            self.webhook_url and self.webhook_url.startswith("https://hooks.slack.com")
        )

    def send(self, payload: NotificationPayload) -> bool:
        """
        Send notification to Slack.

        Args:
            payload: Notification data

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("SlackProvider: Not configured (missing SLACK_WEBHOOK_URL)")
            return False

        try:
            # Build Slack message
            slack_message = self._format_message(payload)

            # Send POST request
            response = requests.post(
                self.webhook_url,
                json=slack_message,
                timeout=5,  # 5 second timeout
            )

            if response.status_code == 200:
                logger.info(
                    f"✅ SlackProvider: Sent notification for conversation {payload.conversation_id}"
                )
                return True
            else:
                logger.error(
                    f"❌ SlackProvider: HTTP {response.status_code} - {response.text}"
                )
                return False

        except requests.RequestException as e:
            logger.error(f"❌ SlackProvider: Request failed - {str(e)}")
            return False
        except Exception as e:
            logger.error(
                f"❌ SlackProvider: Unexpected error - {str(e)}", exc_info=True
            )
            return False

    def _format_message(self, payload: NotificationPayload) -> Dict[str, Any]:
        """
        Format NotificationPayload as Slack message.

        Args:
            payload: Notification data

        Returns:
            dict: Slack-formatted message payload
        """
        # Priority emoji mapping
        priority_emoji = {"low": "🔵", "normal": "⚪", "high": "🟡", "urgent": "🔴"}

        priority = self.validate_priority(payload.priority)
        emoji = priority_emoji.get(priority, "⚪")

        # Build message text
        text = f"{emoji} *{payload.title}*\n\n{payload.message}"

        # Add metadata if present
        if payload.metadata:
            text += "\n\n*Additional Context:*\n"
            for key, value in payload.metadata.items():
                # Format key: remove underscores, capitalize
                formatted_key = key.replace("_", " ").title()
                text += f"• *{formatted_key}:* {value}\n"

        return {
            "text": text,
            "username": "InfinitePay Agent System",
            "icon_emoji": ":robot_face:",
        }
