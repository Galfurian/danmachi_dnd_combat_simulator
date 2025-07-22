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

    Key Features:
        - No damage or healing components
        - Utility effects (teleportation, detection, etc.)
        - Information gathering capabilities
        - Environmental interaction
        - Problem-solving applications

    Effect System:
        - Optional effects (some utilities are pure mechanical functions)
        - Informational effects (like revealing information)
        - Movement effects (teleportation, dimension door)
        - Detection effects (magic, poison, traps)

    Usage Examples:
        - Detect Magic (reveals magical auras)
        - Misty Step (short-range teleportation)
        - Thieves' Tools Expertise (improved lock picking)
        - Animal Handling (calm or communicate with animals)
        - Investigation (enhanced searching abilities)
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

        Utility Function Examples:
            - "detect_magic": Reveals magical auras
            - "teleport": Short-range teleportation
            - "investigate": Enhanced searching
            - "animal_handling": Communicate with animals
            - "identify": Identify magical items

        Raises:
            ValueError: If name is empty or required parameters are invalid

        Note:
            - Category is automatically set to UTILITY
            - utility_function is optional (some utilities just apply effects)
            - Target restrictions vary based on utility type
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

        Execution Sequence:
            1. Validate cooldown and usage restrictions
            2. Execute the utility function if present
            3. Apply optional effect to target
            4. Display results with appropriate verbosity

        Args:
            actor: The character using the ability (must have combat methods)
            target: The character/object being affected (may be actor for self-targeted utilities)

        Returns:
            bool: True if ability was executed successfully, False on system errors

        Utility System:
            - Utility functions: Custom logic for specific utility types
            - Effect application: Optional effects for ongoing benefits
            - Information gathering: May provide information to the user
            - Environmental interaction: May affect the game world
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

        Note:
            This is a placeholder implementation. In a full system, this would
            dispatch to specific utility handlers based on utility_function.
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
        self_targeted_functions = {
            "teleport", "investigate", "detect_magic", "stealth"
        }
        return self.utility_function in self_targeted_functions

    # ============================================================================
    # SERIALIZATION METHODS
    # ============================================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the utility ability to a dictionary representation.

        Returns:
            dict: Complete dictionary representation suitable for JSON serialization
        """
        data = super().to_dict()
        if self.utility_function:
            data["utility_function"] = self.utility_function
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "UtilityAbility":
        """
        Creates a UtilityAbility instance from a dictionary.

        Args:
            data: Dictionary containing complete ability specification

        Returns:
            UtilityAbility: Fully initialized utility ability instance

        Required Dictionary Keys:
            - name: Ability name (str)
            - type: ActionType enum value (str)

        Optional Dictionary Keys:
            - description: Ability description (str, default: "")
            - cooldown: Turns between uses (int, default: 0)
            - maximum_uses: Max uses per encounter (int, default: -1)
            - utility_function: Utility function name (str, default: "")
            - effect: Effect dictionary (dict, default: None)
            - target_expr: Target count expression (str, default: "")
            - target_restrictions: Custom targeting rules (list, default: None)
        """
        return UtilityAbility(
            name=data["name"],
            type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            utility_function=data.get("utility_function", ""),
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
            target_expr=data.get("target_expr", ""),
            target_restrictions=data.get("target_restrictions"),
        )
