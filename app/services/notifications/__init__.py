"""
Notification Service Package

Centralized notification system with multi-provider support.

Quick Start:
    from app.services.notifications import NotificationService

    service = NotificationService()
    service.notify(
        conversation_id="user_123",
        title="Alert",
        message="Something happened",
        priority="high"
    )

Configuration (.env):
    NOTIFICATION_PROVIDERS=slack,email  # Which providers to use
    NOTIFICATION_FALLBACK=true          # Enable fallback on failure

    # Slack
    SLACK_WEBHOOK_URL=https://hooks.slack.com/...

    # Email (Gmail example)
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=your-email@gmail.com
    SMTP_PASSWORD=your-app-password
    SMTP_FROM_EMAIL=notifications@yourcompany.com
    SMTP_TO_EMAIL=support@yourcompany.com

Available Providers:
    - SlackProvider: Send to Slack via webhook
    - EmailProvider: Send via SMTP (Gmail, Outlook, custom)
    - ConsoleProvider: Print to console (dev/testing)
"""
from app.services.notifications.base import NotificationPayload
from app.services.notifications.base import NotificationProvider
from app.services.notifications.providers import ConsoleProvider
from app.services.notifications.providers import SlackProvider
from app.services.notifications.service import NotificationService

__all__ = [
    "NotificationService",
    "NotificationProvider",
    "NotificationPayload",
    "SlackProvider",
    "ConsoleProvider",
]
