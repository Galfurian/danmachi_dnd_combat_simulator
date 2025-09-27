from typing import Literal

from combat.damage import DamageComponent
from core.dice_parser import roll_and_describe
from core.utils import cprint
from pydantic import Field

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

    def model_post_init(self, _) -> None:
        if self.duration is None or self.duration <= 0:
            raise ValueError(
                "Duration must be a positive integer for DamageOverTimeEffect."
            )
        if not isinstance(self.damage, DamageComponent):
            raise ValueError("Damage must be of type DamageComponent.")


class ActiveDamageOverTimeEffect(ActiveEffect):
    """
    Active Damage over Time effect that deals damage each turn.
    """

    @property
    def damage_over_time_effect(self) -> DamageOverTimeEffect:
        """
        Get the effect as a DamageOverTimeEffect (narrowed type for clarity).

        Raises:
            TypeError:
                If the effect is not a DamageOverTimeEffect.

        Returns:
            DamageOverTimeEffect:
                The effect cast as a DamageOverTimeEffect.

        """
        if not isinstance(self.effect, DamageOverTimeEffect):
            raise TypeError("Effect is not a DamageOverTimeEffect.")
        return self.effect

    def turn_update(self) -> None:
        """
        Update the effect for the current turn by calling the effect's
        turn_update method.
        """
        DOT = self.damage_over_time_effect

        # Calculate the damage amount using the provided expression.
        outcome = roll_and_describe(
            DOT.damage.damage_roll,
            self.variables,
        )
        if outcome.value < 0:
            raise ValueError(
                "Damage value must be non-negative for DamageOverTimeEffect"
                f" '{DOT.name}', got {outcome.value}."
            )
        # Apply the damage to the target.
        base, adjusted, taken = self.target.take_damage(
            outcome.value, DOT.damage.damage_type
        )
        # If the damage value is positive, print the damage message.
        dot_str = f"    {DOT.emoji} "
        dot_str += self.target.colored_name + " takes "
        # Create a damage string for display.
        dot_str += f"{DOT.damage.color_roll(taken)} "
        # If the base damage differs from the adjusted damage (due to resistances),
        # include the original and adjusted values in the damage string.
        if base != adjusted:
            dot_str += f"[dim](reduced: {base} → {adjusted})[/] "
        # Append the rolled damage expression to the damage string.
        dot_str += f"({outcome.description})"
        # Print the damage string.
        cprint(dot_str)
        # If the target is defeated, print a message.
        if not self.target.is_alive():
            cprint(f"    [bold red]{self.target.name} has been defeated![/]")
