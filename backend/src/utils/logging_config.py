"""
Logging configuration with structlog for structured logging.
"""

import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO", json_format: bool = False):
    """Configure structured logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_format: Whether to output JSON format
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Configure structlog
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
    ]

    if json_format:
        # JSON format for production
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Pretty format for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    """Get a structured logger.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        BoundLogger: Structured logger instance
    """
    return structlog.get_logger(name)
