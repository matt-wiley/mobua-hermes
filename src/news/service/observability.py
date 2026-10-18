"""Logging setup: structlog, as JSON lines on stdout or a given stream."""

import logging
from typing import TextIO

import structlog


def configure_logging(level: int = logging.INFO, stream: TextIO | None = None) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(stream),
    )
