"""
Abstract Base Class for Notification Providers

This module defines the interface that all notification providers must implement.
Following the Strategy Pattern, each provider (Slack, Email, WhatsApp) is a
separate strategy that can be plugged into the NotificationService.

Design Principles:
- Open/Closed Principle: Open for extension (new providers), closed for modification
- Dependency Inversion: High-level code depends on abstractions, not concrete implementations
- Interface Segregation: Single, focused interface for all notification providers
"""
import logging
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class NotificationPayload:
    """
    Standardized notification data structure.

    All providers receive this payload and adapt it to their specific format.
    This ensures consistency and makes it easy to add new fields without
    modifying individual providers.

    Attributes:
        conversation_id: Unique identifier for the conversation
        title: Subject/title of the notification
        message: Main message body (Markdown supported)
        priority: Priority level ('low', 'normal', 'high', 'urgent')
        metadata: Additional context-specific data
    """

    conversation_id: str
    title: str
    message: str
    priority: str = "normal"  # 'low', 'normal', 'high', 'urgent'
    metadata: Optional[Dict[str, Any]] = None


class NotificationProvider(ABC):
    """
    Abstract base class for all notification providers.

    Each provider (Slack, Email, WhatsApp, etc.) must implement:
    1. send() - Core delivery logic
    2. is_configured() - Configuration validation

    Providers should handle their own errors gracefully and return
    success/failure status without raising exceptions (fail safely).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize provider with configuration.

        Args:
            config: Provider-specific configuration (API keys, URLs, etc.)
        """
        self.config = config or {}
        self.name = self.__class__.__name__.replace("Provider", "")

    @abstractmethod
    def send(self, payload: NotificationPayload) -> bool:
        """
        Send notification using this provider.

        Args:
            payload: Standardized notification data

        Returns:
            bool: True if sent successfully, False otherwise

        Note:
            Implementations should catch exceptions internally and log errors.
            Never raise exceptions from this method (fail safely).
        """
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if provider is properly configured.

        Returns:
            bool: True if all required configuration is present, False otherwise

        Example:
            For Slack: Check if SLACK_WEBHOOK_URL is set
            For Email: Check if SMTP_HOST, SMTP_USER, SMTP_PASS are set
        """
        pass

    def validate_priority(self, priority: str) -> str:
        """
        Validate and normalize priority level.

        Args:
            priority: Priority string from payload

        Returns:
            str: Normalized priority ('low', 'normal', 'high', 'urgent')
        """
        valid_priorities = ["low", "normal", "high", "urgent"]
        normalized = priority.lower()

        if normalized not in valid_priorities:
            logger.warning(
                f"{self.name}: Invalid priority '{priority}', defaulting to 'normal'"
            )
            return "normal"

        return normalized
