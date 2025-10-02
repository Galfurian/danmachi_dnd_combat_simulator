"""
Utilities module for the simulator.

Provides common utility functions and helpers, including console printing
with rich formatting, singleton pattern, and other shared functionality.
"""

from __future__ import annotations

from typing import Any, Generic

from rich.console import Console
from rich.rule import Rule
from typing_extensions import TypeVar

# Initialize the rich console.
_console = Console(markup=True, width=120, force_terminal=True, force_jupyter=False)


def cprint(*args: Any, **kwargs: Any) -> None:
    """
    Custom print function to handle colored output.

    Args:
        *args: Arguments to pass to the console print function.
        **kwargs: Keyword arguments to pass to the console print function.

    """
    _console.print(*args, **kwargs)


def crule(*args: Any, **kwargs: Any) -> None:
    """
    Custom print function to handle colored output with a rule.

    Args:
        *args: Arguments to pass to the Rule constructor.
        **kwargs: Keyword arguments to pass to the Rule constructor.

    """
    _console.print(Rule(*args, **kwargs))


def ccapture(content: Any) -> str:
    """
    Captures console output as a string.

    Args:
        content (Any): The content to capture.

    Returns:
        str: The captured output as a string.

    """
    with _console.capture() as capture:
        _console.print(content, markup=True, end="")
    return capture.get()


# ---- Singleton Metaclass ----


_T = TypeVar("_T")


class Singleton(type, Generic[_T]):
    """Metaclass that returns the same instance every time."""

    _instances: dict[Singleton[_T], _T] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> _T:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


# ---- Stat Modifier ----
def get_stat_modifier(score: int) -> int:
    """
    Calculates the D&D ability score modifier.

    Args:
        score (int): The ability score.

    Returns:
        int: The modifier for the given ability score.

    """
    return (score - 10) // 2


def make_bar(current: int, maximum: int, length: int = 10, color: str = "white") -> str:
    """
    Creates a visual progress bar representation.

    Args:
        current (int): The current value.
        maximum (int): The maximum value.
        length (int): The length of the bar in characters. Defaults to 10.
        color (str): The color for the filled portion. Defaults to "white".

    Returns:
        str: A formatted progress bar string.

    """
    # Compute the filled part of the bar.
    filled = int((current / maximum) * length)
    # Compute the empty part of the bar.
    empty = length - filled
    # Start by creating the bar with the filled part.
    bar = f"[{color}]" + "▮" * filled
    # If there is an empty part, add it to the bar.
    if empty > 0:
        bar += "[dim white]" + "▯" * empty + "[/]"
    bar += "[/]"
    return bar
