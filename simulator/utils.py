import re
import random
import math
from logging import debug, warning
from typing import Any, Optional, Callable


dice_pattern = re.compile(r"^(\d*)[dD](\d+)$")


# ---- Stat Modifier ----
def get_stat_modifier(score: int) -> int:
    return (score - 10) // 2


# ---- Variable Substitution ----
def substitute_variables(
    expr: str, entity: Optional[Any] = None, mind: Optional[int] = 1
) -> str:
    """Substitutes variables in the expression with their corresponding values.

    Args:
        expr (str): The expression to substitute variables in.
        entity (Optional[Any], optional): The entity to get variable values from. Defaults to None.
        mind (Optional[int], optional): The mind value to use for substitution. Defaults to 1.

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
    expr = expr.replace("[MIND]", str(mind))
    # Replace [SPELLCASTING] with the spellcasting value.
    spellcasting = getattr(entity, "SPELLCASTING", 0) if entity else 0
    expr = expr.replace("[SPELLCASTING]", str(spellcasting))
    # Replace the entity's stats with their values using square brackets only.
    for key in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
        value = getattr(entity, key, 0) if entity else 0
        expr = expr.replace(f"[{key}]", str(value))
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
def roll_expression(
    expr: str, entity: Optional[Any] = None, mind: Optional[int] = 1
) -> int:
    if not expr:
        return 0
    expr = expr.upper().strip()
    if expr == "":
        return 0
    if expr.isdigit():
        return int(expr)
    substituted = substitute_variables(expr, entity, mind)
    debug(f"Substituted expression: {substituted}")
    return roll_dice_expression(substituted)


def get_max_roll(
    expr: str, entity: Optional[Any] = None, mind: Optional[int] = 1
) -> int:
    if not expr:
        return 0
    expr = expr.upper().strip()
    if expr == "":
        return 0
    if expr.isdigit():
        return int(expr)
    substituted = substitute_variables(expr, entity, mind)
    debug(f"Substituted expression for max roll: {substituted}")
    return parse_expr_and_assume_max_roll(substituted)


def roll_and_describe(
    expr: str, entity: Optional[Any] = None, mind: Optional[int] = 1
) -> tuple[int, str]:
    if not expr:
        return 0, ""
    expr = expr.upper().strip()
    if expr == "":
        return 0, ""
    if expr.isdigit():
        return int(expr), f"{expr} = {expr}"
    original_expr = expr
    substituted = substitute_variables(expr, entity, mind)
    dice_terms = extract_dice_terms(substituted)
    breakdown = substituted
    for term in dice_terms:
        total, _ = parse_term_and_roll_dice(term)
        breakdown = breakdown.replace(term, str(total), 1)
    try:
        result = int(eval(breakdown, {"__builtins__": None}, math.__dict__))
        comment = f"{substituted} → {breakdown}"
        return result, comment
    except Exception as e:
        warning(f"Failed to evaluate '{breakdown}': {e}")
        return 0, f"{original_expr} = ERROR"


def evaluate_expression(
    expr: str, entity: Optional[Any] = None, mind: Optional[int] = 1
) -> int:
    if not expr:
        return 0
    expr = expr.upper().strip()
    if expr == "":
        return 0
    if expr.isdigit():
        return int(expr)
    substituted = substitute_variables(expr, entity, mind)
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
