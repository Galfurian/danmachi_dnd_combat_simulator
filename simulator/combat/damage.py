from typing import Any, Tuple

from core.constants import (
    BonusType, DamageType, GLOBAL_VERBOSE_LEVEL,
    apply_damage_type_color, get_damage_type_emoji
)
from core.utils import roll_and_describe


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


def roll_damage_component(
    actor: Any,
    target: Any,
    damage_component: Tuple[DamageComponent, int],
) -> Tuple[int, str]:
    """Applies a single damage component to the target, handles resistances,
    and returns the damage dealt along with a description string.

    Args:
        actor (Any): The actor applying the damage.
        target (Any): The target receiving the damage.
        damage_component (Tuple[DamageComponent, int]): A tuple containing the damage component
            and the mind level to use for the damage roll.

    Returns:
        Tuple[int, str]: The damage dealt and a description string.
    """
    variables = actor.get_expression_variables()
    variables["MIND"] = damage_component[1]
    # Substitute variables in the damage roll expression.
    dmg_value, dmg_desc, _ = roll_and_describe(
        damage_component[0].damage_roll, variables
    )
    assert (
        isinstance(dmg_value, int) and dmg_value >= 0
    ), f"Damange must have a non-negative integer damage value, got {dmg_value}."
    # Apply the damage to the target, taking into account resistances.
    base, adjusted, taken = target.take_damage(
        dmg_value, damage_component[0].damage_type
    )
    # Create a damage string for display.
    dmg_str = apply_damage_type_color(
        damage_component[0].damage_type,
        f"{taken} {get_damage_type_emoji(damage_component[0].damage_type)} ",
    )
    # If the base damage differs from the adjusted damage (due to resistances),
    # include the original and adjusted values in the damage string.
    if base != adjusted:
        dmg_str += f"[dim](reduced: {base} → {adjusted})[/]"
    # Append the rolled damage expression to the damage string.
    dmg_str += f"({dmg_desc})"
    return taken, dmg_str


def roll_damage_components(
    actor: Any, target: Any, damage_components: list[Tuple[DamageComponent, int]]
) -> Tuple[int, list[str]]:
    """Rolls damage for multiple components and returns the total damage and details.

    Args:
        actor (Any): The actor applying the damage.
        target (Any): The target receiving the damage.
        damage_components (list[DamageComponent]): The damage components being applied.
        mind_levels (list[int]): The mind levels to use for the damage rolls.

    Returns:
        Tuple[int, list[str]]: The total damage dealt and a list of damage detail strings.
    """
    total_damage = 0
    damage_details: list[str] = []
    for component in damage_components:
        # Roll the damage for the current component.
        dmg_value, dmg_str = roll_damage_component(actor, target, component)
        # Add the rolled damage to the total.
        total_damage += dmg_value
        # Add the damage string to the list of damage details.
        damage_details.append(dmg_str)
    return total_damage, damage_details


def roll_damage_component_no_mind(
    actor: Any, target: Any, damage_component: DamageComponent
) -> Tuple[int, str]:
    """Rolls a single damage component without mind levels and returns the damage dealt and details.

    Args:
        actor (Any): The actor applying the damage.
        target (Any): The target receiving the damage.
        damage_component (DamageComponent): The damage component being applied.

    Returns:
        Tuple[int, str]: The damage dealt and a description string.
    """
    return roll_damage_component(actor, target, (damage_component, 1))


def roll_damage_components_no_mind(
    actor: Any, target: Any, damage_components: list[DamageComponent]
) -> Tuple[int, list[str]]:
    """Rolls damage for multiple components without mind levels and returns the total damage and details.

    Args:
        actor (Any): The actor applying the damage.
        target (Any): The target receiving the damage.
        damage_components (list[DamageComponent]): The damage components being applied.

    Returns:
        Tuple[int, list[str]]: The total damage dealt and a list of damage detail strings.
    """
    return roll_damage_components(actor, target, [(dc, 1) for dc in damage_components])
