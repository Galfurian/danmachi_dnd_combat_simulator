from typing import Any

from rich.console import Console
from rich.rule import Rule

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


class Singleton(type):
    """Metaclass that returns the same instance every time."""

    _inst: "Singleton | None" = None

    def __call__(cls: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Creates or returns the singleton instance.

        Args:
            *args: Positional arguments for instance creation.
            **kwargs: Keyword arguments for instance creation.

        Returns:
            Any: The singleton instance.

        """
        if cls._inst is None:
            cls._inst = super().__call__(*args, **kwargs)
        return cls._inst


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
