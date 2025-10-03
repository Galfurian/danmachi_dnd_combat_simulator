"""
Spell buff module for the simulator.

Defines buff spells that provide beneficial effects to targets, such as
stat enhancements, protection, or other positive magical effects.
"""

from typing import TYPE_CHECKING, Any, Literal

from actions.spells.base_spell import BaseSpell
from core.constants import GLOBAL_VERBOSE_LEVEL, ActionCategory
from core.dice_parser import VarInfo
from core.utils import cprint

if TYPE_CHECKING:
    from character.main import Character


class SpellBuff(BaseSpell):
    """Beneficial spell that enhances targets with positive effects.

    This class represents spells designed to provide buffs or enhancements to
    allies. It includes attributes for required effects and methods for applying
    those effects during combat.
    """

    action_type: Literal["SpellBuff"] = "SpellBuff"

    category: ActionCategory = ActionCategory.BUFF

    def model_post_init(self, _: Any) -> None:
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
                    "SpellBuff effects must be ModifierEffect or TriggerEffect instances."
                )

    # ============================================================================
    # BUFF SPELL METHODS
    # ============================================================================

    def _execute_spell(
        self,
        actor: "Character",
        target: "Character",
        variables: list[VarInfo],
    ) -> bool:
        """
        Common logic for executing a spell after validation.

        Args:
            actor (Any):
                The character casting the spell.
            target (Any):
                The character being targeted.
            variables (list[VarInfo]):
                List of variables for expression evaluation.

        Returns:
            bool:
                True if action executed successfully, False otherwise.

        """
        # Apply the effects.
        effects_applied, effects_not_applied = self._common_apply_effects(
            actor=actor,
            target=target,
            effects=self.effects,
            variables=variables,
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
        else:
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
