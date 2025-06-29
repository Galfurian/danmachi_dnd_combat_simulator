import re
import random
import math
from logging import debug, warning
from typing import Any, Optional


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
    Extracts all dice terms like '1d8', '2D6', or 'd4' from an expression.
    """
    if not expr:
        return []
    expr = expr.upper().strip()
    if expr == "":
        return []
    if expr.isdigit():
        return []
    return re.findall(r"\b\d*D\d+\b", expr)


def parse_and_roll_dice(term: str) -> tuple[int, list[int]]:
    """Parses a dice term and rolls the dice.

    Args:
        term (str): The dice term to roll (e.g., '2d6').

    Returns:
        tuple[int, list[int]]: The total and individual rolls.
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

    rolls = [random.randint(1, sides) for _ in range(num)]
    return sum(rolls), rolls


def roll_dice(term: str) -> int:
    """Rolls a dice term and returns the total.

    Args:
        term (str): The dice term to roll (e.g., '2d6').

    Returns:
        int: The total result of the rolled dice term.
    """
    if not term:
        return 0
    term = term.upper().strip()
    if term == "":
        return 0
    if term.isdigit():
        return int(term)
    total, _ = parse_and_roll_dice(term)
    return total


def roll_dice_expression(expr: str) -> int:
    """Rolls a dice expression and returns the total.

    Args:
        expr (str): The dice expression to roll.

    Returns:
        int: The total result of the rolled dice expression.
    """
    if not expr:
        return 0
    expr = expr.upper().strip()
    if expr == "":
        return 0
    if expr.isdigit():
        return int(expr)
    dice_terms = extract_dice_terms(expr)
    rolled_expr = expr

    for term in dice_terms:
        rolled, _ = parse_and_roll_dice(term)
        rolled_expr = re.sub(term, str(rolled), rolled_expr, count=1)
        debug(f"Rolled {term} → {rolled} ({rolled_expr})")
    try:
        return int(eval(rolled_expr, {"__builtins__": None}, math.__dict__))
    except Exception as e:
        warning(f"Failed to evaluate '{rolled_expr}': {e}")
        return 0


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

    components: list[str] = []
    for term in dice_terms:
        total, rolls = parse_and_roll_dice(term)
        components.append(f"{term} = {'+'.join(map(str, rolls))}")
        breakdown = breakdown.replace(term, str(total), 1)
    try:
        result = int(eval(breakdown, {"__builtins__": None}, math.__dict__))
        comment = f"{original_expr} = {substituted} → {', '.join(components)}"
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
