"""
Notification Service - Orchestrator

Centralized notification system with multi-provider support.

Features:
- Multiple simultaneous channels (Slack + Email + Console)
- Automatic fallback (if primary fails, tries secondary)
- Priority-based routing
- Configurable via environment variables

Configuration (.env):
- NOTIFICATION_PROVIDERS: Comma-separated list of providers to use
  Example: "slack,email" or "console" (dev) or "slack,email,console"

- NOTIFICATION_FALLBACK: Enable fallback to next provider if one fails
  Example: "true" (default) or "false"

Usage:
    from app.services.notifications import NotificationService

    service = NotificationService()
    service.notify(
        conversation_id="user_123",
        title="Human Support Needed",
        message="Complex query requires expert attention...",
        priority="high"
    )
"""
import logging
import os
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from app.services.notifications.base import NotificationPayload
from app.services.notifications.base import NotificationProvider
from app.services.notifications.providers import ConsoleProvider
from app.services.notifications.providers import SlackProvider

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Centralized notification orchestrator.

    Manages multiple notification providers, handles fallbacks, and provides
    a unified interface for sending notifications across different channels.

    Design Pattern: Facade + Strategy Pattern
    - Facade: Simplifies complex multi-provider orchestration
    - Strategy: Each provider is a pluggable strategy

    Note: EmailProvider not yet implemented. Available providers:
        - slack: SlackProvider (requires SLACK_WEBHOOK_URL)
        - console: ConsoleProvider (always available)
    """

    # Registry of available providers
    AVAILABLE_PROVIDERS = {"slack": SlackProvider, "console": ConsoleProvider}

    def __init__(
        self,
        providers: Optional[List[str]] = None,
        enable_fallback: bool = True,
        custom_providers: Optional[Dict[str, NotificationProvider]] = None,
    ):
        """
        Initialize notification service.

        Args:
            providers: List of provider names to use (e.g., ["slack", "email"]).
                      If None, loads from NOTIFICATION_PROVIDERS env var.
                      Defaults to ["console"] if not configured.

            enable_fallback: If True, tries next provider if one fails.
                           Can be overridden by NOTIFICATION_FALLBACK env var.

            custom_providers: Optional dict of custom provider instances.
                            Useful for testing or custom integrations.
        """
        # Load configuration
        self.enable_fallback = self._parse_bool_env(
            "NOTIFICATION_FALLBACK", enable_fallback
        )

        # Determine which providers to use
        # If custom_providers are given and providers is None, use ONLY custom providers
        if providers is None and not custom_providers:
            providers_env = os.getenv("NOTIFICATION_PROVIDERS", "console")
            providers = [p.strip() for p in providers_env.split(",")]
        elif providers is None and custom_providers:
            # Using only custom providers (testing scenario)
            providers = []

        # Initialize providers
        self.providers: List[NotificationProvider] = []

        # Add custom providers first (for testing/overrides)
        if custom_providers:
            self.providers.extend(custom_providers.values())

        # Add configured providers from registry
        for provider_name in providers:
            provider_name = provider_name.lower().strip()

            if provider_name in self.AVAILABLE_PROVIDERS:
                provider_class = self.AVAILABLE_PROVIDERS[provider_name]
                provider_instance = provider_class()

                # Only add if configured (except Console, which is always available)
                if provider_instance.is_configured() or provider_name == "console":
                    self.providers.append(provider_instance)
                    logger.info(
                        f"NotificationService: Registered {provider_name} provider"
                    )
                else:
                    logger.warning(
                        f"NotificationService: {provider_name} provider not configured, skipping"
                    )
            else:
                logger.error(
                    f"NotificationService: Unknown provider '{provider_name}', skipping"
                )

        # Fallback to console if no providers configured
        if not self.providers:
            logger.warning(
                "NotificationService: No providers configured, using console fallback"
            )
            self.providers.append(ConsoleProvider())

        logger.info(
            f"NotificationService initialized with {len(self.providers)} provider(s): "
            f"{[p.name for p in self.providers]}"
        )

    def notify(
        self,
        conversation_id: str,
        title: str,
        message: str,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send notification through configured providers.

        Args:
            conversation_id: Unique conversation identifier
            title: Notification title/subject
            message: Main message body
            priority: Priority level ('low', 'normal', 'high', 'urgent')
            metadata: Optional additional context

        Returns:
            bool: True if at least one provider succeeded, False if all failed

        Example:
            success = service.notify(
                conversation_id="user_123",
                title="Human Support Needed",
                message="Complex query requires expert...",
                priority="high",
                metadata={"retry_count": 3, "tools_used": "rag,web_search"}
            )
        """
        # Build payload
        payload = NotificationPayload(
            conversation_id=conversation_id,
            title=title,
            message=message,
            priority=priority,
            metadata=metadata,
        )

        logger.info(
            f"NotificationService: Sending notification for conversation {conversation_id} "
            f"via {len(self.providers)} provider(s)"
        )

        # Track results
        results = []

        # Try each provider
        for provider in self.providers:
            logger.debug(f"Trying provider: {provider.name}")

            success = provider.send(payload)
            results.append(success)

            if success:
                logger.info(f"✅ {provider.name} sent successfully")

                # If fallback disabled and one succeeded, stop here
                if not self.enable_fallback:
                    break
            else:
                logger.warning(f"❌ {provider.name} failed")

                # If fallback enabled, continue to next provider
                if self.enable_fallback:
                    logger.info("Trying next provider (fallback enabled)...")
                else:
                    break

        # Check if at least one succeeded
        overall_success = any(results)

        if overall_success:
            logger.info(f"Notification sent successfully for {conversation_id}")
        else:
            logger.error(f"All notification providers failed for {conversation_id}")

        return overall_success

    def _parse_bool_env(self, env_var: str, default: bool) -> bool:
        """
        Parse boolean from environment variable.

        Args:
            env_var: Environment variable name
            default: Default value if not set

        Returns:
            bool: Parsed boolean value
        """
        value = os.getenv(env_var)

        if value is None:
            return default

        return value.lower() in ("true", "1", "yes", "on")

    def get_active_providers(self) -> List[str]:
        """
        Get list of active provider names.

        Returns:
            List[str]: Names of currently active providers
        """
        return [p.name for p in self.providers]
