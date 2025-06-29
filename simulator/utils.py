import re
import random
import math
from logging import debug, warning


dice_pattern = re.compile(r"^(\d*)[dD](\d+)$")


# ---- Stat Modifier ----
def get_stat_modifier(score: int) -> int:
    return (score - 10) // 2


# ---- Variable Substitution ----
def substitute_variables(expr: str, entity=None, mind: int = 1) -> str:
    expr = expr.strip().replace("[MIND]", str(mind))
    expr = re.sub(r"\bMIND\b", str(mind), expr)

    if entity:
        for key in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
            val = get_stat_modifier(entity.stats.get(key.lower(), 10))
            expr = re.sub(rf"\b{key}\b", str(val), expr)
    return expr


# ---- Dice Parsing ----
def extract_dice_terms(expr: str) -> list[str]:
    """
    Extracts all dice terms like '1d8', '2D6', or 'd4' from an expression.
    """
    return re.findall(r"\b\d*[dD]\d+\b", expr)


def parse_and_roll_dice(term: str) -> tuple[int, list[int]]:
    """
    Parses a dice term like '2d6' or 'd8' and rolls it.
    Returns (sum, [individual rolls]).
    """
    match = dice_pattern.match(term.strip())
    if not match:
        warning(f"Invalid dice string: '{term}'")
        return 0, []

    num_str, sides_str = match.groups()
    num = int(num_str) if num_str else 1
    sides = int(sides_str)

    rolls = [random.randint(1, sides) for _ in range(num)]
    return sum(rolls), rolls


def roll_dice(term: str) -> int:
    total, _ = parse_and_roll_dice(term)
    return total


def roll_dice_expression(expr: str) -> int:
    expr = expr.upper()
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
def roll_expression(expr: str, entity=None, mind: int = 1) -> int:
    substituted = substitute_variables(expr, entity, mind)
    debug(f"Substituted expression: {substituted}")
    return roll_dice_expression(substituted)


def roll_and_describe(expr: str, entity=None, mind: int = 1) -> tuple[int, str]:
    original_expr = expr
    substituted = substitute_variables(expr, entity, mind)
    dice_terms = extract_dice_terms(substituted)
    breakdown = substituted

    components = []
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


def evaluate_expression(expr: str, entity=None, mind: int = 1) -> int:
    substituted = substitute_variables(expr, entity, mind)
    try:
        return int(eval(substituted, {"__builtins__": None}, math.__dict__))
    except Exception as e:
        warning(f"Failed to evaluate '{substituted}': {e}")
        return 0
