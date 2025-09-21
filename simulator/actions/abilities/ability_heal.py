"""Healing abilities that restore hit points to allies."""

from typing import Any

from catchery import log_warning
from core.constants import GLOBAL_VERBOSE_LEVEL, ActionCategory
from core.utils import (
    cprint,
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    roll_and_describe,
    substitute_variables,
)
from pydantic import Field, model_validator

from actions.abilities.base_ability import BaseAbility


class AbilityHeal(BaseAbility):
    """Represents abilities that restore hit points to targets during combat."""

    category: ActionCategory = ActionCategory.HEALING

    heal_roll: str = Field(
        description="Expression for healing amount, e.g. '1d8 + 3'",
    )

    @model_validator(mode="after")
    def validate_fields(self) -> "AbilityHeal":
        """Validates fields after model initialization."""
        if not self.heal_roll or not isinstance(self.heal_roll, str):
            raise ValueError("heal_roll must be a non-empty string.")
        # Remove spaces before and after '+' and '-'.
        self.heal_roll = self.heal_roll.replace(" +", "+").replace("+ ", "+")
        self.heal_roll = self.heal_roll.replace(" -", "-").replace("- ", "-")
        return self

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
            log_warning(
                "AbilityBuff.execute called without valid actor.",
                {"ability": self.name, "actor": actor},
            )
            return False
        if not isinstance(target, Character):
            log_warning(
                "AbilityBuff.execute called without valid target.",
                {"ability": self.name, "target": target},
            )
            return False
        if actor.is_on_cooldown(self):
            log_warning(
                "AbilityBuff.execute called while actor is on cooldown.",
                {"ability": self.name, "actor": actor.name},
            )
            return False

        # Get expression variables from actor.
        variables = actor.get_expression_variables()
        # Roll healing amount.
        heal = roll_and_describe(self.heal_roll, variables)
        # Apply healing to target.
        actual_healing = target.heal(heal.value)
        # Apply effects
        effect_applied = self._common_apply_effect(actor, target, self.effect)

        # Display the outcome.
        msg = f"    💚 {actor.colored_name} uses [bold green]{self.name}[/] on {target.colored_name}"
        if GLOBAL_VERBOSE_LEVEL == 0:
            msg += f" healing {actual_healing} HP"
            if self.effect and effect_applied:
                msg += f" and applying [bold yellow]{self.effect.name}[/]"
            msg += "."
        elif GLOBAL_VERBOSE_LEVEL >= 1:
            if actual_healing != heal.value:
                msg += f" healing {actual_healing} HP (rolled {heal.value}, capped at max HP)"
            else:
                msg += f" healing {actual_healing} HP → {heal.description}"
            msg += ".\n"

            if self.effect:
                if effect_applied:
                    msg += f"        {target.colored_name} is affected by"
                else:
                    msg += f"        {target.colored_name} resists"
                msg += f" [bold yellow]{self.effect.name}[/]."

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
