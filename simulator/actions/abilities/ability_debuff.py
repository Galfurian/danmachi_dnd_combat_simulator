"""Buff abilities that provide beneficial effects to allies."""

from typing import Any

from core.constants import GLOBAL_VERBOSE_LEVEL, ActionCategory
from core.utils import cprint
from pydantic import model_validator

from actions.abilities.base_ability import BaseAbility


class AbilityDebuff(BaseAbility):
    """
    Represents a debuff ability that provides detrimental effects to targets in combat.
    Inherits from BaseAbility and applies an Effect to enemies.
    """

    category: ActionCategory = ActionCategory.DEBUFF

    @model_validator(mode="after")
    def validate_fields(self) -> "AbilityDebuff":
        """Ensure that the effect field is properly set."""
        from effects.base_effect import Effect

        if not isinstance(self.effect, Effect):
            raise ValueError("AbilityDebuff must have a valid effect assigned.")
        return self

    def execute(self, actor: Any, target: Any) -> bool:
        """
        Execute this debuff ability on a target in combat.

        Args:
            actor (Any): The character using the ability.
            target (Any): The character being debuffed.

        Returns:
            bool: True if ability was executed successfully, False on system errors.

        """
        from character.main import Character
        from effects.modifier_effect import ModifierEffect
        from effects.incapacitating_effect import IncapacitatingEffect

        # Validate effect.
        assert isinstance(self.effect, ModifierEffect | IncapacitatingEffect)
        assert isinstance(actor, Character), "Actor must be an object"
        assert isinstance(target, Character), "Target must be an object"

        # Validate cooldown.
        if actor.is_on_cooldown(self):
            print(
                f"{actor.name} cannot use {self.name} yet, still on cooldown.",
                {"actor": actor.name, "ability": self.name},
            )
            return False

        # Apply the buff effect
        effect_applied = self._common_apply_effect(actor, target, self.effect)

        # Display the outcome.
        msg = f"    ✨ {actor.colored_name} "
        msg += f"uses [bold blue]{self.name}[/] "
        msg += f"on {target.colored_name}"
        if effect_applied:
            msg += f" applying {self.effect.colored_name}"
        else:
            msg += f" but fails to apply {self.effect.colored_name}"
        msg += "."
        if GLOBAL_VERBOSE_LEVEL >= 1:
            if effect_applied:
                msg += f"\n        Effect: {self.effect.description}"
        cprint(msg)

        return True

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def get_effect_description(self) -> str:
        """
        Get a description of the effect this ability provides.

        Returns:
            str: Description of the buff effect.

        """
        if self.effect and hasattr(self.effect, "description"):
            return self.effect.description
        return f"Applies {self.effect.name}" if self.effect else "No effect"
