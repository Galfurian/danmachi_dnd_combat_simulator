"""
Dice parser module for the simulator.

Provides a safe dice expression parser to replace eval() usage, supporting
mathematical operations, dice rolls, and custom functions for combat calculations.
"""

import math
import random
import re
from collections.abc import Callable
from logging import debug
from typing import Any

from catchery import log_warning
from pydantic import BaseModel, Field


class VarInfo(BaseModel):
    """Class to hold variable information."""

    name: str = Field(description="Variable name")
    value: int = Field(description="Variable value")

    def model_post_init(self, _: Any) -> None:
        """Validates fields after model initialization."""
        if not self.name or not isinstance(self.name, str):
            raise ValueError("name must be a non-empty string")
        if not isinstance(self.value, int):
            raise ValueError("value must be an integer")
        # Normalize name to uppercase.
        self.name = self.name.upper().strip()

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


class DiceParser:
    """Safe parser for dice expressions without using eval()."""

    DICE_PATTERN = re.compile(r"(\d*)d(\d+)([+-]\d+)?", re.IGNORECASE)
    SIMPLE_MATH = re.compile(r"^[\d\s\+\-\*\/\(\)]+$")

    @staticmethod
    def parse_dice(expression: str) -> tuple[int, str]:
        """
        Safely parse and roll dice expressions.

        Args:
            expression: Dice expression like "1d20+5" or "2d6"

        Returns:
            tuple of (result, description)

        Raises:
            ValueError: If expression is invalid

        """
        if not expression:
            print("Empty dice expression provided", {"expression": expression})
            raise ValueError("Invalid dice expression: empty")

        # Remove whitespace and convert to uppercase
        try:
            expr = expression.strip().upper()
        except Exception as e:
            print(
                f"Error processing dice expression: {e!s}",
                {"expression": expression},
                e,
                True,
            )
            raise ValueError(f"Error processing expression: {e}")

        # Handle simple numbers
        if expr.isdigit():
            try:
                value = int(expr)
                if value < 0:
                    print(
                        f"Negative values not allowed in dice expressions: {value}",
                        {"expression": expression, "value": value},
                    )
                    raise ValueError(f"Negative value: {value}")
                return value, str(value)
            except ValueError as e:
                print(
                    f"Invalid numeric expression: {expression}",
                    {"expression": expression},
                    e,
                )
                raise

        # Find all dice rolls
        total = 0
        details = []

        # Replace dice rolls with their results
        def roll_dice(match: re.Match[str]) -> str:
            """
            Helper function to process individual dice roll matches.

            Args:
                match (re.Match[str]): Regular expression match object containing dice notation.

            Returns:
                str: String representation of the dice roll result.

            Raises:
                ValueError: If dice parameters are invalid.

            """
            nonlocal total, details

            try:
                count_str, sides_str, modifier_str = match.groups()
                count = int(count_str) if count_str else 1
                sides = int(sides_str)
                modifier = int(modifier_str) if modifier_str else 0

                if count <= 0:
                    print(
                        f"Invalid dice count: {count}",
                        {"expression": expression, "count": count, "sides": sides},
                    )
                    raise ValueError(f"Invalid dice count: {count}")

                if count > 100:  # Reasonable limits
                    print(
                        f"Too many dice: {count} (limit: 100)",
                        {"expression": expression, "count": count, "sides": sides},
                    )
                    raise ValueError(f"Too many dice: {count}")

                if sides <= 0:
                    print(
                        f"Invalid dice sides: {sides}",
                        {"expression": expression, "count": count, "sides": sides},
                    )
                    raise ValueError(f"Invalid dice sides: {sides}")

                if sides > 1000:
                    print(
                        f"Too many sides: {sides} (limit: 1000)",
                        {"expression": expression, "count": count, "sides": sides},
                    )
                    raise ValueError(f"Too many sides: {sides}")

                rolls = [random.randint(1, sides) for _ in range(count)]
                roll_sum = sum(rolls) + modifier

                total += roll_sum

                if count == 1:
                    detail = f"d{sides}({rolls[0]})"
                else:
                    detail = f"{count}d{sides}({'+'.join(map(str, rolls))})"

                if modifier != 0:
                    detail += f"{modifier:+d}"

                details.append(detail)
                return str(roll_sum)

            except Exception as e:
                print(
                    f"Error rolling dice in expression '{expression}': {e!s}",
                    {"expression": expression, "match": match.group()},
                    e,
                )
                raise ValueError(f"Error rolling dice: {e}")

        try:
            # Replace dice expressions
            processed = DiceParser.DICE_PATTERN.sub(roll_dice, expr)

            # Handle any remaining simple math
            if DiceParser.SIMPLE_MATH.match(processed):
                try:
                    # Safe evaluation of simple arithmetic
                    total = eval(processed, {"__builtins__": {}}, {})
                    description = " + ".join(details) if details else processed
                    return int(total), description
                except Exception as e:
                    print(
                        f"Error evaluating processed expression '{processed}': {e!s}",
                        {"original": expression, "processed": processed},
                        e,
                    )
                    raise ValueError(f"Invalid expression: {e}")
            else:
                print(
                    f"Unsafe expression detected: {expression}",
                    {"expression": expression, "processed": processed},
                )
                raise ValueError(f"Unsafe expression: {expression}")

        except ValueError:
            raise  # Re-raise ValueError as-is
        except Exception as e:
            print(
                f"Unexpected error parsing dice expression '{expression}': {e!s}",
                {"expression": expression},
                e,
                True,
            )
            raise ValueError(f"Unexpected error: {e}")


DICE_PATTERN = re.compile(r"^(\d*)[dD](\d+)$")


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
            Exception("Error evaluating dice expression."),
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
            Exception("Error evaluating dice expression."),
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
        r"\b(\d+\s*[\+\-\*\/]\s*\d+)\b",
        lambda m: str(eval(m.group(0), {"__builtins__": None}, math.__dict__)),
        substituted,
    )
    return substituted
