from typing import Any, Tuple

from core.constants import (
    BonusType,
    DamageType,
    GLOBAL_VERBOSE_LEVEL,
    apply_damage_type_color,
    get_damage_type_emoji,
)
from core.utils import roll_and_describe
from core.error_handling import log_error, log_warning


class DamageComponent:
    """Represents a single component of damage, including its roll expression and type.

    This class encapsulates the logic for defining and validating damage components,
    which include a damage roll expression and a damage type (e.g., PHYSICAL, FIRE).
    It also provides methods for serialization and deserialization.
    """

    def __init__(self, damage_roll: str, damage_type: DamageType):
        """Initialize a new DamageComponent.

        Args:
            damage_roll (str): The damage roll expression (e.g., "1d6+3").
            damage_type (DamageType): The type of damage (e.g., PHYSICAL, FIRE).

        Raises:
            ValueError: If the damage roll or damage type is invalid.
        """
        # Validate inputs
        if not damage_roll or not isinstance(damage_roll, str):
            log_error(
                f"Damage roll must be a non-empty string, got: {damage_roll}",
                {"damage_roll": damage_roll, "damage_type": damage_type},
            )
            raise ValueError(f"Invalid damage roll: {damage_roll}")

        if not isinstance(damage_type, DamageType):
            log_error(
                f"Damage type must be DamageType enum, got: {type(damage_type).__name__}",
                {"damage_roll": damage_roll, "damage_type": damage_type},
            )
            raise ValueError(f"Invalid damage type: {damage_type}")

        self.damage_roll: str = damage_roll.strip()
        self.damage_type: DamageType = damage_type

    def to_dict(self) -> dict[str, Any]:
        """Serialize the DamageComponent to a dictionary.

        Returns:
            dict[str, Any]: A dictionary representation of the damage component.
        """
        try:
            return {
                "damage_roll": self.damage_roll,
                "damage_type": self.damage_type.name,
            }
        except Exception as e:
            log_error(
                f"Error serializing DamageComponent to dict: {str(e)}",
                {"damage_roll": self.damage_roll, "damage_type": self.damage_type},
                e,
            )
            return {"damage_roll": str(self.damage_roll), "damage_type": "PHYSICAL"}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "DamageComponent":
        """Deserialize a DamageComponent from a dictionary.

        Args:
            data (dict[str, Any]): A dictionary containing damage component data.

        Returns:
            DamageComponent: The deserialized damage component.

        Raises:
            ValueError: If the data is invalid or missing required fields.
        """
        try:
            if not isinstance(data, dict):
                log_error(
                    f"DamageComponent data must be dict, got: {type(data).__name__}",
                    {"data": data},
                )
                raise ValueError(f"Invalid data type: {type(data)}")

            if "damage_roll" not in data:
                log_error(
                    "Missing required field 'damage_roll' in DamageComponent data",
                    {"data": data},
                )
                raise ValueError("Missing damage_roll field")

            if "damage_type" not in data:
                log_error(
                    "Missing required field 'damage_type' in DamageComponent data",
                    {"data": data},
                )
                raise ValueError("Missing damage_type field")

            damage_type_str = data["damage_type"]
            if not hasattr(DamageType, damage_type_str):
                log_error(
                    f"Unknown damage type: {damage_type_str}",
                    {"data": data, "damage_type": damage_type_str},
                )
                raise ValueError(f"Unknown damage type: {damage_type_str}")

            return DamageComponent(
                damage_roll=data["damage_roll"],
                damage_type=DamageType[damage_type_str],
            )

        except Exception as e:
            if not isinstance(e, ValueError):
                log_error(
                    f"Unexpected error creating DamageComponent from dict: {str(e)}",
                    {"data": data},
                    e,
                )
            raise


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
        damage_components (list[Tuple[DamageComponent, int]]): The damage components being applied.

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
