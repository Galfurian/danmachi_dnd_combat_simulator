from typing import Any, Optional

from core.constants import get_effect_emoji, apply_character_type_color, apply_damage_type_color, get_damage_type_emoji
from core.utils import cprint, roll_and_describe
from combat.damage import DamageComponent

from .base_effect import Effect


class DamageOverTimeEffect(Effect):
    """
    Damage over Time effect that deals damage each turn.

    Damage over Time effects continuously damage the target for a specified duration,
    using a damage roll expression that can include variables like MIND level.
    """

    def __init__(
        self,
        name: str,
        description: str,
        max_duration: int,
        damage: DamageComponent,
    ):
        super().__init__(name, description, max_duration)
        self.damage: DamageComponent = damage

        self.validate()

    def turn_update(
        self, actor: Any, target: Any, mind_level: Optional[int] = 1
    ) -> None:
        """
        Apply damage over time to the target.

        Args:
            actor (Any): The character who applied the DoT effect.
            target (Any): The character receiving the damage.
            mind_level (Optional[int]): The mind level for damage calculation. Defaults to 1.
        """
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        # Calculate the damage amount using the provided expression.
        dot_value, dot_desc, _ = roll_and_describe(self.damage.damage_roll, variables)
        # Asser that the damage value is a positive integer.
        assert (
            isinstance(dot_value, int) and dot_value >= 0
        ), f"DamageOverTimeEffect '{self.name}' must have a non-negative integer damage value, got {dot_value}."
        # Apply the damage to the target.
        base, adjusted, taken = target.take_damage(dot_value, self.damage.damage_type)
        # If the damage value is positive, print the damage message.
        dot_str = f"    {get_effect_emoji(self)} "
        dot_str += apply_character_type_color(target.type, target.name) + " takes "
        # Create a damage string for display.
        dot_str += apply_damage_type_color(
            self.damage.damage_type,
            f"{taken} {get_damage_type_emoji(self.damage.damage_type)} ",
        )
        # If the base damage differs from the adjusted damage (due to resistances),
        # include the original and adjusted values in the damage string.
        if base != adjusted:
            dot_str += f"[dim](reduced: {base} → {adjusted})[/] "
        # Append the rolled damage expression to the damage string.
        dot_str += f"({dot_desc})"
        # Add the damage string to the list of damage details.
        cprint(dot_str)
        # If the target is defeated, print a message.
        if not target.is_alive():
            cprint(f"    [bold red]{target.name} has been defeated![/]")

    def validate(self) -> None:
        """
        Validate the DoT effect's properties.

        Raises:
            AssertionError: If validation conditions are not met.
        """
        super().validate()
        assert self.max_duration > 0, "DamageOverTimeEffect duration must be greater than 0."
        assert isinstance(
            self.damage, DamageComponent
        ), "Damage must be of type DamageComponent."
