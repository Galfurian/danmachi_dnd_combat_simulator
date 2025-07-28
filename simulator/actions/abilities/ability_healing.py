"""Healing abilities that restore hit points to allies."""

from typing import Any

from actions.abilities.base_ability import BaseAbility
from core.constants import ActionCategory, ActionType, GLOBAL_VERBOSE_LEVEL
from core.error_handling import (
    ensure_string,
    log_critical,
    log_error,
    validate_required_object,
)
from core.utils import (
    cprint,
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    roll_and_describe,
    substitute_variables,
)
from effects.base_effect import Effect


class HealingAbility(BaseAbility):
    """Represents abilities that restore hit points to targets during combat."""

    def __init__(
        self,
        name: str,
        action_type: ActionType,
        description: str,
        cooldown: int,
        maximum_uses: int,
        heal_roll: str,
        effect: Effect | None = None,
        target_expr: str = "",
        target_restrictions: list[str] | None = None,
    ):
        """Initialize a new HealingAbility.

        Args:
            name (str): Display name of the ability.
            action_type (ActionType): Action type (STANDARD, BONUS, REACTION, etc.).
            description (str): Flavor text describing what the ability does.
            cooldown (int): Turns to wait before reusing (0 = no cooldown).
            maximum_uses (int): Max uses per encounter/day (-1 = unlimited).
            heal_roll (str): Healing expression (e.g., "2d8 + WIS", "1d4 + LEVEL").
            effect (Effect | None): Optional effect applied to targets on use (like regeneration).
            target_expr (str): Expression determining number of targets ("" = single target).
            target_restrictions (list[str] | None): Override default targeting if needed.

        Raises:
            ValueError: If name is empty or required parameters are invalid.
        """
        try:
            super().__init__(
                name,
                action_type,
                ActionCategory.HEALING,
                description,
                cooldown,
                maximum_uses,
                effect,
                target_expr,
                target_restrictions,
            )

            # Validate heal_roll using helper
            self.heal_roll = ensure_string(heal_roll, "heal roll", "0", {"name": name})

        except Exception as e:
            log_critical(
                f"Error initializing HealingAbility {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

    def execute(self, actor: Any, target: Any) -> bool:
        """Execute this healing ability on a target.

        Args:
            actor (Any): The character using the ability.
            target (Any): The character being healed.

        Returns:
            bool: True if ability was executed successfully, False on system errors.
        """
        # Validate actor and target.
        if not self._validate_actor_and_target(actor, target):
            return False

        # Get display strings for logging.
        actor_str, target_str = self._get_display_strings(actor, target)

        # Check cooldown.
        if actor.is_on_cooldown(self):
            log_critical(
                f"{actor_str} cannot use {self.name} yet, still on cooldown.",
                {"actor": actor_str, "ability": self.name},
            )
            return False

        # Roll healing amount
        variables = actor.get_expression_variables()
        healing_amount, healing_desc, _ = roll_and_describe(self.heal_roll, variables)

        # Apply healing to target
        old_hp = target.hp
        target.heal(healing_amount)
        actual_healing = target.hp - old_hp

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
