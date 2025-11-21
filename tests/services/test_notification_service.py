"""
Tests for NotificationService

Tests cover:
- Service initialization with different configurations
- Fallback logic (enabled/disabled)
- Multiple providers (success/failure scenarios)
- Environment variable parsing
- Custom provider injection
"""
from unittest.mock import patch

from app.services.notifications import NotificationPayload
from app.services.notifications import NotificationService
from app.services.notifications.base import NotificationProvider


class MockProvider(NotificationProvider):
    """Mock provider for testing."""

    def __init__(self, name="Mock", configured=True, should_succeed=True):
        # Don't call super().__init__() - it tries to set name property which we override
        # Manually initialize what we need
        self.config = {}  # Required by base class
        self._name = name
        self._configured = configured
        self._should_succeed = should_succeed
        self.send_called = False
        self.last_payload = None

    @property
    def name(self):
        return self._name

    def is_configured(self) -> bool:
        return self._configured

    def send(self, payload: NotificationPayload) -> bool:
        self.send_called = True
        self.last_payload = payload
        return self._should_succeed


class TestNotificationServiceInitialization:
    """Test service initialization and provider loading."""

    def test_init_with_custom_providers(self):
        """Service should accept custom providers."""
        mock1 = MockProvider(name="Custom1")
        mock2 = MockProvider(name="Custom2")

        service = NotificationService(custom_providers={"mock1": mock1, "mock2": mock2})

        assert len(service.providers) == 2
        assert "Custom1" in service.get_active_providers()
        assert "Custom2" in service.get_active_providers()

    def test_init_with_env_var(self):
        """Service should load providers from NOTIFICATION_PROVIDERS env var."""
        with patch.dict("os.environ", {"NOTIFICATION_PROVIDERS": "console"}):
            service = NotificationService()

            assert len(service.providers) >= 1
            assert "Console" in service.get_active_providers()

    def test_init_defaults_to_console_when_empty(self):
        """Service should fallback to console if no providers configured."""
        service = NotificationService(providers=[])

        assert len(service.providers) == 1
        assert "Console" in service.get_active_providers()

    def test_init_skips_unconfigured_providers(self):
        """Service should skip providers from registry that are not configured."""
        # Test with registry providers (not custom providers)
        # Patch the AVAILABLE_PROVIDERS to use a mock that returns unconfigured
        with patch.dict(
            "app.services.notifications.service.NotificationService.AVAILABLE_PROVIDERS",
            {"test_unconfigured": MockProvider},
            clear=False,  # Keep existing providers
        ):
            # Create unconfigured mock provider class
            class UnconfiguredMockProvider(NotificationProvider):
                def __init__(self, config=None):
                    self.config = config or {}
                    self._name = "Unconfigured"

                @property
                def name(self):
                    return self._name

                def is_configured(self) -> bool:
                    return False  # Always unconfigured

                def send(self, payload):
                    return False

            # Patch registry with unconfigured provider
            with patch.dict(
                "app.services.notifications.service.NotificationService.AVAILABLE_PROVIDERS",
                {"unconfigured_test": UnconfiguredMockProvider},
            ):
                # Try to initialize with only unconfigured provider
                service = NotificationService(providers=["unconfigured_test"])

                # Should fallback to console since provider is not configured
                assert len(service.providers) == 1
                assert "Console" in service.get_active_providers()

    @patch.dict("os.environ", {"NOTIFICATION_FALLBACK": "false"})
    def test_init_respects_fallback_env_var(self):
        """Service should respect NOTIFICATION_FALLBACK env var."""
        service = NotificationService()

        assert service.enable_fallback is False

    def test_init_with_unknown_provider_name(self):
        """Service should skip unknown provider names gracefully."""
        with patch.dict(
            "os.environ", {"NOTIFICATION_PROVIDERS": "slack,unknown_provider,console"}
        ):
            service = NotificationService()

            # Should have slack and console (unknown_provider skipped)
            provider_names = service.get_active_providers()
            assert "unknown_provider" not in [p.lower() for p in provider_names]


class TestNotificationServiceNotify:
    """Test notification sending logic."""

    def test_notify_success_single_provider(self):
        """Notification should succeed with single working provider."""
        mock = MockProvider(should_succeed=True)
        service = NotificationService(custom_providers={"mock": mock})

        success = service.notify(
            conversation_id="test_123", title="Test", message="Test message"
        )

        assert success is True
        assert mock.send_called is True
        assert mock.last_payload.conversation_id == "test_123"
        assert mock.last_payload.title == "Test"
        assert mock.last_payload.message == "Test message"

    def test_notify_failure_single_provider(self):
        """Notification should fail if single provider fails."""
        mock = MockProvider(should_succeed=False)
        service = NotificationService(custom_providers={"mock": mock})

        success = service.notify(
            conversation_id="test_123", title="Test", message="Test message"
        )

        assert success is False
        assert mock.send_called is True

    def test_notify_fallback_enabled_tries_all(self):
        """With fallback enabled, should try all providers."""
        mock1 = MockProvider(name="Mock1", should_succeed=False)
        mock2 = MockProvider(name="Mock2", should_succeed=True)
        mock3 = MockProvider(name="Mock3", should_succeed=True)

        service = NotificationService(
            custom_providers={"mock1": mock1, "mock2": mock2, "mock3": mock3},
            enable_fallback=True,
        )

        success = service.notify(
            conversation_id="test_123", title="Test", message="Test message"
        )

        assert success is True
        assert mock1.send_called is True  # Tried first (failed)
        assert mock2.send_called is True  # Tried second (succeeded)
        assert mock3.send_called is True  # Still tried third (fallback enabled)

    def test_notify_fallback_disabled_stops_on_first_success(self):
        """With fallback disabled, should stop after first success."""
        mock1 = MockProvider(name="Mock1", should_succeed=True)
        mock2 = MockProvider(name="Mock2", should_succeed=True)

        service = NotificationService(
            custom_providers={"mock1": mock1, "mock2": mock2}, enable_fallback=False
        )

        success = service.notify(
            conversation_id="test_123", title="Test", message="Test message"
        )

        assert success is True
        assert mock1.send_called is True  # Tried first (succeeded)
        assert mock2.send_called is False  # Should NOT try second

    def test_notify_fallback_disabled_stops_on_first_failure(self):
        """With fallback disabled, should stop after first failure."""
        mock1 = MockProvider(name="Mock1", should_succeed=False)
        mock2 = MockProvider(name="Mock2", should_succeed=True)

        service = NotificationService(
            custom_providers={"mock1": mock1, "mock2": mock2}, enable_fallback=False
        )

        success = service.notify(
            conversation_id="test_123", title="Test", message="Test message"
        )

        assert success is False
        assert mock1.send_called is True  # Tried first (failed)
        assert mock2.send_called is False  # Should NOT try second

    def test_notify_all_providers_fail(self):
        """Notification should fail if all providers fail."""
        mock1 = MockProvider(name="Mock1", should_succeed=False)
        mock2 = MockProvider(name="Mock2", should_succeed=False)

        service = NotificationService(
            custom_providers={"mock1": mock1, "mock2": mock2}, enable_fallback=True
        )

        success = service.notify(
            conversation_id="test_123", title="Test", message="Test message"
        )

        assert success is False
        assert mock1.send_called is True
        assert mock2.send_called is True

    def test_notify_with_metadata(self):
        """Notification should pass metadata correctly."""
        mock = MockProvider()
        service = NotificationService(custom_providers={"mock": mock})

        metadata = {"user_id": "user_123", "retry_count": 3}

        service.notify(
            conversation_id="test_123",
            title="Test",
            message="Test message",
            metadata=metadata,
        )

        assert mock.last_payload.metadata == metadata

    def test_notify_with_priority(self):
        """Notification should pass priority correctly."""
        mock = MockProvider()
        service = NotificationService(custom_providers={"mock": mock})

        service.notify(
            conversation_id="test_123",
            title="Test",
            message="Test message",
            priority="high",
        )

        assert mock.last_payload.priority == "high"


class TestNotificationServiceHelpers:
    """Test helper methods."""

    def test_parse_bool_env_true_variations(self):
        """Should parse various true values correctly."""
        service = NotificationService(providers=["console"])

        with patch.dict("os.environ", {"TEST_VAR": "true"}):
            assert service._parse_bool_env("TEST_VAR", False) is True

        with patch.dict("os.environ", {"TEST_VAR": "True"}):
            assert service._parse_bool_env("TEST_VAR", False) is True

        with patch.dict("os.environ", {"TEST_VAR": "1"}):
            assert service._parse_bool_env("TEST_VAR", False) is True

        with patch.dict("os.environ", {"TEST_VAR": "yes"}):
            assert service._parse_bool_env("TEST_VAR", False) is True

        with patch.dict("os.environ", {"TEST_VAR": "on"}):
            assert service._parse_bool_env("TEST_VAR", False) is True

    def test_parse_bool_env_false_variations(self):
        """Should parse false values correctly."""
        service = NotificationService(providers=["console"])

        with patch.dict("os.environ", {"TEST_VAR": "false"}):
            assert service._parse_bool_env("TEST_VAR", True) is False

        with patch.dict("os.environ", {"TEST_VAR": "0"}):
            assert service._parse_bool_env("TEST_VAR", True) is False

        with patch.dict("os.environ", {"TEST_VAR": "no"}):
            assert service._parse_bool_env("TEST_VAR", True) is False

    def test_parse_bool_env_uses_default_when_not_set(self):
        """Should use default value when env var not set."""
        service = NotificationService(providers=["console"])

        with patch.dict("os.environ", {}, clear=True):
            assert service._parse_bool_env("NONEXISTENT_VAR", True) is True
            assert service._parse_bool_env("NONEXISTENT_VAR", False) is False

    def test_get_active_providers(self):
        """Should return list of active provider names."""
        mock1 = MockProvider(name="Provider1")
        mock2 = MockProvider(name="Provider2")

        service = NotificationService(custom_providers={"p1": mock1, "p2": mock2})

        active = service.get_active_providers()

        assert len(active) == 2
        assert "Provider1" in active
        assert "Provider2" in active


class TestNotificationServiceIntegration:
    """Integration tests with real console provider."""

    def test_console_provider_always_works(self):
        """Console provider should always succeed."""
        service = NotificationService(providers=["console"])

        success = service.notify(
            conversation_id="test_123",
            title="Integration Test",
            message="This should always work",
            priority="normal",
        )

        assert success is True

    def test_mixed_providers_with_fallback(self):
        """Should succeed with mixed success/failure and fallback enabled."""
        failing_mock = MockProvider(name="FailingProvider", should_succeed=False)

        # Mixed: failing mock + console (always works)
        service = NotificationService(
            providers=["console"],
            custom_providers={"failing": failing_mock},
            enable_fallback=True,
        )

        success = service.notify(
            conversation_id="test_123",
            title="Mixed Test",
            message="Should succeed via console",
        )

        assert success is True
        assert failing_mock.send_called is True  # Tried and failed
        # Console should have succeeded (but we can't easily verify without inspecting logs)
