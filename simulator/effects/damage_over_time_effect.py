from typing import Any

from combat.damage import DamageComponent
from core.utils import cprint, roll_and_describe
from pydantic import Field, model_validator

from .base_effect import Effect


class DamageOverTimeEffect(Effect):
    """
    Damage over Time effect that deals damage each turn.

    Damage over Time effects continuously damage the target for a specified duration,
    using a damage roll expression that can include variables like MIND level.
    """

    damage: DamageComponent = Field(
        description="Damage component defining the damage roll and type.",
    )

    @property
    def color(self) -> str:
        """Returns the color string for damage over time effects."""
        return "bold magenta"

    @property
    def emoji(self) -> str:
        """Returns the emoji for damage over time effects."""
        return "❣️"

    @model_validator(mode="after")
    def check_duration(self) -> Any:
        if self.duration is None or self.duration <= 0:
            raise ValueError(
                "Duration must be a positive integer for DamageOverTimeEffect."
            )
        return self

    @model_validator(mode="after")
    def check_damage(self) -> Any:
        if not isinstance(self.damage, DamageComponent):
            raise ValueError("Damage must be of type DamageComponent.")
        return self

    def turn_update(
        self, actor: Any, target: Any, mind_level: int | None = 1
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
        dot_str = f"    {self.emoji} "
        dot_str += target.char_type.colorize(target.name) + " takes "
        # Create a damage string for display.
        dot_str += f"{self.damage.damage_type.colorize(taken)} "
        dot_str += f"{self.damage.damage_type.emoji} "
        dot_str += f"{self.damage.damage_type.colored_name} "
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
