"""Buff abilities that provide beneficial effects to allies."""

from typing import Any

from actions.abilities.base_ability import BaseAbility
from core.constants import (
    ActionCategory,
    ActionType,
    GLOBAL_VERBOSE_LEVEL,
    get_effect_color,
)
from core.error_handling import log_critical
from core.utils import cprint
from effects.base_effect import Effect
from effects.modifier_effect import DebuffEffect


class DebuffAbility(BaseAbility):
    """
    Represents a buff ability that provides beneficial effects to targets in combat.
    Inherits from BaseAbility and applies an Effect to allies or self.
    """

    def __init__(
        self,
        name: str,
        action_type: ActionType,
        description: str,
        cooldown: int,
        maximum_uses: int,
        effect: Effect,
        target_expr: str = "",
        target_restrictions: list[str] | None = None,
    ) -> None:
        """
        Initialize a new DebuffAbility for combat.

        Args:
            name (str): Display name of the ability.
            action_type (ActionType): Action type (STANDARD, BONUS, REACTION, etc.).
            description (str): Flavor text describing what the ability does.
            cooldown (int): Turns to wait before reusing (0 = no cooldown).
            maximum_uses (int): Max uses per encounter/day (-1 = unlimited).
            effect (Effect): Effect to apply to targets (required for buff abilities).
            target_expr (str, optional): Expression determining number of targets ("" = single target). Defaults to "".
            target_restrictions (list[str] | None, optional): Override default targeting if needed. Defaults to None.

        Raises:
            ValueError: If name is empty, effect is None, or other parameters are invalid.
        """
        try:
            super().__init__(
                name,
                action_type,
                ActionCategory.BUFF,
                description,
                cooldown,
                maximum_uses,
                effect,
                target_expr,
                target_restrictions,
            )

            # Make sure effect is valid.
            if not isinstance(effect, DebuffEffect):
                log_critical(
                    f"DebuffAbility {name} effect must be a DebuffEffect instance, got: {type(effect).__name__}",
                    {"name": name, "effect_type": type(effect).__name__},
                )
                raise ValueError(
                    f"DebuffAbility {name} effect must be a DebuffEffect instance"
                )

        except Exception as e:
            log_critical(
                f"Error initializing DebuffAbility {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

    def execute(self, actor: Any, target: Any) -> bool:
        """
        Execute this buff ability on a target in combat.

        Args:
            actor (Any): The character using the ability.
            target (Any): The character being buffed.

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

        # Check the effect is valid.
        if not isinstance(self.effect, Effect):
            log_critical(
                f"DebuffAbility {self.name} has invalid effect type: {type(self.effect).__name__}",
                {"name": self.name, "effect_type": type(self.effect).__name__},
            )
            return False

        # Apply the buff effect
        effect_applied = self._common_apply_effect(actor, target, self.effect)

        # Display results
        effect_color = get_effect_color(self.effect)

        msg = f"    ✨ {actor_str} uses [bold blue]{self.name}[/] on {target_str}"

        if GLOBAL_VERBOSE_LEVEL == 0:
            if effect_applied:
                msg += f" applying [{effect_color}]{self.effect.name}[/]"
            else:
                msg += f" but fails to apply [{effect_color}]{self.effect.name}[/]"
            msg += "."
        elif GLOBAL_VERBOSE_LEVEL >= 1:
            if effect_applied:
                msg += f" successfully applying [{effect_color}]{self.effect.name}[/]"
            else:
                msg += (
                    f" but {target_str} resists [{effect_color}]{self.effect.name}[/]"
                )
            msg += ".\n"

            if effect_applied and hasattr(self.effect, "description"):
                msg += f"        Effect: {self.effect.description}"

        cprint(msg)

        return True

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def get_effect_description(self) -> str:
        """
        Get a description of the effect this ability provides.

        Returns:
            str: Description of the buff effect.
        """
        if self.effect and hasattr(self.effect, "description"):
            return self.effect.description
        return f"Applies {self.effect.name}" if self.effect else "No effect"
