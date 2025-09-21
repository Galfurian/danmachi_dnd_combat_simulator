from typing import Any, Literal

from core.utils import VarInfo, cprint, roll_and_describe
from pydantic import Field, model_validator

from .base_effect import ActiveEffect, Effect


class HealingOverTimeEffect(Effect):
    """
    Heal over Time effect that heals the target each turn.

    Healing over Time effects continuously heal the target for a specified duration,
    using a heal expression that can include variables like MIND level.
    """

    effect_type: Literal["HealingOverTimeEffect"] = "HealingOverTimeEffect"

    heal_per_turn: str = Field(
        description="Heal expression defining the heal amount per turn.",
    )

    @property
    def color(self) -> str:
        """Returns the color string for healing over time effects."""
        return "bold green"

    @property
    def emoji(self) -> str:
        """Returns the emoji for healing over time effects."""
        return "💚"

    @model_validator(mode="after")
    def check_duration(self) -> Any:
        if self.duration is None or self.duration <= 0:
            raise ValueError(
                "Duration must be a positive integer for HealingOverTimeEffect."
            )
        return self

    @model_validator(mode="after")
    def check_heal_per_turn(self) -> Any:
        if not isinstance(self.heal_per_turn, str):
            raise ValueError("Heal per turn must be a string expression.")
        return self

    def turn_update(self, effect: ActiveEffect) -> None:
        """
        Update the healing over time effect for the current turn.

        Args:
            effect (ActiveEffect):
                The active effect instance containing actor, target, and
                variables.

        """
        # Calculate the heal amount using the provided expression.
        outcome = roll_and_describe(
            self.heal_per_turn,
            effect.variables,
        )
        # Assert that the heal value is a positive integer.
        if outcome.value < 0:
            raise ValueError(
                "Heal value must be non-negative for HealingOverTimeEffect"
                f" '{self.name}', got {outcome.value}."
            )
        # Apply the heal to the target.
        hot_value = effect.target.heal(outcome.value)
        # If the heal value is positive, print the heal message.
        message = f"    {self.emoji} "
        message += effect.target.char_type.colorize(effect.target.name)
        message += f" heals for {hot_value} ([white]{outcome.description}[/]) hp from "
        message += self.colorize(self.name) + "."
        cprint(message)
