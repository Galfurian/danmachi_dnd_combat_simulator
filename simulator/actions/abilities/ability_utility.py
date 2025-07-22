"""
Utility abilities that provide non-combat benefits.

This module contains the UtilityAbility class for non-combat special abilities
like Detect Magic, Misty Step, and other utility powers.
"""

from typing import Any

from actions.abilities.base_ability import BaseAbility
from core.constants import ActionCategory, ActionType, GLOBAL_VERBOSE_LEVEL
from core.error_handling import log_critical
from core.utils import cprint
from effects.effect import Effect


class UtilityAbility(BaseAbility):
    """
    Utility abilities that provide non-combat benefits.

    UtilityAbility represents non-combat special powers like Detect Magic,
    Misty Step, Investigation abilities, and other utility functions. These
    abilities typically don't deal damage or heal but provide other benefits.
    """

    def __init__(
        self,
        name: str,
        type: ActionType,
        description: str,
        cooldown: int,
        maximum_uses: int,
        utility_function: str = "",
        effect: Effect | None = None,
        target_expr: str = "",
        target_restrictions: list[str] | None = None,
    ):
        """
        Initialize a new UtilityAbility.

        Args:
            name: Display name of the ability
            type: Action type (STANDARD, BONUS, REACTION, etc.)
            description: Flavor text describing what the ability does
            cooldown: Turns to wait before reusing (0 = no cooldown)
            maximum_uses: Max uses per encounter/day (-1 = unlimited)
            utility_function: Name of the utility function this ability performs
            effect: Optional effect applied to targets on use
            target_expr: Expression determining number of targets ("" = single target)
            target_restrictions: Override default targeting if needed

        Raises:
            ValueError: If name is empty or required parameters are invalid
        """
        try:
            super().__init__(
                name,
                type,
                ActionCategory.UTILITY,
                description,
                cooldown,
                maximum_uses,
                effect,
                target_expr,
                target_restrictions,
            )

            self.utility_function = utility_function or ""

        except Exception as e:
            log_critical(
                f"Error initializing UtilityAbility {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

    def execute(self, actor: Any, target: Any) -> bool:
        """
        Execute this utility ability on a target.

        This method handles the complete utility ability activation sequence
        focusing on the utility function and optional effect application.

        Args:
            actor: The character using the ability (must have combat methods)
            target: The character/object being affected (may be actor for self-targeted utilities)

        Returns:
            bool: True if ability was executed successfully, False on system errors
        """
        actor_str, target_str = self._get_display_strings(actor, target)

        # Check cooldown and uses
        assert not actor.is_on_cooldown(self), f"Action {self.name} is on cooldown."

        # Execute utility function if present
        utility_result = self._execute_utility_function(actor, target)

        # Apply optional effect
        effect_applied = self._apply_common_effects(actor, target)

        # Display results
        self._display_execution_result(
            actor_str, target_str, utility_result, effect_applied
        )

        return True

    def _execute_utility_function(self, actor: Any, target: Any) -> str:
        """
        Execute the specific utility function for this ability.

        Args:
            actor: The character using the ability
            target: The target of the ability

        Returns:
            str: Description of what the utility function accomplished
        """
        if not self.utility_function:
            return "No specific utility function"

        # In a full implementation, this would dispatch to specific handlers
        utility_functions = {
            "detect_magic": self._detect_magic,
            "teleport": self._teleport,
            "investigate": self._investigate,
            "identify": self._identify,
            # Add more utility functions as needed
        }

        handler = utility_functions.get(self.utility_function)
        if handler:
            return handler(actor, target)
        else:
            return f"Executed {self.utility_function}"

    def _detect_magic(self, actor: Any, target: Any) -> str:
        """Placeholder for detect magic utility function."""
        return "Detected magical auras in the area"

    def _teleport(self, actor: Any, target: Any) -> str:
        """Placeholder for teleportation utility function."""
        return "Teleported to a nearby location"

    def _investigate(self, actor: Any, target: Any) -> str:
        """Placeholder for investigation utility function."""
        return "Gained insight about the surroundings"

    def _identify(self, actor: Any, target: Any) -> str:
        """Placeholder for identify utility function."""
        return "Identified the properties of a magical item"

    def _display_execution_result(
        self,
        actor_str: str,
        target_str: str,
        utility_result: str,
        effect_applied: bool,
    ) -> None:
        """
        Display the results of the utility ability execution.

        Args:
            actor_str: Formatted actor name string
            target_str: Formatted target name string
            utility_result: Description of utility function result
            effect_applied: Whether effect was successfully applied
        """
        msg = f"    🔧 {actor_str} uses [bold cyan]{self.name}[/]"

        # Show target if different from actor
        if actor_str != target_str:
            msg += f" on {target_str}"

        if GLOBAL_VERBOSE_LEVEL == 0:
            msg += f" - {utility_result}"
            if self.effect and effect_applied:
                msg += f" and applies [bold yellow]{self.effect.name}[/]"
            msg += "."
        elif GLOBAL_VERBOSE_LEVEL >= 1:
            msg += f".\n        Result: {utility_result}"

            if self.effect:
                if effect_applied:
                    msg += f"\n        {target_str} is affected by [bold yellow]{self.effect.name}[/]"
                else:
                    msg += f"\n        {target_str} resists [bold yellow]{self.effect.name}[/]"
            msg += "."

        cprint(msg)

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def get_utility_description(self) -> str:
        """
        Get a description of what this utility ability does.

        Returns:
            str: Description of the utility function
        """
        if self.utility_function:
            return f"Performs {self.utility_function} utility function"
        elif self.effect:
            return f"Applies {self.effect.name} effect"
        else:
            return "General utility ability"

    def is_self_targeted(self) -> bool:
        """
        Check if this utility ability typically targets the user.

        Returns:
            bool: True if commonly self-targeted, False otherwise
        """
        self_targeted_functions = {"teleport", "investigate", "detect_magic", "stealth"}
        return self.utility_function in self_targeted_functions
