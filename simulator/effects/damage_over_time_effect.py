from typing import Any, Literal

from combat.damage import DamageComponent
from core.utils import VarInfo, cprint, roll_and_describe
from pydantic import Field, model_validator

from .base_effect import ActiveEffect, Effect


class DamageOverTimeEffect(Effect):
    """
    Damage over Time effect that deals damage each turn.

    Damage over Time effects continuously damage the target for a specified duration,
    using a damage roll expression that can include variables like MIND level.
    """

    effect_type: Literal["DamageOverTimeEffect"] = "DamageOverTimeEffect"

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
        self,
        effect: ActiveEffect,
    ) -> None:
        """
        Apply damage over time to the target.

        Args:
            effect (ActiveEffect):
                The active effect instance containing actor, target, and
                variables.

        """

        # Calculate the damage amount using the provided expression.
        outcome = roll_and_describe(
            self.damage.damage_roll,
            effect.variables,
        )
        if outcome.value < 0:
            raise ValueError(
                "Damage value must be non-negative for DamageOverTimeEffect"
                f" '{self.name}', got {outcome.value}."
            )
        # Apply the damage to the target.
        base, adjusted, taken = effect.target.take_damage(
            outcome.value, self.damage.damage_type
        )
        # If the damage value is positive, print the damage message.
        dot_str = f"    {self.emoji} "
        dot_str += effect.target.char_type.colorize(effect.target.name) + " takes "
        # Create a damage string for display.
        dot_str += f"{self.damage.damage_type.colorize(taken)} "
        dot_str += f"{self.damage.damage_type.emoji} "
        dot_str += f"{self.damage.damage_type.colored_name} "
        # If the base damage differs from the adjusted damage (due to resistances),
        # include the original and adjusted values in the damage string.
        if base != adjusted:
            dot_str += f"[dim](reduced: {base} → {adjusted})[/] "
        # Append the rolled damage expression to the damage string.
        dot_str += f"({outcome.description})"
        # Add the damage string to the list of damage details.
        cprint(dot_str)
        # If the target is defeated, print a message.
        if not effect.target.is_alive():
            cprint(f"    [bold red]{effect.target.name} has been defeated![/]")
