from typing import Any, Tuple

from constants import *
from utils import *


class DamageComponent:
    def __init__(self, damage_roll: str, damage_type: DamageType):
        self.damage_roll: str = damage_roll
        self.damage_type: DamageType = damage_type

    def to_dict(self) -> dict[str, Any]:
        return {
            "damage_roll": self.damage_roll,
            "damage_type": self.damage_type.name,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "DamageComponent":
        return DamageComponent(
            damage_roll=data["damage_roll"],
            damage_type=DamageType[data["damage_type"]],
        )


def roll_damage_components(
    actor: Any,
    target: Any,
    damage_components: list[DamageComponent],
    mind_level: int = 1,
) -> Tuple[int, list[str]]:
    """
    Applies a list of damage components to the target, handles resistances,
    and returns total damage dealt plus breakdown strings.

    Returns:
        (total_damage, damage_details)
    """
    total_damage = 0
    damage_details: list[str] = []
    for component in damage_components:
        # Substitute variables in the damage roll expression.
        damage_expr = substitute_variables(component.damage_roll, actor, mind_level)
        # Roll the damage expression.
        damage_amount = roll_expression(damage_expr, actor, mind_level)
        # Apply the damage to the target, taking into account resistances.
        base, adjusted, taken = target.take_damage(damage_amount, component.damage_type)
        # Accumulate the total damage taken by the target.
        total_damage += taken
        # Create a damage string for display.
        dmg_str = apply_damage_type_color(
            component.damage_type,
            f"{taken} {get_damage_type_emoji(component.damage_type)} ",
        )
        # If the base damage differs from the adjusted damage (due to resistances),
        # include the original and adjusted values in the damage string.
        if base != adjusted:
            dmg_str += f"[dim]({base} → {adjusted})[/]"
        # Append the rolled damage expression to the damage string.
        dmg_str += f"({damage_expr})"
        # Add the damage string to the list of damage details.
        damage_details.append(dmg_str)
    return total_damage, damage_details
