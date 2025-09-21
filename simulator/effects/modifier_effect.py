from typing import Any, Literal

from catchery import log_warning
from pydantic import Field, model_validator

from .base_effect import ActiveEffect, Effect, Modifier


class ModifierEffect(Effect):
    """
    Base class for effects that apply stat modifiers to characters.

    This includes buffs and debuffs that temporarily modify character attributes
    like HP, AC, damage bonuses, etc.
    """

    effect_type: Literal["ModifierEffect"] = "ModifierEffect"

    modifiers: list[Modifier] = Field(
        description="List of modifiers applied by this effect.",
    )

    @property
    def color(self) -> str:
        """Returns the color string for modifier effects."""
        return "bold yellow"

    @property
    def emoji(self) -> str:
        """Returns the emoji for modifier effects."""
        return "🛡️"

    @model_validator(mode="after")
    def check_modifiers(self) -> "ModifierEffect":
        """
        Ensure that the modifiers list is not empty.

        Raises:
            ValueError: If the modifiers list is empty.

        """
        if not self.modifiers:
            raise ValueError("Modifiers list cannot be empty.")
        for modifier in self.modifiers:
            if not isinstance(modifier, Modifier):
                raise ValueError(f"Invalid modifier: {modifier}")
        return self

    def can_apply(self, actor: Any, target: Any) -> bool:
        """
        Check if the modifier effect can be applied to the target.

        Args:
            actor (Any): The character applying the effect.
            target (Any): The character receiving the effect.

        Returns:
            bool: True if the effect can be applied, False otherwise.

        """
        from character.main import Character

        # Validate actor and target types.
        if not isinstance(actor, Character):
            log_warning(
                "ModifierEffect.can_apply called without valid actor.",
                {"effect": self.name, "actor": actor},
            )
            return False
        if not isinstance(target, Character):
            log_warning(
                "ModifierEffect.can_apply called without valid target.",
                {"effect": self.name, "target": target},
            )
            return False
        # If the target is dead, cannot apply effects.
        if not target.is_alive():
            return False
        # Check if the target is already affected by the same modifiers.
        return target.can_add_effect(
            actor,
            self,
            actor.get_expression_variables(),
        )

    def turn_update(
        self,
        effect: ActiveEffect,
    ) -> None:
        """
        Update the effect at the start of the target's turn.
        """
        pass
