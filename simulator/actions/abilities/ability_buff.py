"""
Buff abilities that provide beneficial effects to allies.

This module contains the BuffAbility class for beneficial special abilities
like Bardic Inspiration, Guidance, and other enhancement powers.
"""

from typing import Any

from actions.abilities.base_ability import BaseAbility
from core.constants import ActionCategory, ActionType, GLOBAL_VERBOSE_LEVEL, get_effect_color
from core.error_handling import log_critical
from core.utils import cprint
from effects.effect import Effect


class BuffAbility(BaseAbility):
    """
    Buff abilities that provide beneficial effects to targets.

    BuffAbility represents beneficial special powers like Bardic Inspiration,
    Guidance, Bless, and other enhancement abilities. These abilities apply
    positive effects to allies without dealing damage.

    Key Features:
        - No damage components (pure effect application)
        - Always beneficial effects on willing targets
        - Duration-based enhancements
        - Multi-target support through target expressions
        - Concentration requirements for some abilities

    Effect System:
        - Mandatory effect parameter (buffs must provide benefits)
        - Effect duration management
        - Stacking rules handled by effect system
        - Concentration tracking for long-duration buffs

    Usage Examples:
        - Bardic Inspiration (bonus dice to rolls)
        - Guidance (advantage on ability checks)
        - Bless (attack and save bonuses)
        - Heroism (temporary hit points and immunity to fear)
        - Haste (extra actions and movement)

    Example:
        ```python
        # Create a bardic inspiration ability
        inspiration = BuffAbility(
            name="Bardic Inspiration",
            type=ActionType.BONUS,
            description="Inspire an ally with words of encouragement",
            cooldown=0,
            maximum_uses=3,  # Based on Charisma modifier
            effect=inspiration_effect,  # Provides bonus d6 to rolls
            target_expr=""  # Single target
        )
        ```
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

        Note:
            - Category is automatically set to BUFF
            - Effect parameter is mandatory (buff abilities must provide benefits)
            - Target restrictions default to allies and self
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

        Execution Sequence:
            1. Validate cooldown and usage restrictions
            2. Apply the beneficial effect to target
            3. Handle concentration requirements if applicable
            4. Display results with appropriate verbosity

        Args:
            actor: The character using the ability (must have combat methods)
            target: The character being buffed (must have combat methods)

        Returns:
            bool: True if ability was executed successfully, False on system errors

        Buff System:
            - Pure effect application: No damage or healing rolls
            - Beneficial effects: Always positive enhancements
            - Duration management: Effects have their own duration tracking
            - Concentration: Some buffs require concentration to maintain

        Example:
            ```python
            # Execute a bardic inspiration ability
            if inspiration.execute(bard, fighter):
                print("Bardic inspiration activated successfully")
            else:
                print("System error during ability execution")
            ```
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
                msg += f" but {target_str} resists [{effect_color}]{self.effect.name}[/]"
            msg += ".\n"
            
            if effect_applied and hasattr(self.effect, 'description'):
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
        if self.effect and hasattr(self.effect, 'description'):
            return self.effect.description
        return f"Applies {self.effect.name}" if self.effect else "No effect"

    def is_concentration_required(self) -> bool:
        """
        Check if this buff ability requires concentration.

        Returns:
            bool: True if concentration is required, False otherwise
        """
        # Effect is guaranteed to exist for BuffAbility
        assert self.effect is not None, "BuffAbility must have an effect"
        return (hasattr(self.effect, 'requires_concentration') and 
                self.effect.requires_concentration)

    # ============================================================================
    # SERIALIZATION METHODS
    # ============================================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the buff ability to a dictionary representation.

        Returns:
            dict: Complete dictionary representation suitable for JSON serialization

        Note:
            The effect field is always included since it's mandatory for buff abilities.
        """
        data = super().to_dict()
        # Effect is guaranteed to exist for BuffAbility
        assert self.effect is not None, "BuffAbility must have an effect"
        data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "BuffAbility":
        """
        Creates a BuffAbility instance from a dictionary.

        Args:
            data: Dictionary containing complete ability specification

        Returns:
            BuffAbility: Fully initialized buff ability instance

        Required Dictionary Keys:
            - name: Ability name (str)
            - type: ActionType enum value (str)
            - effect: Effect dictionary (dict, required for buff abilities)

        Optional Dictionary Keys:
            - description: Ability description (str, default: "")
            - cooldown: Turns between uses (int, default: 0)
            - maximum_uses: Max uses per encounter (int, default: -1)
            - target_expr: Target count expression (str, default: "")
            - target_restrictions: Custom targeting rules (list, default: None)

        Raises:
            ValueError: If effect is missing from the data dictionary
        """
        if "effect" not in data:
            raise ValueError(f"BuffAbility {data.get('name', 'Unknown')} requires an effect")

        return BuffAbility(
            name=data["name"],
            type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            effect=Effect.from_dict(data["effect"]),
            target_expr=data.get("target_expr", ""),
            target_restrictions=data.get("target_restrictions"),
        )
