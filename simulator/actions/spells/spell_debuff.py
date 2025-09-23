"""Detrimental spell debuff implementation."""

from typing import Any, Literal

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

    action_type: Literal["SpellDebuff"] = "SpellDebuff"

    category: ActionCategory = ActionCategory.DEBUFF

    @model_validator(mode="after")
    def validate_fields(self) -> "SpellDebuff":
        """Validates fields after model initialization."""
        from effects.modifier_effect import ModifierEffect
        from effects.incapacitating_effect import IncapacitatingEffect

        if not self.effects:
            raise ValueError("SpellDebuff must have at least one effect.")
        
        for effect in self.effects:
            if not isinstance(effect, ModifierEffect | IncapacitatingEffect):
                print(effect)
                print(type(effect))
                raise ValueError(
                    "All effects must be ModifierEffect or IncapacitatingEffect instances"
                )
        return self

    # ============================================================================
    # DEBUFF SPELL METHODS
    # ============================================================================

    def cast_spell(
        self,
        actor: Any,
        target: Any,
        rank: int,
    ) -> bool:
        """
        Cast the debuff spell from actor to target.

        Args:
            actor (Any):
                The entity casting the spell.
            target (Any):
                The entity receiving the spell.
            rank (int):
                The rank or level of the spell being cast.

        Returns:
            bool:
                True if the spell was successfully cast and the effect applied,
                False otherwise.

        """
        # Call the base class cast_spell to handle common checks.
        if not super().cast_spell(actor, target, rank):
            return False
        # Validate that the effects are set.
        if not self.effects:
            raise ValueError("The effects field must be set.")

        # Apply the detrimental effect
        effect_applied = self._spell_apply_effects(actor, target, rank)

        # Display the outcome.
        msg = f"    🔮 {actor.colored_name} "
        msg += f"casts [bold blue]{self.name}[/] "
        msg += f"on {target.colored_name}"
        if effect_applied:
            effect_names = [effect.colored_name for effect in self.effects]
            msg += f" applying {', '.join(effect_names)}"
        else:
            effect_names = [effect.colored_name for effect in self.effects]
            msg += f" but fails to apply {', '.join(effect_names)}"
        msg += "."
        if GLOBAL_VERBOSE_LEVEL >= 1 and effect_applied:
            for effect in self.effects:
                msg += f"\n        Effect: {effect.description}"
        cprint(msg)

        return True
