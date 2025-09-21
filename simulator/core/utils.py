import math
import random
import re
from collections.abc import Callable
from logging import debug
from typing import Any

from pydantic import BaseModel, Field, model_validator
from rich.console import Console
from rich.rule import Rule
from catchery import log_warning

DICE_PATTERN = re.compile(r"^(\d*)[dD](\d+)$")

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


class GameException(Exception):
    """Custom exception for game errors."""

    pass


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


class VarInfo(BaseModel):
    """Class to hold variable information."""

    name: str = Field(description="Variable name")
    value: int = Field(description="Variable value")

    @model_validator(mode="after")
    def validate_fields(self) -> "VarInfo":
        """Validates fields after model initialization."""
        if not self.name or not isinstance(self.name, str):
            raise ValueError("name must be a non-empty string")
        if not isinstance(self.value, int):
            raise ValueError("value must be an integer")
        # Normalize name to uppercase.
        self.name = self.name.upper().strip()
        return self

    def replace_in_expr(self, expr: str) -> str:
        """
        Replaces occurrences of the variable in the expression with its value.

        Args:
            expr (str): The expression to perform replacements in.

        Returns:
            str: The expression with variable replaced by its value.

        """
        if not expr or not self.name:
            return expr
        return expr.replace(f"[{self.name}]", str(self.value))


class RollBreakdown(BaseModel):
    """Class to hold roll breakdown information."""

    value: int = Field(
        description="Total roll result",
    )
    description: str = Field(
        description="Description of the roll",
    )
    rolls: list[int] = Field(
        description="List of individual dice rolls",
        default_factory=list,
    )

    def get_roll(self) -> int:
        """
        Returns the total roll value.

        Returns:
            int: The total roll value.
        """
        return self.value

    def is_critical(self) -> bool:
        """
        Determines if the roll is a critical hit (natural 20).
        """
        return self.rolls[0] == 20 if self.rolls else False

    def is_fumble(self) -> bool:
        """
        Determines if the roll is a fumble (natural 1).
        """
        return self.rolls[0] == 1 if self.rolls else False


def _safe_eval(arith_expr: str) -> str:
    """Safely evaluates a simple arithmetic expression.

    DEPRECATED: This function uses eval() which is unsafe.
    Use DiceParser from core.dice_parser instead.

    Args:
        arith_expr (str): The arithmetic expression to evaluate.

    Returns:
        str: The result of the evaluation or the original expression if an error occurs.

    """

    # TODO: Replace with DiceParser.parse_dice()
    def _unsafe_eval() -> str:
        """
        Nested function to evaluate arithmetic expression.

        Returns:
            str: The string result of the evaluation.

        """
        # Only allow safe arithmetic evaluation
        return str(eval(arith_expr, {"__builtins__": None}, {}))

    try:
        return _unsafe_eval()
    except Exception as e:
        log_warning(
            f"Failed to evaluate expression: {arith_expr}",
            {"expression": arith_expr},
            e,
        )
        return arith_expr  # Return original on error


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


# ---- Variable Substitution ----
def substitute_variables(
    expr: str,
    variables: list[VarInfo] = [],
) -> str:
    """
    Substitutes variables in the expression with their corresponding values.

    Args:
        expr (str):
            The expression to substitute variables in.
        variables (Optional[dict], optional):
            The variables values to use for substitution. Defaults to None.

    Returns:
        str: The expression with variables substituted.

    """
    expr = expr.upper().strip()
    if expr == "":
        return ""
    if expr.isdigit():
        return str(expr)
    # Replace the variables with their actual values.
    for variable in variables or []:
        expr = variable.replace_in_expr(expr)
    return expr


# ---- Dice Parsing ----
def extract_dice_terms(expr: str) -> list[str]:
    """
    Extracts all dice terms like '1d8', '2D6', or 'd4' from an expression.

    Args:
        expr (str): The expression to extract dice terms from.

    Returns:
        list[str]: List of dice terms found in the expression.

    """
    expr = expr.upper().strip()
    if not expr:
        return []
    if expr.isdigit():
        return []
    return re.findall(r"\b\d*D\d+\b", expr)


def _parse_term_and_process_dice(
    term: str,
    dice_action: Callable[[int, int], list[int]],
) -> tuple[int, list[int]]:
    """Parses a dice term and processes the dice based on the provided action.

    Args:
        term (str): The dice term to process (e.g., '2d6').
        dice_action (Callable[[int, int], list[int]]): A function that takes
            (num_dice, sides) and returns a list of individual dice results.

    Returns:
        tuple[int, list[int]]: The total and individual processed rolls.

    """
    term = term.upper().strip()
    if not term:
        return 0, []
    if term.isdigit():
        value = int(term)
        if value < 0:
            log_warning(
                f"Negative dice value not allowed: {value}",
                {"term": term, "value": value},
            )
            return 0, []
        return value, [value]

    match = DICE_PATTERN.match(term)
    if not match:
        log_warning(
            f"Invalid dice string format: '{term}'",
            {"term": term},
        )
        return 0, []

    num_str, sides_str = match.groups()
    num = int(num_str) if num_str else 1
    sides = int(sides_str)

    # Validate dice parameters
    if num <= 0:
        log_warning(
            f"Number of dice must be positive, got {num}",
            {"term": term, "num": num, "sides": sides},
        )
        return 0, []

    if sides <= 0:
        log_warning(
            f"Number of sides must be positive, got {sides}",
            {"term": term, "num": num, "sides": sides},
        )
        return 0, []

    if num > 100:  # Reasonable limit
        log_warning(
            f"Too many dice requested: {num} (limit: 100)",
            {"term": term, "num": num, "sides": sides},
        )
        return 0, []

    if sides > 1000:  # Reasonable limit
        log_warning(
            f"Too many sides on dice: {sides} (limit: 1000)",
            {"term": term, "num": num, "sides": sides},
        )
        return 0, []

    rolls = dice_action(num, sides)
    return sum(rolls), rolls


def _roll_individual_dice(num: int, sides: int) -> list[int]:
    """
    Helper function to roll individual dice.

    Args:
        num (int): Number of dice to roll.
        sides (int): Number of sides on each die.

    Returns:
        list[int]: List of individual dice roll results.

    """
    return [random.randint(1, sides) for _ in range(num)]


def _assume_min_individual_dice(num: int, sides: int) -> list[int]:
    """
    Helper function to assume min for individual dice.

    Args:
        num (int): Number of dice.
        sides (int): Number of sides on each die.

    Returns:
        list[int]: List with minimum roll (1) for each die.

    """
    return [1] * num  # The minimum roll for any die is always 1


def _assume_max_individual_dice(num: int, sides: int) -> list[int]:
    """
    Helper function to assume max for individual dice.

    Args:
        num (int): Number of dice.
        sides (int): Number of sides on each die.

    Returns:
        list[int]: List with maximum roll for each die.

    """
    return [sides] * num


def parse_term_and_roll_dice(term: str) -> tuple[int, list[int]]:
    """
    Parses a dice term and rolls the dice.

    Args:
        term (str): The dice term to parse and roll.

    Returns:
        tuple[int, list[int]]: Total roll result and list of individual rolls.

    """
    return _parse_term_and_process_dice(term, _roll_individual_dice)


def parse_term_and_assume_min_dice(term: str) -> tuple[int, list[int]]:
    """
    Parses a dice term and assumes the minimum roll (1) for each die.

    Args:
        term (str): The dice term to parse.

    Returns:
        tuple[int, list[int]]: Total minimum result and list of minimum rolls.

    """
    return _parse_term_and_process_dice(term, _assume_min_individual_dice)


def parse_term_and_assume_max_dice(term: str) -> tuple[int, list[int]]:
    """
    Parses a dice term and assumes the maximum roll for each die.

    Args:
        term (str): The dice term to parse.

    Returns:
        tuple[int, list[int]]: Total maximum result and list of maximum rolls.

    """
    return _parse_term_and_process_dice(term, _assume_max_individual_dice)


def roll_dice(term: str) -> int:
    """
    Rolls a dice term and returns the total.

    Args:
        term (str): The dice term to roll.

    Returns:
        int: The total result of the dice roll.

    """
    if not term:
        return 0
    term = term.upper().strip()
    if term == "":
        return 0
    if term.isdigit():
        return int(term)
    total, _ = parse_term_and_roll_dice(term)
    return total


def _process_dice_expression(
    expr: str,
    term_processor: Callable[[str], tuple[int, list[int]]],
) -> int:
    """Processes a dice expression by replacing dice terms with their processed values.

    Args:
        expr (str): The dice expression to process.
        term_processor (Callable[[str], tuple[int, list[int]]]): A function
            that takes a dice term and returns its total and individual rolls.

    Returns:
        int: The total result of the processed dice expression.

    """
    if not expr:
        return 0
    expr = expr.upper().strip()
    if expr == "":
        return 0
    if expr.isdigit():
        return int(expr)

    dice_terms = extract_dice_terms(expr)
    processed_expr = expr

    for term in dice_terms:
        total, _ = term_processor(term)
        # Use re.sub to replace only the first occurrence of the term to avoid issues
        # if the same term appears multiple times and is meant to represent distinct rolls.
        processed_expr = re.sub(
            r"\b" + re.escape(term) + r"\b", str(total), processed_expr, count=1
        )
        debug(f"Processed {term} → {total} ({processed_expr})")

    # Now evaluate the processed expression safely.
    try:
        return int(eval(processed_expr, {"__builtins__": None}, math.__dict__))
    except Exception as e:
        log_warning(
            f"Failed to evaluate '{processed_expr}': {e}",
            {
                "expression": processed_expr,
                "error": str(e),
                "context": "dice_expression_evaluation",
            },
            GameException("Error evaluating dice expression."),
            True,
            e,
        )
        return 0


def roll_dice_expression(expr: str) -> int:
    """
    Rolls a dice expression and returns the total.

    Args:
        expr (str): The dice expression to roll.

    Returns:
        int: The total result of the dice expression.

    """
    return _process_dice_expression(expr, parse_term_and_roll_dice)


def parse_expr_and_assume_min_roll(expr: str) -> int:
    """
    Assumes the minimum roll (1) for all dice terms in the expression.

    Args:
        expr (str): The dice expression to process.

    Returns:
        int: The minimum possible result for the expression.

    """
    return _process_dice_expression(expr, parse_term_and_assume_min_dice)


def parse_expr_and_assume_max_roll(expr: str) -> int:
    """
    Assumes the maximum roll for all dice terms in the expression.

    Args:
        expr (str): The dice expression to process.

    Returns:
        int: The maximum possible result for the expression.

    """
    return _process_dice_expression(expr, parse_term_and_assume_max_dice)


# ---- Public API ----
def roll_expression(
    expr: str,
    variables: list[VarInfo] = [],
) -> int:
    """
    Rolls a dice expression with variable substitution.

    Args:
        expr (str):
            The dice expression to roll.
        variables (list[VarInfo]):
            A list of variable information for substitution.

    Returns:
        int:
            The total result of the roll.

    """
    if not expr:
        return 0
    expr = expr.upper().strip()
    if expr == "":
        return 0
    if expr.isdigit():
        return int(expr)
    return roll_dice_expression(substitute_variables(expr, variables))


def get_max_roll(
    expr: str,
    variables: list[VarInfo] = [],
) -> int:
    """
    Gets the maximum possible roll for a dice expression.

    Args:
        expr (str):
            The dice expression to analyze.
        variables (list[VarInfo]):
            A list of variable information for substitution.

    Returns:
        int:
            The maximum possible result.

    """
    if not expr:
        return 0
    expr = expr.upper().strip()
    if expr == "":
        return 0
    if expr.isdigit():
        return int(expr)
    return parse_expr_and_assume_max_roll(substitute_variables(expr, variables))


def roll_and_describe(
    expr: str,
    variables: list[VarInfo] = [],
) -> RollBreakdown:
    """
    Rolls a dice expression with variable substitution and provides a breakdown.

    Args:
        expr (str):
            The dice expression to roll.
        variables (list[VarInfo]):
            A list of variable information for substitution.

    Returns:
        RollBreakdown:
            An object containing the total roll value, a description of the roll,
            and a list of individual dice rolls.

    """
    if not expr:
        return RollBreakdown(value=0, description="", rolls=[])
    expr = expr.upper().strip()
    if expr == "":
        return RollBreakdown(value=0, description="", rolls=[])
    if expr.isdigit():
        return RollBreakdown(
            value=int(expr),
            description=f"{expr} → {expr}",
            rolls=[],
        )
    original_expr = expr
    substituted = substitute_variables(expr, variables)
    dice_terms = extract_dice_terms(substituted)
    dice_rolls: list[int] = []
    breakdown = substituted
    for term in dice_terms:
        total, _ = parse_term_and_roll_dice(term)
        breakdown = breakdown.replace(term, str(total), 1)
        dice_rolls.append(total)
    try:
        result = int(eval(breakdown, {"__builtins__": None}, math.__dict__))
        comment = f"{substituted} → {breakdown}"
        return RollBreakdown(
            value=result,
            description=comment,
            rolls=dice_rolls,
        )
    except Exception as e:
        log_warning(
            f"Failed to evaluate '{breakdown}': {e}",
            {
                "breakdown": breakdown,
                "original_expr": original_expr,
                "error": str(e),
                "context": "dice_breakdown_evaluation",
            },
            GameException("Error evaluating dice expression."),
            True,
            e,
        )
        return RollBreakdown(value=0, description="", rolls=[])


def evaluate_expression(
    expr: str,
    variables: list[VarInfo] = [],
) -> int:
    """
    Evaluates a mathematical expression with variable substitution.

    Args:
        expr (str):
            The expression to evaluate.
        variables (list[VarInfo]):
            A list of variable information for substitution.

    Returns:
        int:
            The result of the expression evaluation.

    """
    if not expr:
        return 0
    expr = expr.upper().strip()
    if expr == "":
        return 0
    if expr.isdigit():
        return int(expr)
    substituted = substitute_variables(expr, variables)
    try:
        return int(eval(substituted, {"__builtins__": None}, math.__dict__))
    except Exception as e:
        log_warning(
            f"Failed to evaluate '{substituted}': {e}",
            {
                "expression": substituted,
                "original": expr,
                "variables": variables or {},
                "error": str(e),
                "context": "variable_expression_evaluation",
            },
        )
        return 0


def simplify_expression(
    expr: str,
    variables: list[VarInfo] = [],
) -> str:
    """
    Simplifies an expression by substituting variables and evaluating arithmetic.

    Args:
        expr (str):
            The expression to simplify.
        variables (list[VarInfo]):
            A list of variable information for substitution.

    Returns:
        str:
            The simplified expression.

    """
    if not expr:
        return ""
    # Step 1: Substitute variables
    substituted = substitute_variables(expr, variables)
    # Step 2: Evaluate entire expression safely.
    substituted = re.sub(
        r"\b(\d+\s*[\+\-\*\/]\s*\d+)\b", lambda m: _safe_eval(m.group(0)), substituted
    )
    return substituted


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
