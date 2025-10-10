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
    logger_levels: Dict[str, int] = {},
) -> None:
    """
    Sets up logging configuration with rich colored output.

    Args:
        logger_levels (Dict[str, int]): Dictionary mapping logger names to their specific levels.
                                       The "simulator" logger allows propagation, others are independent.

    """
    # Create a rich console for logging
    console = Console(width=120, force_terminal=True, force_jupyter=False)

    # Set up root logger first
    logging.basicConfig(
        level=logging.WARNING,  # Root logger at WARNING to not interfere
        format="%(message)s",
        datefmt="%X",
        handlers=[]
    )

    # Configure logger levels.
    for logger_name, logger_level in logger_levels.items():
        specific_logger = logging.getLogger(logger_name)
        # Clear existing handlers to avoid duplicates
        specific_logger.handlers.clear()
        specific_logger.setLevel(logger_level)

        # Only make non-simulator loggers independent (no propagation)
        if logger_name != "simulator":
            specific_logger.propagate = False

        # Create a handler for this logger with the specific level
        specific_handler = _create_rich_handler(console, logger_level)
        specific_logger.addHandler(specific_handler)

    # Set specific levels for noisy libraries if needed
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


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
character_logger = get_logger("simulator.character")
