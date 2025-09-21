from typing import Any, Literal

from pydantic import Field

from .base_effect import ActiveEffect, Effect


class IncapacitatingEffect(Effect):
    """
    Effect that prevents a character from taking actions.

    Unlike ModifierEffect which only applies stat penalties, IncapacitatingEffect
    completely prevents the character from acting during their turn.
    """

    effect_type: Literal["IncapacitatingEffect"] = "IncapacitatingEffect"

    incapacitation_type: str = Field(
        description="Type of incapacitation (e.g., 'sleep', 'paralyzed', 'stunned').",
    )
    save_ends: bool = Field(
        False,
        description="Whether the effect can end on a successful saving throw.",
    )
    save_dc: int = Field(
        0,
        description="DC for the saving throw to end the effect.",
    )
    save_stat: str = Field(
        "CON",
        description="Stat used for the saving throw (e.g., 'CON', 'WIS').",
    )
    damage_threshold: int = Field(
        1,
        description="Minimum damage needed to break effect (if applicable).",
    )

    @property
    def color(self) -> str:
        """Returns the color string for incapacitating effects."""
        return "bold red"

    @property
    def emoji(self) -> str:
        """Returns the emoji for incapacitating effects."""
        return "😵‍💫"

    def prevents_actions(self) -> bool:
        """
        Check if this effect prevents the character from taking actions.

        Returns:
            bool: True if actions are prevented, False otherwise.

        """
        return True

    def prevents_movement(self) -> bool:
        """
        Check if this effect prevents movement.

        Returns:
            bool: True if movement is prevented, False otherwise.

        """
        return self.incapacitation_type in ["paralyzed", "stunned", "unconscious"]

    def auto_fails_saves(self) -> bool:
        """
        Check if character automatically fails certain saves.

        Returns:
            bool: True if saves are automatically failed, False otherwise.

        """
        return self.incapacitation_type in ["unconscious"]

    def breaks_on_damage(self, damage_amount: int = 1) -> bool:
        """
        Check if taking damage should break this incapacitation.

        Args:
            damage_amount (int): Amount of damage taken.

        Returns:
            bool: True if damage breaks the effect, False otherwise.

        """
        # First check if this type of incapacitation can break on damage
        if self.incapacitation_type not in ["sleep", "charm"]:
            return False

        # Then check if damage meets the threshold
        return damage_amount >= self.damage_threshold

    def can_apply(self, actor: Any, target: Any) -> bool:
        """Incapacitating effects can be applied to any living target."""
        return target.is_alive()

    def turn_update(
        self,
        effect: ActiveEffect,
    ) -> None:
        """
        Update the effect at the start of the target's turn.

        Decrease the duration and remove the effect if it has expired.

        Args:
            effect (ActiveEffect): The active effect instance to update.

        """
        if not effect.duration:
            raise ValueError("Effect duration is not set.")
        if effect.duration <= 0:
            raise ValueError("Effect duration is already zero or negative.")
        effect.duration -= 1
