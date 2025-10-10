"""
Logging configuration module for the simulator.

Provides centralized logging setup with colored output using rich.
Supports multiple named loggers with individual level configuration.
"""

import logging
from typing import Any, Dict

from rich.console import Console
from rich.logging import RichHandler


def _create_rich_handler(console: Console, level: int = logging.NOTSET) -> RichHandler:
    """Create a RichHandler with consistent configuration."""
    handler = RichHandler(
        console=console,
        show_time=False,
        show_level=True,
        show_path=True,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
    )
    handler.setLevel(level)
    return handler


def setup_logging(
    level: int = logging.INFO,
    logger_levels: Dict[str, int] | None = None
) -> None:
    """
    Sets up logging configuration with rich colored output.

    Args:
        level (int): The default logging level to set. Defaults to logging.INFO.
        logger_levels (Dict[str, int] | None): Dictionary mapping logger names to their specific levels.

    """
    # Create a rich console for logging
    console = Console(width=120, force_terminal=True, force_jupyter=False)

    # Configure the rich handler
    rich_handler = _create_rich_handler(console)

    # Configure the root logger
    logging.basicConfig(
        level=level, format="%(message)s", datefmt="%X", handlers=[rich_handler]
    )

    # Set specific levels for noisy libraries if needed
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Configure specific logger levels
    if logger_levels:
        for logger_name, logger_level in logger_levels.items():
            specific_logger = logging.getLogger(logger_name)
            # Clear existing handlers to avoid duplicates
            specific_logger.handlers.clear()
            specific_logger.setLevel(logger_level)
            # Prevent propagation to root logger for independently configured loggers
            specific_logger.propagate = False
            # Create a handler for this logger with the specific level
            specific_handler = _create_rich_handler(console, logger_level)
            specific_logger.addHandler(specific_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Gets a logger instance with the specified name.

    Args:
        name (str): The name of the logger.

    Returns:
        logging.Logger: The configured logger instance.

    """
    return logging.getLogger(name)


# Create default loggers for the simulator
logger = get_logger("simulator")
effects_logger = get_logger("simulator.effects")
