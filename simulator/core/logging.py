"""
Logging configuration module for the simulator.

Provides centralized logging setup with colored output using rich.
"""

import logging
from typing import Any

from rich.console import Console
from rich.logging import RichHandler


def setup_logging(level: int = logging.INFO) -> None:
    """
    Sets up logging configuration with rich colored output.

    Args:
        level (int): The logging level to set. Defaults to logging.INFO.

    """
    # Create a rich console for logging
    console = Console(width=120, force_terminal=True, force_jupyter=False)

    # Configure the rich handler
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_level=True,
        show_path=False,  # Don't show file path to keep output clean
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
    )

    # Set up the formatter
    rich_handler.setFormatter(
        logging.Formatter(
            "%(name)s - %(levelname)s - %(message)s",
            datefmt="[%X]"
        )
    )

    # Configure the root logger
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[rich_handler]
    )

    # Set specific levels for noisy libraries if needed
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Gets a logger instance with the specified name.

    Args:
        name (str): The name of the logger.

    Returns:
        logging.Logger: The configured logger instance.

    """
    return logging.getLogger(name)


# Create a default logger for the simulator
logger = get_logger("simulator")


def log_error(message: str, context: dict[str, Any] | None = None) -> None:
    """
    Logs an error message with optional context.

    Args:
        message (str): The error message.
        context (Dict[str, Any] | None): Optional context dictionary.

    """
    if context:
        # Format context as key=value pairs
        context_str = " ".join(f"{k}={v}" for k, v in context.items())
        message = f"{message} [{context_str}]"

    logger.error(message)


def log_warning(message: str, context: dict[str, Any] | None = None) -> None:
    """
    Logs a warning message with optional context.

    Args:
        message (str): The warning message.
        context (Dict[str, Any] | None): Optional context dictionary.

    """
    if context:
        # Format context as key=value pairs
        context_str = " ".join(f"{k}={v}" for k, v in context.items())
        message = f"{message} [{context_str}]"

    logger.warning(message)


def log_info(message: str, context: dict[str, Any] | None = None) -> None:
    """
    Logs an info message with optional context.

    Args:
        message (str): The info message.
        context (Dict[str, Any] | None): Optional context dictionary.

    """
    if context:
        # Format context as key=value pairs
        context_str = " ".join(f"{k}={v}" for k, v in context.items())
        message = f"{message} [{context_str}]"

    logger.info(message)


def log_debug(message: str, context: dict[str, Any] | None = None) -> None:
    """
    Logs a debug message with optional context.

    Args:
        message (str): The debug message.
        context (Dict[str, Any] | None): Optional context dictionary.

    """
    if context:
        # Format context as key=value pairs
        context_str = " ".join(f"{k}={v}" for k, v in context.items())
        message = f"{message} [{context_str}]"

    logger.debug(message)
