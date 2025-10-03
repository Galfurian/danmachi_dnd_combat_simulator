"""
Spell debuff module for the simulator.

Defines debuff spells that apply negative effects to targets, such as
stat reductions, curses, or other detrimental magical effects.
"""

from typing import TYPE_CHECKING, Any, Literal

from actions.spells.base_spell import BaseSpell
from core.constants import GLOBAL_VERBOSE_LEVEL, ActionCategory
from core.utils import cprint

if TYPE_CHECKING:
    from character.main import Character

class SpellDebuff(BaseSpell):
    """Detrimental spell that weakens enemies with negative effects.

    This class represents spells designed to apply debuffs or negative effects
    to enemies. It includes attributes for required effects and methods for
    applying those effects during combat.
    """

    action_type: Literal["SpellDebuff"] = "SpellDebuff"

    category: ActionCategory = ActionCategory.DEBUFF

    def model_post_init(self, _: Any) -> None:
        """Validates fields after model initialization."""
        from effects.incapacitating_effect import IncapacitatingEffect
        from effects.modifier_effect import ModifierEffect

        if not self.effects:
            raise ValueError("SpellDebuff must have at least one effect.")

        for effect in self.effects:
            if not isinstance(effect, ModifierEffect | IncapacitatingEffect):
                print(effect)
                print(type(effect))
                raise ValueError(
                    "All effects must be ModifierEffect or IncapacitatingEffect instances"
                )

    # ============================================================================
    # DEBUFF SPELL METHODS
    # ============================================================================

    def execute_spell(
        self,
        actor: "Character",
        target: "Character",
        rank: int,
    ) -> bool:
        """
        Execute the buff spell from actor to target.

        Args:
            actor (Any):
                The character casting the spell.
            target (Any):
                The character being targeted.
            rank (int):
                The rank at which the spell is being cast.

        Returns:
            bool:
                True if action executed successfully, False otherwise.

        """
        # Apply the buffs.
        effects_applied, effects_not_applied = self._spell_apply_effects(
            actor=actor,
            target=target,
            effects=self.effects,
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
                msg += f"        {target.colored_name} is affected by "
                msg += self._effect_list_string(effects_applied)
                msg += ".\n"
            if effects_not_applied:
                msg += f"        {target.colored_name} resists "
                msg += self._effect_list_string(effects_not_applied)
                msg += ".\n"
        cprint(msg)

        return True
