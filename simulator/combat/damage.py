"""
Damage module for the simulator.

Handles damage calculation, application, and resolution, including
damage components, types, and effects on characters.
"""

from typing import Any

from core.constants import DamageType
from core.dice_parser import VarInfo, roll_and_describe
from pydantic import BaseModel, Field


class DamageComponent(BaseModel):
    """Represents a single component of damage, including its roll expression and type.

    This class encapsulates the logic for defining and validating damage components,
    which include a damage roll expression and a damage type (e.g., PHYSICAL, FIRE).
    It also provides methods for serialization and deserialization.
    """

    damage_roll: str = Field(
        description="The damage roll expression (e.g., '1d6+3')",
    )
    damage_type: DamageType = Field(
        description="The type of damage (e.g., PHYSICAL, FIRE)",
    )

    def model_post_init(self, _: Any) -> None:
        """Validates fields after model initialization."""
        if not self.damage_roll:
            raise ValueError("damage_roll must be a non-empty string")
        if not isinstance(self.damage_type, DamageType):
            raise ValueError("damage_type must be an instance of DamageType")
        # Remove space before and after '+' in damage_roll.
        self.damage_roll = self.damage_roll.replace(" +", "+").replace("+ ", "+")
        self.damage_roll = self.damage_roll.replace(" -", "-").replace("- ", "-")

    def color_roll(self, taken: Any) -> str:
        """
        Colors the damage taken based on the damage type.

        Args:
            taken (int):
                The amount of damage taken.

        Returns:
            str:
                The colored damage string.

        """
        return (
            f"{self.damage_type.colorize(str(taken))} "
            f"{self.damage_type.emoji} "
            f"{self.damage_type.colored_name}"
        )

    def __str__(self) -> str:
        return self.color_roll(f"({self.damage_roll})")


def roll_damage_component(
    actor: Any,
    target: Any,
    damage_component: DamageComponent,
    variables: list[VarInfo] = [],
) -> tuple[int, str]:
    """
    Applies a single damage component to the target, handles resistances,
    and returns the damage dealt along with a description string.

    Args:
        actor (Any):
            The actor applying the damage.
        target (Any):
            The target receiving the damage.
        damage_component (DamageComponent):
            The damage component being applied.
        variables (list[VarInfo]):
            Optional variables for damage roll expressions. If nothing is
            provided, the actors variables will be used.

    Returns:
        Tuple[int, str]: The damage dealt and a description string.

    """
    from character.main import Character

    assert isinstance(actor, Character), "Actor must be an object"
    assert isinstance(target, Character), "Target must be an object"

    # Use actor's variables if none are provided.
    variables = variables or actor.get_expression_variables()

    damage = roll_and_describe(
        damage_component.damage_roll,
        variables,
    )
    # Apply the damage to the target, taking into account resistances.
    base, adjusted, taken = target.take_damage(
        damage.value,
        damage_component.damage_type,
    )
    # Create a damage string for display.
    dmg_str = f"{damage_component.damage_type.colorize(str(taken))} "
    dmg_str += f"{damage_component.damage_type.emoji} "
    dmg_str += f"{damage_component.damage_type.colored_name} "
    # If the base damage differs from the adjusted damage (due to resistances),
    # include the original and adjusted values in the damage string.
    if base != adjusted:
        dmg_str += f"[dim](reduced: {base} → {adjusted})[/]"
    # Append the rolled damage expression to the damage string.
    dmg_str += f"({damage.description})"
    return taken, dmg_str


def roll_damage_components(
    actor: Any,
    target: Any,
    damage_components: list[DamageComponent],
    variables: list[VarInfo],
) -> tuple[int, list[str]]:
    """
    Rolls damage for multiple components and returns the total damage and
    details.

    Args:
        actor (Any):
            The actor applying the damage.
        target (Any):
            The target receiving the damage.
        damage (list[DamageComponent]):
            The damage components being applied.
        variables (list[VarInfo]):
            The variables for damage roll expressions.

    Returns:
        tuple[int, list[str]]:
            The total damage dealt and a list of damage detail strings.

    """
    if not damage_components:
        return 0, []

    from character.main import Character

    assert isinstance(actor, Character), "Actor must be an object"
    assert isinstance(target, Character), "Target must be an object"
    assert variables, "Variables list cannot be empty"

    total_damage = 0
    damage_details: list[str] = []
    for damage_component in damage_components:
        # Roll the damage for the current component.
        dmg_value, dmg_str = roll_damage_component(
            actor,
            target,
            damage_component,
            variables,
        )
        # Add the rolled damage to the total.
        total_damage += dmg_value
        # Add the damage string to the list of damage details.
        damage_details.append(dmg_str)
    return total_damage, damage_details


def get_full_expr(
    components: list[str],
    variables: list[VarInfo],
) -> str:
    """
    Returns the damage expression with variables substituted.

    Args:
        actor:
            The character using the ability
        components:
            List of damage components to build expression from
        variables:
            Additional variables to include in the expression

    Returns:
        str:
            Complete damage expression with variables replaced by values

    """
    assert components, "components list cannot be empty"
    assert variables, "variables list cannot be empty"

    from core.dice_parser import substitute_variables

    return " + ".join(
        substitute_variables(component, variables) for component in components
    )


def get_damage_expr(
    damage_components: list["DamageComponent"],
    variables: list[VarInfo],
) -> str:
    """
    Returns the damage expression with variables substituted.

    Args:
        damage_components:
            List of damage components to build expression from
        variables:
            Additional variables to include in the expression

    Returns:
        str:
            Complete damage expression with variables replaced by values

    """
    if not damage_components:
        return "0"

    assert variables, "variables list cannot be empty"

    from core.dice_parser import substitute_variables

    return " + ".join(
        substitute_variables(component.damage_roll, variables)
        for component in damage_components
    )


def get_min_damage(
    damage_components: list["DamageComponent"],
    variables: list[VarInfo] = [],
) -> int:
    """
    Returns the minimum possible damage value for the ability.

    Args:
        damage_components:
            List of damage components to calculate from
        variables:
            Additional variables to include in the calculation

    Returns:
        int:
            Minimum total damage across all damage components

    """
    if not damage_components:
        return 0

    from core.dice_parser import get_min_roll

    assert variables, "variables list cannot be empty"

    expr = " + ".join(component.damage_roll for component in damage_components)

    return get_min_roll(expr, variables)


def get_max_damage(
    damage_components: list["DamageComponent"],
    variables: list[VarInfo] = [],
) -> int:
    """
    Returns the maximum possible damage value for the ability.

    Args:
        damage_components:
            List of damage components to calculate from
        variables:
            Additional variables to include in the calculation

    Returns:
        int:
            Maximum total damage across all damage components

    """
    if not damage_components:
        return 0
    
    from core.dice_parser import get_max_roll

    assert variables, "variables list cannot be empty"

    expr = " + ".join(component.damage_roll for component in damage_components)

    return get_max_roll(expr, variables)
