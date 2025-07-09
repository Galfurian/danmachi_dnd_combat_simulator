import re
import random
import math
from logging import debug, warning
from typing import Any, Optional, Callable


dice_pattern = re.compile(r"^(\d*)[dD](\d+)$")


# ---- Singleton Metaclass ----


class Singleton(type):
    """Metaclass that returns the same instance every time."""

    _inst = None

    def __call__(cls, *a, **kw):
        if cls._inst is None:
            cls._inst = super().__call__(*a, **kw)
        return cls._inst


# ---- Stat Modifier ----
def get_stat_modifier(score: int) -> int:
    return (score - 10) // 2


# ---- Variable Substitution ----
def substitute_variables(expr: str, resources: Optional[dict[str, int]] = None) -> str:
    """Substitutes variables in the expression with their corresponding values.

    Args:
        expr (str): The expression to substitute variables in.
        entity (Optional[Any], optional): The entity to get variable values from. Defaults to None.
        resources (Optional[dict], optional): The resources values to use for substitution. Defaults to None.

    Returns:
        str: The expression with variables substituted.
    """
    if not expr:
        return ""
    expr = expr.upper().strip()
    if expr == "":
        return ""
    if expr.isdigit():
        return str(expr)
    # Replace [MIND] with the mind value.
    for key, value in resources.items() if resources else {}:
        if key.upper() in expr:
            expr = expr.replace(f"[{key.upper()}]", str(value))
    return expr


# ---- Dice Parsing ----
def extract_dice_terms(expr: str) -> list[str]:
    """
    Extracsts all dice terms like '1d8', '2D6', or 'd4' from an expression.
    """
    if not expr:
        return []
    expr = expr.upper().strip()
    if expr == "":
        return []
    if expr.isdigit():
        return []
    return re.findall(r"\b\d*D\d+\b", expr)


def _parse_term_and_process_dice(
    term: str, dice_action: Callable[[int, int], list[int]]
) -> tuple[int, list[int]]:
    """Parses a dice term and processes the dice based on the provided action.

    Args:
        term (str): The dice term to process (e.g., '2d6').
        dice_action (Callable[[int, int], list[int]]): A function that takes
            (num_dice, sides) and returns a list of individual dice results.

    Returns:
        tuple[int, list[int]]: The total and individual processed rolls.
    """
    if not term:
        return 0, []
    term = term.upper().strip()
    if term == "":
        return 0, []
    if term.isdigit():
        return int(term), [int(term)]
    match = dice_pattern.match(term)
    if not match:
        warning(f"Invalid dice string: '{term}'")
        return 0, []

    num_str, sides_str = match.groups()
    num = int(num_str) if num_str else 1
    sides = int(sides_str)

    rolls = dice_action(num, sides)
    return sum(rolls), rolls


def _roll_individual_dice(num: int, sides: int) -> list[int]:
    """Helper function to roll individual dice."""
    return [random.randint(1, sides) for _ in range(num)]


def _assume_min_individual_dice(num: int, sides: int) -> list[int]:
    """Helper function to assume min for individual dice."""
    return [1] * num  # The minimum roll for any die is always 1


def _assume_max_individual_dice(num: int, sides: int) -> list[int]:
    """Helper function to assume max for individual dice."""
    return [sides] * num


def parse_term_and_roll_dice(term: str) -> tuple[int, list[int]]:
    """Parses a dice term and rolls the dice."""
    return _parse_term_and_process_dice(term, _roll_individual_dice)


def parse_term_and_assume_min_dice(term: str) -> tuple[int, list[int]]:
    """Parses a dice term and assumes the minimum roll (1) for each die."""
    return _parse_term_and_process_dice(term, _assume_min_individual_dice)


def parse_term_and_assume_max_dice(term: str) -> tuple[int, list[int]]:
    """Parses a dice term and assumes the maximum roll for each die."""
    return _parse_term_and_process_dice(term, _assume_max_individual_dice)


def roll_dice(term: str) -> int:
    """Rolls a dice term and returns the total."""
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
    expr: str, term_processor: Callable[[str], tuple[int, list[int]]]
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

    try:
        return int(eval(processed_expr, {"__builtins__": None}, math.__dict__))
    except Exception as e:
        warning(f"Failed to evaluate '{processed_expr}': {e}")
        return 0


def roll_dice_expression(expr: str) -> int:
    """Rolls a dice expression and returns the total."""
    return _process_dice_expression(expr, parse_term_and_roll_dice)


def parse_expr_and_assume_min_roll(expr: str) -> int:
    """Assumes the minimum roll (1) for all dice terms in the expression."""
    return _process_dice_expression(expr, parse_term_and_assume_min_dice)


def parse_expr_and_assume_max_roll(expr: str) -> int:
    """Assumes the maximum roll for all dice terms in the expression."""
    return _process_dice_expression(expr, parse_term_and_assume_max_dice)


# ---- Public API ----
def roll_expression(expr: str, resources: Optional[dict[str, int]] = None) -> int:
    if not expr:
        return 0
    expr = expr.upper().strip()
    if expr == "":
        return 0
    if expr.isdigit():
        return int(expr)
    substituted = substitute_variables(expr, resources)
    debug(f"Substituted expression: {substituted}")
    return roll_dice_expression(substituted)


def get_max_roll(expr: str, resources: Optional[dict[str, int]] = None) -> int:
    if not expr:
        return 0
    expr = expr.upper().strip()
    if expr == "":
        return 0
    if expr.isdigit():
        return int(expr)
    substituted = substitute_variables(expr, resources)
    debug(f"Substituted expression for max roll: {substituted}")
    return parse_expr_and_assume_max_roll(substituted)


def roll_and_describe(
    expr: str, resources: Optional[dict[str, int]] = None
) -> tuple[int, str, list[int]]:
    """Rolls a dice expression and returns the total, a description, and the individual rolls.

    Args:
        expr (str): The dice expression to roll.
        entity (Optional[Any], optional): The entity rolling the dice. Defaults to None.
        mind (Optional[int], optional): The mind level to use for the roll. Defaults to 1.

    Returns:
        tuple[int, str, list[int]]: The total roll, a description of the roll, and the individual rolls.
    """
    if not expr:
        return 0, "", []
    expr = expr.upper().strip()
    if expr == "":
        return 0, "", []
    if expr.isdigit():
        return int(expr), f"{expr} = {expr}", []
    original_expr = expr
    substituted = substitute_variables(expr, resources)
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
        return result, comment, dice_rolls
    except Exception as e:
        warning(f"Failed to evaluate '{breakdown}': {e}")
        return 0, f"{original_expr} = ERROR", []


def evaluate_expression(expr: str, resources: Optional[dict[str, int]] = None) -> int:
    if not expr:
        return 0
    expr = expr.upper().strip()
    if expr == "":
        return 0
    if expr.isdigit():
        return int(expr)
    substituted = substitute_variables(expr, resources)
    try:
        return int(eval(substituted, {"__builtins__": None}, math.__dict__))
    except Exception as e:
        warning(f"Failed to evaluate '{substituted}': {e}")
        return 0


def make_bar(current: int, maximum: int, length: int = 10, color: str = "white") -> str:
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
