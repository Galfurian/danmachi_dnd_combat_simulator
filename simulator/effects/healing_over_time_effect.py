"""
Healing over time effect module for the simulator.

Defines effects that provide healing over multiple turns, such as
regeneration or restorative spells with ongoing benefits.
"""

from typing import Any, Literal

from core.dice_parser import VarInfo, roll_and_describe
from core.logging import log_debug
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

    def model_post_init(self, _: Any) -> None:
        if self.duration is None or self.duration <= 0:
            raise ValueError(
                "Duration must be a positive integer for HealingOverTimeEffect."
            )
        if not isinstance(self.heal_per_turn, str):
            raise ValueError("Heal per turn must be a string expression.")

    def can_apply(
        self,
        actor: Any,
        target: Any,
        variables: list[VarInfo],
    ) -> bool:
        """
        Check if the healing over time effect can be applied to the target.

        Rules for HoT application:
            1. Basic eligibility: Actor and target must be alive Characters
            2. Stacking limit: Target cannot have 3 or more active HoT effects

        Args:
            actor (Character):
                The character applying the effect.
            target (Character):
                The character receiving the effect.
            variables (list[VarInfo]):
                List of variable info for dynamic calculations.

        Returns:
            bool:
                True if the effect can be applied, False otherwise.

        """
        from character.main import Character

        # Rule 1: Basic validation from parent class
        if not super().can_apply(actor, target, variables):
            return False

        assert isinstance(actor, Character), "Actor must be a Character."
        assert isinstance(target, Character), "Target must be a Character."

        # Rule 2: Stacking limit - prevent applying if target has 3+ HoT effects
        if sum(1 for _ in target.effects.healing_over_time_effects) >= 3:
            log_debug(
                f"Cannot apply HoT effect: Target {target.colored_name} "
                "already has 3 or more active HoT effects."
            )
            return False

        return True


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
