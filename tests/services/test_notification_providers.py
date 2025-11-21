"""
Tests for Notification Providers

Tests cover:
- SlackProvider
- ConsoleProvider

Note: EmailProvider tests removed as EmailProvider is not yet implemented.
"""
from unittest.mock import Mock
from unittest.mock import patch

from app.services.notifications.base import NotificationPayload
from app.services.notifications.providers import ConsoleProvider
from app.services.notifications.providers import SlackProvider


class TestSlackProvider:
    """Test SlackProvider functionality."""

    def test_is_configured_with_valid_webhook(self):
        """Should be configured when valid webhook URL is set."""
        provider = SlackProvider(
            config={"webhook_url": "https://hooks.slack.com/services/TEST/WEBHOOK/URL"}
        )

        assert provider.is_configured() is True

    def test_is_not_configured_with_invalid_webhook(self):
        """Should NOT be configured with invalid webhook URL."""
        provider = SlackProvider(
            config={"webhook_url": "https://example.com/not-slack"}
        )

        assert provider.is_configured() is False

    def test_is_not_configured_with_empty_webhook(self):
        """Should NOT be configured with empty webhook URL."""
        provider = SlackProvider(config={"webhook_url": ""})

        assert provider.is_configured() is False

    @patch("requests.post")
    def test_send_success(self, mock_post):
        """Should send successfully when webhook returns 200."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        provider = SlackProvider(
            config={"webhook_url": "https://hooks.slack.com/services/TEST/WEBHOOK/URL"}
        )

        payload = NotificationPayload(
            conversation_id="test_123",
            title="Test Title",
            message="Test message",
            priority="normal",
        )

        result = provider.send(payload)

        assert result is True
        mock_post.assert_called_once()

        # Verify payload structure
        call_kwargs = mock_post.call_args[1]
        assert "json" in call_kwargs
        assert "text" in call_kwargs["json"]

    @patch("requests.post")
    def test_send_failure_http_error(self, mock_post):
        """Should fail gracefully when webhook returns error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        provider = SlackProvider(
            config={"webhook_url": "https://hooks.slack.com/services/TEST/WEBHOOK/URL"}
        )

        payload = NotificationPayload(
            conversation_id="test_123", title="Test", message="Test", priority="normal"
        )

        result = provider.send(payload)

        assert result is False

    @patch("requests.post")
    def test_send_failure_network_error(self, mock_post):
        """Should fail gracefully on network errors."""
        import requests

        mock_post.side_effect = requests.RequestException("Network error")

        provider = SlackProvider(
            config={"webhook_url": "https://hooks.slack.com/services/TEST/WEBHOOK/URL"}
        )

        payload = NotificationPayload(
            conversation_id="test_123", title="Test", message="Test", priority="normal"
        )

        result = provider.send(payload)

        assert result is False

    @patch("requests.post")
    def test_send_includes_priority_emoji(self, mock_post):
        """Should include priority emoji in message."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        provider = SlackProvider(
            config={"webhook_url": "https://hooks.slack.com/services/TEST/WEBHOOK/URL"}
        )

        # Test different priorities
        priorities = {"low": "🔵", "normal": "⚪", "high": "🟡", "urgent": "🔴"}

        for priority, emoji in priorities.items():
            payload = NotificationPayload(
                conversation_id="test", title="Test", message="Test", priority=priority
            )

            provider.send(payload)

            call_kwargs = mock_post.call_args[1]
            message_text = call_kwargs["json"]["text"]
            assert emoji in message_text

    @patch("requests.post")
    def test_send_includes_metadata(self, mock_post):
        """Should format metadata in message."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        provider = SlackProvider(
            config={"webhook_url": "https://hooks.slack.com/services/TEST/WEBHOOK/URL"}
        )

        payload = NotificationPayload(
            conversation_id="test",
            title="Test",
            message="Test",
            priority="normal",
            metadata={"user_id": "user_123", "retry_count": 3},
        )

        provider.send(payload)

        call_kwargs = mock_post.call_args[1]
        message_text = call_kwargs["json"]["text"]
        assert "user_123" in message_text
        assert "3" in str(message_text)


# EmailProvider tests removed - EmailProvider not yet implemented
# TODO: Add EmailProvider tests when EmailProvider is implemented


class TestConsoleProvider:
    """Test ConsoleProvider functionality."""

    def test_is_always_configured(self):
        """Console provider should always be configured."""
        provider = ConsoleProvider()

        assert provider.is_configured() is True

    def test_send_always_succeeds(self):
        """Console provider should always succeed."""
        provider = ConsoleProvider()

        payload = NotificationPayload(
            conversation_id="test_123",
            title="Test",
            message="Test message",
            priority="normal",
        )

        result = provider.send(payload)

        assert result is True

    @patch("app.services.notifications.providers.console.logger")
    def test_send_logs_message(self, mock_logger):
        """Should log notification to console."""
        provider = ConsoleProvider()

        payload = NotificationPayload(
            conversation_id="test_123",
            title="Test Title",
            message="Test message",
            priority="normal",
        )

        provider.send(payload)

        # Should have logged (at warning level for normal priority)
        assert mock_logger.warning.called

    @patch("app.services.notifications.providers.console.logger")
    def test_send_uses_different_log_levels(self, mock_logger):
        """Should use different log levels based on priority."""
        provider = ConsoleProvider()

        # Test urgent -> critical
        payload = NotificationPayload(
            conversation_id="test", title="Test", message="Test", priority="urgent"
        )
        provider.send(payload)
        assert mock_logger.critical.called

        # Reset
        mock_logger.reset_mock()

        # Test high -> error
        payload = NotificationPayload(
            conversation_id="test", title="Test", message="Test", priority="high"
        )
        provider.send(payload)
        assert mock_logger.error.called

    def test_send_handles_formatting_errors(self):
        """Should not fail even if formatting fails."""
        provider = ConsoleProvider()

        # Payload with None values that might cause formatting issues
        payload = NotificationPayload(
            conversation_id="test",
            title="Test",
            message="Test",
            priority="normal",
            metadata=None,  # Explicitly None
        )

        result = provider.send(payload)

        # Should still return True (fail safely)
        assert result is True
