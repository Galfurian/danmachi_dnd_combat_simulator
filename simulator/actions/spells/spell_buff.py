"""Beneficial spell buff implementation."""

from typing import Any, Literal

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

    action_type: Literal["SpellBuff"] = "SpellBuff"

    category: ActionCategory = ActionCategory.BUFF

    def model_post_init(self, _) -> None:
        """Ensure that the effects field is properly set."""
        from effects.modifier_effect import ModifierEffect
        from effects.trigger_effect import TriggerEffect

        if not self.effects:
            raise ValueError("SpellBuff must have at least one effect.")

        for effect in self.effects:
            if not isinstance(effect, ModifierEffect | TriggerEffect):
                print(effect)
                print(type(effect))
                raise ValueError(
                    f"SpellBuff effects must be ModifierEffect or TriggerEffect instances."
                )

    # ============================================================================
    # BUFF SPELL METHODS
    # ============================================================================

    def cast_spell(
        self,
        actor: Any,
        target: Any,
        rank: int,
    ) -> bool:
        """
        Execute a buff spell with automatic success and beneficial effects.

        Args:
            actor (Any):
                The character casting the spell.
            target (Any):
                The character targeted by the spell.
            rank (int):
                The rank or level of the spell being cast.

        Returns:
            bool:
                True if spell was cast successfully, False on failure.

        """
        # Call the base class cast_spell to handle common checks.
        if not super().cast_spell(actor, target, rank):
            return False
        # Validate that the effects are set.
        if not self.effects:
            raise ValueError("The effects field must be set.")

        # Apply the buffs.
        effects_applied, effects_not_applied = self._spell_apply_effects(
            actor=actor,
            target=target,
            rank=rank,
        )

        # Display the outcome.
        msg = f"    🔮 {actor.colored_name} "
        msg += f"casts [bold blue]{self.name}[/] "
        msg += f"on {target.colored_name}"
        if GLOBAL_VERBOSE_LEVEL == 0:
            if effects_applied:
                msg += f" applying {self._effect_list_string(effects_applied)}"
            if effects_not_applied:
                msg += f" but fails to apply {self._effect_list_string(effects_not_applied)}"
            msg += "."
        if GLOBAL_VERBOSE_LEVEL >= 1:
            msg += "."
            if effects_applied or effects_not_applied:
                msg += "\n"
            if effects_applied:
                msg += f"        {target.colored_name} gains "
                msg += self._effect_list_string(effects_applied)
                msg += ".\n"
            if effects_not_applied:
                msg += f"        {target.colored_name} doesn't gain "
                msg += self._effect_list_string(effects_not_applied)
                msg += ".\n"
        cprint(msg)

        return True
