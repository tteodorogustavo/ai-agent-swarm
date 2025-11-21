"""
Notification Providers Package

Available providers:
- SlackProvider: Send to Slack via webhook
- ConsoleProvider: Print to console (dev/testing)

Note:
- EmailProvider: Not yet implemented (TODO)
- WhatsAppProvider: Not yet implemented (TODO)
"""
from .console import ConsoleProvider
from .slack import SlackProvider

__all__ = [
    "SlackProvider",
    "ConsoleProvider",
]
