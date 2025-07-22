"""
Buff abilities that provide beneficial effects to allies.

This module contains the BuffAbility class for beneficial special abilities
like Bardic Inspiration, Guidance, and other enhancement powers.
"""

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
from effects.effect import Effect


class BuffAbility(BaseAbility):
    """
    Buff abilities that provide beneficial effects to targets.

    BuffAbility represents beneficial special powers like Bardic Inspiration,
    Guidance, Bless, and other enhancement abilities. These abilities apply
    positive effects to allies without dealing damage.
    """

    def __init__(
        self,
        name: str,
        type: ActionType,
        description: str,
        cooldown: int,
        maximum_uses: int,
        effect: Effect,  # Required for buff abilities
        target_expr: str = "",
        target_restrictions: list[str] | None = None,
    ):
        """
        Initialize a new BuffAbility.

        Args:
            name: Display name of the ability
            type: Action type (STANDARD, BONUS, REACTION, etc.)
            description: Flavor text describing what the ability does
            cooldown: Turns to wait before reusing (0 = no cooldown)
            maximum_uses: Max uses per encounter/day (-1 = unlimited)
            effect: Effect to apply to targets (required for buff abilities)
            target_expr: Expression determining number of targets ("" = single target)
            target_restrictions: Override default targeting if needed

        Raises:
            ValueError: If name is empty, effect is None, or other parameters are invalid
        """
        try:
            # Validate that effect is provided
            if effect is None:
                raise ValueError(f"BuffAbility {name} requires an effect parameter")

            super().__init__(
                name,
                type,
                ActionCategory.BUFF,
                description,
                cooldown,
                maximum_uses,
                effect,
                target_expr,
                target_restrictions,
            )

        except Exception as e:
            log_critical(
                f"Error initializing BuffAbility {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

    def execute(self, actor: Any, target: Any) -> bool:
        """
        Execute this buff ability on a target.

        This method handles the complete buff ability activation sequence
        focusing on effect application since buffs don't deal damage.

        Args:
            actor: The character using the ability (must have combat methods)
            target: The character being buffed (must have combat methods)

        Returns:
            bool: True if ability was executed successfully, False on system errors
        """
        actor_str, target_str = self._get_display_strings(actor, target)

        # Check cooldown and uses
        assert not actor.is_on_cooldown(self), f"Action {self.name} is on cooldown."

        # Apply the buff effect
        effect_applied = self._apply_common_effects(actor, target)

        # Display results
        self._display_execution_result(actor_str, target_str, effect_applied)

        return True

    def _display_execution_result(
        self,
        actor_str: str,
        target_str: str,
        effect_applied: bool,
    ) -> None:
        """
        Display the results of the buff ability execution.

        Args:
            actor_str: Formatted actor name string
            target_str: Formatted target name string
            effect_applied: Whether effect was successfully applied
        """
        # Effect is guaranteed to exist for BuffAbility
        assert self.effect is not None, "BuffAbility must have an effect"
        effect_color = get_effect_color(self.effect)

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

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def get_effect_description(self) -> str:
        """
        Get a description of the effect this ability provides.

        Returns:
            str: Description of the buff effect
        """
        if self.effect and hasattr(self.effect, "description"):
            return self.effect.description
        return f"Applies {self.effect.name}" if self.effect else "No effect"
