from typing import Any

from .base_effect import Effect


class IncapacitatingEffect(Effect):
    """
    Effect that prevents a character from taking actions.

    Unlike ModifierEffect which only applies stat penalties, IncapacitatingEffect
    completely prevents the character from acting during their turn.
    """

    def __init__(
        self,
        name: str,
        description: str,
        duration: int | None,
        incapacitation_type: str = "general",  # "sleep", "paralyzed", "stunned", etc.
        save_ends: bool = False,
        save_dc: int = 0,
        save_stat: str = "CON",
        damage_threshold: int = 1,  # Minimum damage needed to break effect (if applicable)
    ):
        super().__init__(name, description, duration)
        self.incapacitation_type = incapacitation_type
        self.save_ends = save_ends
        self.save_dc = save_dc
        self.save_stat = save_stat
        self.damage_threshold = damage_threshold

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
