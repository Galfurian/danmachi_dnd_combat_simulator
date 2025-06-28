from logging import info, debug, warning, error

import random
import re


def get_stat_modifier(value):
    """Calculates the D&D-style modifier for a given stat value."""
    return (value - 10) // 2


def get_prop_value(entity, name, mind_level):
    """
    Retrieves the numerical value for a given operand string from an entity.
    This handles raw numbers, D&D stat properties (e.g., .str, .cha),
    stat names (e.g., "strength"), and "MIND".

    Args:
        entity (Character): The character object.
        name (str): The string name of the operand (e.g., "strength", "CHA", "mind", "5").
        mind_level (int): The current mind level for [MIND] and MIND scaling.

    Returns:
        int: The resolved numerical value, or 0 if not found/error.
    """
    # Try to convert to integer first (for direct numbers like "5")
    try:
        return int(name)
    except ValueError:
        pass  # Not a simple integer, proceed to check entity properties/stats

    # Check for specific keywords
    if name.upper() == "MIND":
        return mind_level

    if entity:
        # Check if it's a property (e.g., entity.str, entity.dex, entity.cha)
        # These properties already return the modifier, which is often what we want.
        prop_value = getattr(entity, name.upper(), None)
        if prop_value is not None:
            return prop_value
        # Check if it's a raw stat name from the .stats dictionary (e.g., "strength")
        # If so, get its modifier.
        if name.upper() in entity.stats:
            return get_stat_modifier(entity.stats[name.upper()])
        warning(f"Warning: Could not resolve operand '{name}'. Defaulting to 0.")
    else:
        warning(f"Warning: No entity provided to resolve '{name}'. Defaulting to 0.")
    return 0


def _roll_single_dice_string(dice_str):
    """
    Parses a single dice string (e.g., "2d6") and rolls the dice.

    Args:
        dice_str (str): The dice string (e.g., "2d6", "1d20").

    Returns:
        int: The sum of the dice rolls.
    """
    parts = dice_str.lower().split("d")
    if len(parts) != 2:
        warning(f"Warning: Invalid dice format '{dice_str}'.")
        return 0
    try:
        num_dice = int(parts[0])
        sides = int(parts[1])
        if num_dice <= 0 or sides <= 0:
            return 0
        return sum(random.randint(1, sides) for _ in range(num_dice))
    except ValueError:
        warning(f"Warning: Invalid numbers in dice string '{dice_str}'.")
        return 0


# --- Main Refactored roll_expression Function ---


def evaluate_expression(
    expr: str, entity=None, mind_level: int = 1
) -> int:
    """
    Evaluates a numeric expression string that may contain stats and MIND,
    but must NOT contain dice rolls.

    Example: "2 + [MIND]", "CHA * 2", "floor([MIND] / 2) + 1"
    """
    import math

    safe_globals = {
        "floor": math.floor,
        "ceil": math.ceil,
        "min": min,
        "max": max,
        "abs": abs,
    }

    # Replace stat keywords
    expr_clean = expr.strip()
    if "[MIND]" in expr_clean:
        expr_clean = expr_clean.replace("[MIND]", str(mind_level))
    expr_clean = re.sub(r"\bMIND\b", str(mind_level), expr_clean)

    # Replace stats with actual values
    if entity:
        for key in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
            val = get_prop_value(entity, key, mind_level)
            expr_clean = re.sub(rf"\b{key}\b", str(val), expr_clean)

    try:
        result = eval(expr_clean, safe_globals, {})
        return max(0, int(result))  # Ensure non-negative integer
    except Exception as e:
        warning(f"evaluate_expression failed on '{expr}': {e}")
        return 1  # fallback


def roll_expression(roll_string, entity=None, mind_level=1):
    """
    Rolls dice and calculates the total based on a roll string,
    potentially incorporating a Character's stats and DanMachi mind-based scaling.

    Args:
        roll_string (str): The string representing the roll (e.g., "2d6+STR", "1d4+3", "[MIND]d8+CHA", "MIND*CHA_MOD").
                           Stat modifiers should be uppercase abbreviations (STR, DEX, CON, INT, WIS, CHA)
                           or full stat names (strength, dexterity, etc.).
                           '[MIND]' will be replaced by mind_level.
        entity (Character, optional): The character object whose stats should be used.
                                      Required if the roll_string includes stat modifiers.
        mind_level (int, optional): The current "level" of the spell for [MIND] scaling. Defaults to 1.

    Returns:
        int: The total result of the roll.
    """
    total_result = 0
    processing_string = roll_string.strip()  # Work with a mutable copy

    debug(f"Processing roll string: '{roll_string}' (MIND Level: {mind_level})")

    # 1. Handle [MIND] replacement
    if "[MIND]" in processing_string:
        processing_string = processing_string.replace("[MIND]", str(mind_level))
        debug(f"After [MIND] replacement: '{processing_string}'")

    # 2. Process multiplication expressions first (e.g., "MIND*CHA_MOD", "2*STR")
    # This regex looks for: (word character string or number) * (word character string or number)
    # It attempts to handle multiple multiplications, processing one at a time and replacing it.
    while True:
        match = re.search(
            r"(\b\w+\b)\s*\*\s*(\b\w+\b)", processing_string, re.IGNORECASE
        )
        if not match:
            break  # No more multiplications found

        operand1_str, operand2_str = match.groups()

        val1 = get_prop_value(entity, operand1_str, mind_level)
        val2 = get_prop_value(entity, operand2_str, mind_level)

        multiplication_result = val1 * val2

        # Replace the matched multiplication part with its calculated value in the string
        processing_string = processing_string.replace(
            match.group(0), str(multiplication_result), 1
        )
        debug(
            f"After multiplication '{match.group(0)}' -> '{multiplication_result}': '{processing_string}'"
        )

    # 3. Extract and process all dice rolls (e.g., "2d6", "-1d4")
    # This regex captures an optional sign, number of dice, 'd', and sides.
    dice_matches = list(
        re.finditer(r"([+-]?\s*\d+D\d+)", processing_string, re.IGNORECASE)
    )

    # Track parts of the string that are not dice, so we can process them later.
    remaining_additive_parts = []
    last_idx = 0

    for match in dice_matches:
        full_dice_match = match.group(0).strip()

        # Add the non-dice part before this match
        if match.start() > last_idx:
            remaining_additive_parts.append(
                processing_string[last_idx : match.start()].strip()
            )

        # Determine the sign for the dice roll
        sign = 1
        pure_dice_str = full_dice_match
        if full_dice_match.startswith("-"):
            sign = -1
            pure_dice_str = full_dice_match[1:].strip()
        elif full_dice_match.startswith("+"):
            pure_dice_str = full_dice_match[1:].strip()

        # Remove the number of dice if it's explicitly part of the string like "2d6"
        # The _roll_single_dice_string expects "XdY", not "+XdY" or "-XdY".
        dice_only_pattern = re.search(r"(\d+D\d+)", pure_dice_str, re.IGNORECASE)
        if dice_only_pattern:
            rolled_value = _roll_single_dice_string(dice_only_pattern.group(0)) * sign
            total_result += rolled_value
            debug(
                f"Rolled '{full_dice_match}' -> {rolled_value}. Current total: {total_result}"
            )
        else:
            warning(f"Warning: Could not parse dice roll part '{full_dice_match}'.")

        last_idx = match.end()

    # Add any remaining part of the string after the last dice match
    if last_idx < len(processing_string):
        remaining_additive_parts.append(processing_string[last_idx:].strip())

    # Reconstruct the string without dice rolls, preparing for additive/subtractive parsing
    # This step simplifies the remaining string, effectively removing dice parts.
    # It's not strictly necessary to rebuild the string if we're careful with regex and indices,
    # but it can make the next step simpler.
    # For now, let's just use the parts we've collected.
    remaining_string_for_additive = " ".join(p for p in remaining_additive_parts if p)
    debug(
        f"Remaining string for additive/subtractive processing: '{remaining_string_for_additive}'"
    )

    # 4. Process remaining additions and subtractions (e.g., "+3", "-CHA", "+STAT")
    # Split by explicit '+' or '-' operators, keeping the operators.
    parts_with_ops = re.split(r"([+-])", remaining_string_for_additive)

    current_operator = "+"  # Default to addition for the first part if no leading sign
    for part in parts_with_ops:
        part = part.strip()
        if not part:
            continue

        if part == "+":
            current_operator = "+"
        elif part == "-":
            current_operator = "-"
        else:
            value = get_prop_value(entity, part, mind_level)

            if current_operator == "+":
                total_result += value
                debug(f"Adding {part} ({value}). Current total: {total_result}")
            elif current_operator == "-":
                total_result -= value
                debug(f"Subtracting {part} ({value}). Current total: {total_result}")

    debug(f"Final result for '{roll_string}': {total_result}")
    return total_result
