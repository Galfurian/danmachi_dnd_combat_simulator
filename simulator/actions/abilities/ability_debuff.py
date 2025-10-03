"""
Ability debuff module for the simulator.

Defines debuff abilities that apply negative effects to targets, such as
stat reductions, status conditions, or other detrimental effects.
"""

from typing import TYPE_CHECKING, Any, Literal

from actions.abilities.base_ability import BaseAbility
from core.constants import GLOBAL_VERBOSE_LEVEL, ActionCategory
from core.dice_parser import VarInfo
from core.utils import cprint

if TYPE_CHECKING:
    from character.main import Character


class AbilityDebuff(BaseAbility):
    """
    Represents a debuff ability that provides detrimental effects to targets in combat.
    Inherits from BaseAbility and applies an Effect to enemies.
    """

    action_type: Literal["AbilityDebuff"] = "AbilityDebuff"

    category: ActionCategory = ActionCategory.DEBUFF

    def model_post_init(self, _: Any) -> None:
        """Ensure that the effect field is properly set."""
        from effects.base_effect import Effect

        if not self.effects:
            raise ValueError("AbilityDebuff must have an effect defined.")

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
                msg += f"        {target.colored_name} is affected by "
                msg += self._effect_list_string(effects_applied)
                msg += ".\n"
            if effects_not_applied:
                msg += f"        {target.colored_name} resists "
                msg += self._effect_list_string(effects_not_applied)
                msg += ".\n"
        cprint(msg)

        return True
