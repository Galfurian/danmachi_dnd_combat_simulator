"""Buff abilities that provide beneficial effects to allies."""

from typing import Any, Literal

from actions.abilities.base_ability import BaseAbility
from core.constants import GLOBAL_VERBOSE_LEVEL, ActionCategory
from core.utils import cprint


class AbilityDebuff(BaseAbility):
    """
    Represents a debuff ability that provides detrimental effects to targets in combat.
    Inherits from BaseAbility and applies an Effect to enemies.
    """

    action_type: Literal["AbilityDebuff"] = "AbilityDebuff"

    category: ActionCategory = ActionCategory.DEBUFF

    def model_post_init(self, _) -> None:
        """Ensure that the effect field is properly set."""
        from effects.base_effect import Effect

        if not self.effects:
            raise ValueError("AbilityDebuff must have an effect defined.")

        if not all(isinstance(effect, Effect) for effect in self.effects):
            raise ValueError("All effects must be Effect instances.")

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

        if not self.effects:
            raise ValueError("The effect field must be set.")
        if not isinstance(actor, Character):
            raise ValueError("The actor must be a Character instance.")
        if not isinstance(target, Character):
            raise ValueError("The target must be a Character instance.")

        # Check if the ability is on cooldown.
        if actor.is_on_cooldown(self):
            return False

        # Apply the buff effect.
        effects_applied, effects_not_applied = self._common_apply_effects(
            actor,
            target,
            self.effects,
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
