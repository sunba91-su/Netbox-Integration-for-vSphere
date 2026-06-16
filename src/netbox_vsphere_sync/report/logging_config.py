"""Logging configuration for netbox-vsphere-sync.

Provides structured logging via structlog with two renderers:
- Console (dev): human-readable coloured output
- JSON (prod): machine-parseable structured logs

Sensitive fields (password, token, secret) are automatically masked.
"""

from __future__ import annotations

import logging
import os
from typing import Literal

import structlog

SENSITIVE_KEYS = frozenset({"password", "token", "secret", "secret_id", "api_token"})

_LOG_FORMAT_ENV = "NVS_LOG_LEVEL"
_DEFAULT_LOG_LEVEL = "INFO"


def _mask_sensitive_keys(
    logger: logging.Logger, method_name: str, event_dict: structlog.types.EventDict
) -> structlog.types.EventDict:
    """Mask sensitive values before they reach the renderer."""
    for key in event_dict:
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = "****"
    return event_dict


def configure_logging(
    log_level: str | None = None,
    log_format: Literal["console", "json"] = "console",
) -> None:
    """Configure structlog with the chosen renderer and log level.

    Args:
        log_level: Python log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                   Falls back to NVS_LOG_LEVEL env var, then INFO.
        log_format: "console" for human-readable, "json" for structured output.
    """
    level = log_level or os.environ.get(_LOG_FORMAT_ENV, _DEFAULT_LOG_LEVEL)
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _mask_sensitive_keys,
    ]

    if log_format == "json":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
