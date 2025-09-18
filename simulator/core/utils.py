import math
import random
import re
from collections.abc import Callable
from logging import debug
from typing import Any

from rich.console import Console
from rich.rule import Rule

DICE_PATTERN = re.compile(r"^(\d*)[dD](\d+)$")


def cprint(*args, **kwargs) -> None:
    """
    Custom print function to handle colored output.

    Args:
        *args: Arguments to pass to the console print function.
        **kwargs: Keyword arguments to pass to the console print function.

    """
    console = Console()
    console.print(*args, **kwargs)


def crule(*args, **kwargs) -> None:
    """
    Custom print function to handle colored output with a rule.

    Args:
        *args: Arguments to pass to the Rule constructor.
        **kwargs: Keyword arguments to pass to the Rule constructor.

    """
    console = Console()
    console.print(Rule(*args, **kwargs))


def ccapture(content: Any) -> str:
    """
    Captures console output as a string.

    Args:
        content (Any): The content to capture.

    Returns:
        str: The captured output as a string.

    """
    console = Console()
    with console.capture() as capture:
        console.print(content, markup=True, end="")
    return capture.get()


# ---- Singleton Metaclass ----


class Singleton(type):
    """Metaclass that returns the same instance every time."""

    _inst = None

    def __call__(cls, *a, **kw) -> Any:
        """
        Creates or returns the singleton instance.

        Args:
            *a: Positional arguments for instance creation.
            **kw: Keyword arguments for instance creation.

        Returns:
            Any: The singleton instance.

        """
        if cls._inst is None:
            cls._inst = super().__call__(*a, **kw)
        return cls._inst


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
        print(
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
def substitute_variables(expr: str, variables: dict[str, int] | None = None) -> str:
    """Substitutes variables in the expression with their corresponding values.

    Args:
        expr (str): The expression to substitute variables in.
        variables (Optional[dict], optional): The variables values to use for substitution. Defaults to None.

    Returns:
        str: The expression with variables substituted.

    """
    if not expr:
        print(
            "Empty expression provided to substitute_variables",
            {"expression": expr, "variables": variables},
        )
        return ""

    if not isinstance(expr, str):
        print(
            f"Expression must be a string, got {type(expr).__name__}",
            {"expression": expr, "type": type(expr).__name__},
        )
        return str(expr) if expr is not None else ""

    expr = expr.upper().strip()
    if expr == "":
        return ""
    if expr.isdigit():
        return str(expr)

    # Replace [MIND] with the mind value.
    try:
        for key, value in variables.items() if variables else {}:
            if not isinstance(key, str):
                print(
                    f"Variable key must be string, got {type(key).__name__}",
                    {"key": key, "value": value},
                )
                continue

            if not isinstance(value, (int, float)):
                print(
                    f"Variable value must be numeric, got {type(value).__name__}",
                    {"key": key, "value": value},
                )
                continue

            if key.upper() in expr:
                expr = expr.replace(f"[{key.upper()}]", str(int(value)))
    except Exception as e:
        print(
            f"Error during variable substitution: {e!s}",
            {"expression": expr, "variables": variables},
            e,
        )
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
        print("Empty dice term provided", {"term": term})
        return 0, []

    if not isinstance(term, str):
        print(
            f"Dice term must be string, got {type(term).__name__}",
            {"term": term},
        )
        return 0, []

    term = term.upper().strip()
    if term == "":
        return 0, []
    if term.isdigit():
        try:
            value = int(term)
            if value < 0:
                print(
                    f"Negative dice value not allowed: {value}",
                    {"term": term, "value": value},
                )
                return 0, []
            return value, [value]
        except ValueError as e:
            print(
                f"Invalid numeric dice term: {term}",
                {"term": term},
                e,
            )
            return 0, []

    match = DICE_PATTERN.match(term)
    if not match:
        print(
            f"Invalid dice string format: '{term}'",
            {"term": term},
        )
        return 0, []

    try:
        num_str, sides_str = match.groups()
        num = int(num_str) if num_str else 1
        sides = int(sides_str)

        # Validate dice parameters
        if num <= 0:
            print(
                f"Number of dice must be positive, got {num}",
                {"term": term, "num": num, "sides": sides},
            )
            return 0, []

        if sides <= 0:
            print(
                f"Number of sides must be positive, got {sides}",
                {"term": term, "num": num, "sides": sides},
            )
            return 0, []

        if num > 100:  # Reasonable limit
            print(
                f"Too many dice requested: {num} (limit: 100)",
                {"term": term, "num": num, "sides": sides},
            )
            return 0, []

        if sides > 1000:  # Reasonable limit
            print(
                f"Too many sides on dice: {sides} (limit: 1000)",
                {"term": term, "num": num, "sides": sides},
            )
            return 0, []

        rolls = dice_action(num, sides)
        return sum(rolls), rolls

    except ValueError as e:
        print(
            f"Error parsing dice values from '{term}': {e!s}",
            {"term": term},
            e,
        )
        return 0, []
    except Exception as e:
        print(
            f"Unexpected error processing dice '{term}': {e!s}",
            {"term": term},
            e,
        )
        return 0, []


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

    # Now evaluate the processed expression safely.
    try:
        return int(eval(processed_expr, {"__builtins__": None}, math.__dict__))
    except Exception as e:
        print(
            f"Failed to evaluate '{processed_expr}': {e}",
            {
                "expression": processed_expr,
                "error": str(e),
                "context": "dice_expression_evaluation",
            },
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
def roll_expression(expr: str, variables: dict[str, int] | None = None) -> int:
    """
    Rolls a dice expression with variable substitution.

    Args:
        expr (str): The dice expression to roll.
        variables (Optional[dict[str, int]]): Variables to substitute in the expression.

    Returns:
        int: The total result of the roll.

    """
    if not expr:
        return 0
    expr = expr.upper().strip()
    if expr == "":
        return 0
    if expr.isdigit():
        return int(expr)
    substituted = substitute_variables(expr, variables)
    debug(f"Substituted expression: {substituted}")
    return roll_dice_expression(substituted)


def get_max_roll(expr: str, variables: dict[str, int] | None = None) -> int:
    """
    Gets the maximum possible roll for a dice expression.

    Args:
        expr (str): The dice expression to analyze.
        variables (Optional[dict[str, int]]): Variables to substitute in the expression.

    Returns:
        int: The maximum possible result.

    """
    if not expr:
        return 0
    expr = expr.upper().strip()
    if expr == "":
        return 0
    if expr.isdigit():
        return int(expr)
    substituted = substitute_variables(expr, variables)
    debug(f"Substituted expression for max roll: {substituted}")
    return parse_expr_and_assume_max_roll(substituted)


def roll_and_describe(
    expr: str, variables: dict[str, int] | None = None
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
        return result, comment, dice_rolls
    except Exception as e:
        print(
            f"Failed to evaluate '{breakdown}': {e}",
            {
                "breakdown": breakdown,
                "original_expr": original_expr,
                "error": str(e),
                "context": "dice_breakdown_evaluation",
            },
        )
        return 0, f"{original_expr} = ERROR", []


def evaluate_expression(expr: str, variables: dict[str, int] | None = None) -> int:
    """
    Evaluates a mathematical expression with variable substitution.

    Args:
        expr (str): The expression to evaluate.
        variables (Optional[dict[str, int]]): Variables to substitute in the expression.

    Returns:
        int: The result of the expression evaluation.

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
        print(
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


def simplify_expression(expr: str, variables: dict[str, int] | None = None) -> str:
    """
    Simplifies an expression by substituting variables and evaluating arithmetic.

    Args:
        expr (str): The expression to simplify.
        variables (Optional[dict[str, int]]): Variables to substitute in the expression.

    Returns:
        str: The simplified expression.

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
