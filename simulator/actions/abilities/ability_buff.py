"""
Ability buff module for the simulator.

Defines buff abilities that provide beneficial effects to allies, such as
stat bonuses, damage resistance, or other positive enhancements.
"""

from typing import TYPE_CHECKING, Any, Literal

from actions.abilities.base_ability import BaseAbility
from core.constants import GLOBAL_VERBOSE_LEVEL, ActionCategory
from core.dice_parser import VarInfo
from core.utils import cprint

if TYPE_CHECKING:
    from character.main import Character


class AbilityBuff(BaseAbility):
    """
    Represents a buff ability that provides beneficial effects to targets in combat.
    Inherits from BaseAbility and applies an Effect to allies or self.
    """

    action_type: Literal["AbilityBuff"] = "AbilityBuff"

    category: ActionCategory = ActionCategory.BUFF

    def model_post_init(self, _: Any) -> None:
        """Ensure that the effect field is properly set."""
        from effects.base_effect import Effect

        if not self.effects:
            raise ValueError("AbilityBuff must have an effect defined.")

        if not all(isinstance(effect, Effect) for effect in self.effects):
            raise ValueError("All effects must be Effect instances.")

    def _execute_ability(
        self,
        actor: "Character",
        target: "Character",
        variables: list[VarInfo],
    ) -> bool:
        """
        Abstract method to be implemented by subclasses for specific ability execution.

        Args:
            actor (Character):
                The character performing the action.
            target (Character):
                The character being targeted.
            variables (list[VarInfo]):
                The variables available for the action execution.

        Returns:
            bool:
                True if action executed successfully, False otherwise.
        """
        # Apply the buff effect.
        effects_applied, effects_not_applied = self._common_apply_effects(
            actor=actor,
            target=target,
            effects=self.effects,
            variables=variables,
        )

        # Display the outcome.
        msg = f"    ✨ {actor.colored_name} "
        msg += f"uses {self.colored_name} "
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
