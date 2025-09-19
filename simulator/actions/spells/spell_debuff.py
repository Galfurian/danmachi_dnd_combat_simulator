"""Detrimental spell debuff implementation."""

from typing import Any

from combat.damage import DamageComponent
from core.constants import GLOBAL_VERBOSE_LEVEL, ActionCategory, BonusType
from core.utils import cprint, substitute_variables
from pydantic import model_validator

from actions.spells.base_spell import Spell


class SpellDebuff(Spell):
    """Detrimental spell that weakens enemies with negative effects.

    This class represents spells designed to apply debuffs or negative effects
    to enemies. It includes attributes for required effects and methods for
    applying those effects during combat.
    """

    category: ActionCategory = ActionCategory.DEBUFF

    @model_validator(mode="after")
    def validate_fields(self) -> "SpellDebuff":
        """Validates fields after model initialization."""
        from effects.modifier_effect import ModifierEffect
        from effects.incapacitating_effect import IncapacitatingEffect

        if not isinstance(self.effect, ModifierEffect | IncapacitatingEffect):
            print(self.effect)
            print(type(self.effect))
            raise ValueError(
                "effect must be a valid ModifierEffect or IncapacitatingEffect instance"
            )
        return self

    # ============================================================================
    # DEBUFF SPELL METHODS
    # ============================================================================

    def cast_spell(self, actor: Any, target: Any, mind_level: int) -> bool:
        """Execute a debuff spell with automatic application and optional saves.

        Args:
            actor (Any): The character casting the spell.
            target (Any): The character targeted by the spell.
            mind_level (int): The spell level to cast at (affects cost and power).

        Returns:
            bool: True if spell was cast successfully, False on failure.

        """
        from character.main import Character
        from effects.modifier_effect import ModifierEffect
        from effects.incapacitating_effect import IncapacitatingEffect

        # Validate effect.
        assert isinstance(self.effect, ModifierEffect | IncapacitatingEffect)
        assert isinstance(actor, Character), "Actor must be an object"
        assert isinstance(target, Character), "Target must be an object"

        # Call the base class cast_spell to handle common checks.
        if super().cast_spell(actor, target, mind_level) is False:
            return False

        # Handle concentration requirements
        if self.requires_concentration:
            actor.concentration_module.break_concentration()

        # Apply the detrimental effect
        effect_applied = self._common_apply_effect(
            actor,
            target,
            self.effect,
            mind_level,
        )

        # Display the outcome.
        msg = f"    🔮 {actor.colored_name} "
        msg += f"casts [bold blue]{self.name}[/] "
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
