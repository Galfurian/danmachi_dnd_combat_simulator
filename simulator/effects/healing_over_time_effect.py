"""
Healing over time effect module for the simulator.

Defines effects that provide healing over multiple turns, such as
regeneration or restorative spells with ongoing benefits.
"""

from typing import Literal

from core.dice_parser import roll_and_describe
from core.utils import cprint
from pydantic import Field

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

    def model_post_init(self, _) -> None:
        if self.duration is None or self.duration <= 0:
            raise ValueError(
                "Duration must be a positive integer for HealingOverTimeEffect."
            )
        if not isinstance(self.heal_per_turn, str):
            raise ValueError("Heal per turn must be a string expression.")


class ActiveHealingOverTimeEffect(ActiveEffect):
    """
    Active Healing over Time effect that heals the target each turn.
    """

    @property
    def healing_over_time_effect(self) -> HealingOverTimeEffect:
        """
        Get the effect as a HealingOverTimeEffect (narrowed type for clarity).

        Raises:
            TypeError:
                If the effect is not a HealingOverTimeEffect.

        Returns:
            HealingOverTimeEffect:
                The effect cast as a HealingOverTimeEffect.

        """
        if not isinstance(self.effect, HealingOverTimeEffect):
            raise ValueError("Effect must be a HealingOverTimeEffect instance.")
        return self.effect

    def turn_update(self) -> None:
        """
        Apply healing to the target at the start of their turn.
        """
        HOT = self.healing_over_time_effect

        # Calculate the heal amount using the provided expression.
        outcome = roll_and_describe(
            HOT.heal_per_turn,
            self.variables,
        )
        # Assert that the heal value is a positive integer.
        if outcome.value < 0:
            raise ValueError(
                "Heal value must be non-negative for HealingOverTimeEffect"
                f" '{HOT.name}', got {outcome.value}."
            )
        # Apply the heal to the target.
        hot_value = self.target.heal(outcome.value)
        # If the heal value is positive, print the heal message.
        message = f"    {HOT.emoji} "
        message += self.target.char_type.colorize(self.target.name)
        message += f" heals for {hot_value} ([white]{outcome.description}[/]) hp from "
        message += HOT.colored_name + "."
        cprint(message)
