"""Tests for report.logging_config module."""

from __future__ import annotations

import structlog

from netbox_vsphere_sync.report.logging_config import (
    SENSITIVE_KEYS,
    _mask_sensitive_keys,
    configure_logging,
)


class TestMaskSensitiveKeys:
    """Tests for the _mask_sensitive_keys processor."""

    def test_masks_password(self) -> None:
        event_dict: dict[str, str] = {"password": "s3cret!", "user": "admin"}
        result = _mask_sensitive_keys(None, "", event_dict)  # type: ignore[arg-type]
        assert result["password"] == "****"
        assert result["user"] == "admin"

    def test_masks_token(self) -> None:
        event_dict: dict[str, str] = {"token": "abc-123"}
        result = _mask_sensitive_keys(None, "", event_dict)  # type: ignore[arg-type]
        assert result["token"] == "****"

    def test_masks_secret(self) -> None:
        event_dict: dict[str, str] = {"secret": "vault-key"}
        result = _mask_sensitive_keys(None, "", event_dict)  # type: ignore[arg-type]
        assert result["secret"] == "****"

    def test_masks_secret_id(self) -> None:
        event_dict: dict[str, str] = {"secret_id": "sid-456"}
        result = _mask_sensitive_keys(None, "", event_dict)  # type: ignore[arg-type]
        assert result["secret_id"] == "****"

    def test_case_insensitive_matching(self) -> None:
        event_dict: dict[str, str] = {"Password": "p1", "TOKEN": "t1", "Secret": "s1"}
        result = _mask_sensitive_keys(None, "", event_dict)  # type: ignore[arg-type]
        assert result["Password"] == "****"
        assert result["TOKEN"] == "****"
        assert result["Secret"] == "****"

    def test_non_sensitive_keys_unchanged(self) -> None:
        event_dict: dict[str, str] = {"entity": "site", "name": "dc-west"}
        result = _mask_sensitive_keys(None, "", event_dict)  # type: ignore[arg-type]
        assert result["entity"] == "site"
        assert result["name"] == "dc-west"

    def test_sensitive_keys_constant_is_complete(self) -> None:
        expected = {"password", "token", "secret", "secret_id", "api_token"}
        assert SENSITIVE_KEYS == expected


class TestConfigureLogging:
    """Tests for the configure_logging function."""

    def test_default_console_format(self) -> None:
        configure_logging()
        log = structlog.get_logger("test")
        log.info("test.event", value=42)

    def test_json_format(self) -> None:
        configure_logging(log_format="json")
        log = structlog.get_logger("test")
        log.info("test.event", value=42)

    def test_debug_level(self) -> None:
        configure_logging(log_level="DEBUG")
        log = structlog.get_logger("test")
        log.debug("debug.event")

    def test_custom_log_level(self) -> None:
        configure_logging(log_level="WARNING")
        log = structlog.get_logger("test")
        log.warning("warning.event")
