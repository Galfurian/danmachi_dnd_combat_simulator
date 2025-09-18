"""Buff abilities that provide beneficial effects to allies."""

from typing import Any

from actions.abilities.base_ability import BaseAbility
from core.constants import (
    ActionCategory,
    ActionType,
    GLOBAL_VERBOSE_LEVEL,
)
from core.utils import cprint
from effects.base_effect import Effect
from effects.modifier_effect import BuffEffect
from pydantic import Field


class AbilityBuff(BaseAbility):
    """
    Represents a buff ability that provides beneficial effects to targets in combat.
    Inherits from BaseAbility and applies an Effect to allies or self.
    """

    category: ActionCategory = ActionCategory.BUFF

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
        if not self._validate_character(actor):
            return False
        if not self._validate_character(target):
            return False
        # Validate effect.
        if not self.effect or not isinstance(self.effect, BuffEffect):
            print(
                f"{self.name} has invalid effect type: {type(self.effect).__name__}",
                {"name": self.name, "effect_type": type(self.effect).__name__},
            )
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

        # Apply the buff effect
        effect_applied = self._common_apply_effect(actor, target, self.effect)

        # Display results.
        effect_color = self.effect.color

        msg = f"    ✨ {actor_str} uses [bold blue]{self.name}[/] on {target_str}"

        if GLOBAL_VERBOSE_LEVEL == 0:
            if effect_applied:
                msg += f" granting [{effect_color}]{self.effect.name}[/]"
            else:
                msg += f" but fails to apply [{effect_color}]{self.effect.name}[/]"
            msg += "."
        elif GLOBAL_VERBOSE_LEVEL >= 1:
            if effect_applied:
                msg += f" successfully granting [{effect_color}]{self.effect.name}[/]"
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
