"""
Ability heal module for the simulator.

Defines healing abilities that restore hit points to allies, including
various healing spells and abilities with different effects and ranges.
"""

from typing import Any, Literal

from actions.abilities.base_ability import BaseAbility
from core.constants import GLOBAL_VERBOSE_LEVEL, ActionCategory
from core.dice_parser import (
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    roll_and_describe,
    substitute_variables,
)
from core.utils import cprint
from pydantic import Field


class AbilityHeal(BaseAbility):
    """Represents abilities that restore hit points to targets during combat."""

    action_type: Literal["AbilityHeal"] = "AbilityHeal"

    category: ActionCategory = ActionCategory.HEALING

    heal_roll: str = Field(
        description="Expression for healing amount, e.g. '1d8 + 3'",
    )

    def model_post_init(self, _) -> None:
        """Validates fields after model initialization."""
        if not self.heal_roll or not isinstance(self.heal_roll, str):
            raise ValueError("heal_roll must be a non-empty string.")
        # Remove spaces before and after '+' and '-'.
        self.heal_roll = self.heal_roll.replace(" +", "+").replace("+ ", "+")
        self.heal_roll = self.heal_roll.replace(" -", "-").replace("- ", "-")

    def execute(self, actor: Any, target: Any) -> bool:
        """Execute this healing ability on a target.

        Args:
            actor (Any): The character using the ability.
            target (Any): The character being healed.

        Returns:
            bool: True if ability was executed successfully, False on system errors.

        """
        from character.main import Character

        if not isinstance(actor, Character):
            raise ValueError("The actor must be a Character instance.")
        if not isinstance(target, Character):
            raise ValueError("The target must be a Character instance.")

        # Check if the ability is on cooldown.
        if actor.is_on_cooldown(self):
            return False

        # Get expression variables from actor.
        variables = actor.get_expression_variables()
        # Roll healing amount.
        heal = roll_and_describe(self.heal_roll, variables)
        # Apply healing to target.
        actual_healing = target.heal(heal.value)
        # Apply the effects.
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
            msg += f" healing {actual_healing} 💚"
            if effects_applied:
                msg += f" applying {self._effect_list_string(effects_applied)}"
            if effects_not_applied:
                msg += f" but fails to apply {self._effect_list_string(effects_not_applied)}"
            msg += "."
        elif GLOBAL_VERBOSE_LEVEL >= 1:
            if actual_healing != heal.value:
                msg += f" healing {actual_healing} 💚 (rolled {heal.value}, capped at max 💚)"
            else:
                msg += f" healing {actual_healing} 💚 → {heal.description}"
            msg += ".\n"

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

    # ============================================================================
    # HEALING CALCULATION METHODS
    # ============================================================================

    def get_heal_expr(self, actor: Any) -> str:
        """Returns the healing expression with variables substituted.

        Args:
            actor (Any): The character using the ability.

        Returns:
            str: Complete healing expression with variables replaced by values.

        """
        variables = actor.get_expression_variables()
        return substitute_variables(self.heal_roll, variables)

    def get_min_heal(self, actor: Any) -> int:
        """Returns the minimum possible healing value for the ability.

        Args:
            actor (Any): The character using the ability.

        Returns:
            int: Minimum healing amount.

        """
        variables = actor.get_expression_variables()
        substituted = substitute_variables(self.heal_roll, variables)
        return parse_expr_and_assume_min_roll(substituted)

    def get_max_heal(self, actor: Any) -> int:
        """Returns the maximum possible healing value for the ability.

        Args:
            actor (Any): The character using the ability.

        Returns:
            int: Maximum healing amount.

        """
        variables = actor.get_expression_variables()
        substituted = substitute_variables(self.heal_roll, variables)
        return parse_expr_and_assume_max_roll(substituted)
