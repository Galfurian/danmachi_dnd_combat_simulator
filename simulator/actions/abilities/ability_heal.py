"""Healing abilities that restore hit points to allies."""

from typing import Any

from core.constants import GLOBAL_VERBOSE_LEVEL, ActionCategory
from core.utils import (
    cprint,
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    roll_and_describe,
    substitute_variables,
)
from pydantic import Field

from actions.abilities.base_ability import BaseAbility


class AbilityHeal(BaseAbility):
    """Represents abilities that restore hit points to targets during combat."""

    category: ActionCategory = ActionCategory.HEALING

    # Validate the heal_roll expression.
    heal_roll: str = Field(
        description="Expression for healing amount, e.g. '1d8 + 3'",
    )

    def execute(self, actor: Any, target: Any) -> bool:
        """Execute this healing ability on a target.

        Args:
            actor (Any): The character using the ability.
            target (Any): The character being healed.

        Returns:
            bool: True if ability was executed successfully, False on system errors.

        """
        # Validate actor and target.
        if not self._validate_character(actor):
            return False
        if not self._validate_character(target):
            return False
        # Validate cooldown.
        if actor.is_on_cooldown(self):
            print(
                f"{actor.name} cannot use {self.name} yet, still on cooldown.",
                {"actor": actor.name, "ability": self.name},
            )
            return False

        # Get display strings for logging.
        actor_str, target_str = self._get_display_strings(actor, target)

        # Roll healing amount
        variables = actor.get_expression_variables()
        healing_amount, healing_desc, _ = roll_and_describe(self.heal_roll, variables)

        # Apply healing to target.
        actual_healing = target.heal(healing_amount)

        # Apply effects
        effect_applied = self._common_apply_effect(actor, target, self.effect)

        # Display results.
        msg = f"    💚 {actor_str} uses [bold green]{self.name}[/] on {target_str}"

        if GLOBAL_VERBOSE_LEVEL == 0:
            msg += f" healing {actual_healing} HP"
            if self.effect and effect_applied:
                msg += f" and applying [bold yellow]{self.effect.name}[/]"
            msg += "."
        elif GLOBAL_VERBOSE_LEVEL >= 1:
            if actual_healing != healing_amount:
                msg += f" healing {actual_healing} HP (rolled {healing_amount}, capped at max HP)"
            else:
                msg += f" healing {actual_healing} HP → {healing_desc}"
            msg += ".\n"

            if self.effect:
                if effect_applied:
                    msg += f"        {target_str} is affected by"
                else:
                    msg += f"        {target_str} resists"
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
