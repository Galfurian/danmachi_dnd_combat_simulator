"""Beneficial spell buff implementation."""

from typing import Any

from combat.damage import DamageComponent
from core.constants import GLOBAL_VERBOSE_LEVEL, ActionCategory, BonusType
from core.utils import cprint, substitute_variables
from pydantic import model_validator

from actions.spells.base_spell import Spell


class SpellBuff(Spell):
    """Beneficial spell that enhances targets with positive effects.

    This class represents spells designed to provide buffs or enhancements to
    allies. It includes attributes for required effects and methods for applying
    those effects during combat.
    """

    category: ActionCategory = ActionCategory.BUFF

    @model_validator(mode="after")
    def validate_fields(self) -> "SpellBuff":
        """Ensure that the effect field is properly set."""
        from effects.modifier_effect import ModifierEffect
        from effects.trigger_effect import TriggerEffect

        if not isinstance(self.effect, ModifierEffect | TriggerEffect):
            print(self.effect)
            print(type(self.effect))
            raise ValueError(
                f"SpellBuff must have a valid ModifierEffect or TriggerEffect assigned."
            )
        return self

    # ============================================================================
    # BUFF SPELL METHODS
    # ============================================================================

    def cast_spell(self, actor: Any, target: Any, mind_level: int) -> bool:
        """Execute a buff spell with automatic success and beneficial effects.

        Args:
            actor (Any): The character casting the spell.
            target (Any): The character targeted by the spell.
            mind_level (int): The spell level to cast at (affects cost and power).

        Returns:
            bool: True if spell was cast successfully, False on failure.

        """
        from character.main import Character
        from effects.modifier_effect import ModifierEffect
        from effects.trigger_effect import TriggerEffect

        # Validate effect.
        assert isinstance(
            self.effect, ModifierEffect | TriggerEffect
        ), "Effect must be a ModifierEffect or TriggerEffect"
        assert isinstance(actor, Character), "Actor must be an object"
        assert isinstance(target, Character), "Target must be an object"

        # Call the base class cast_spell to handle common checks.
        if super().cast_spell(actor, target, mind_level) is False:
            return False

        # Handle concentration requirements
        if self.requires_concentration:
            actor.concentration_module.break_concentration()

        # Apply the beneficial effect
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
            msg += f" granting {self.effect.colored_name}"
        else:
            msg += f" but fails to grant {self.effect.colored_name}"
        msg += "."
        if GLOBAL_VERBOSE_LEVEL >= 1:
            if effect_applied:
                msg += f"\n        Effect: {self.effect.description}"
        cprint(msg)

        return True
