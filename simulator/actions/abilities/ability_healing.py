"""
Healing abilities that restore hit points to allies.

This module contains the HealingAbility class for healing special abilities
like Healing Word, Lay on Hands, and other restorative powers.
"""

from typing import Any

from actions.abilities.base_ability import BaseAbility
from core.constants import ActionCategory, ActionType, GLOBAL_VERBOSE_LEVEL
from core.error_handling import ensure_string, log_critical
from core.utils import (
    cprint,
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    roll_and_describe,
    substitute_variables,
)
from effects.effect import Effect


class HealingAbility(BaseAbility):
    """
    Healing abilities that restore hit points to targets.

    HealingAbility represents healing special powers like Healing Word, Lay on
    Hands, Second Wind, and other restorative abilities. These abilities restore
    hit points without requiring attack rolls and always succeed on willing targets.

    Key Features:
        - Automatic success on willing targets
        - Variable healing with dice expressions
        - Level scaling support with variables
        - Effect application (like ongoing regeneration)
        - Multi-target support through target expressions

    Healing System:
        - Healing roll expressions (similar to damage rolls)
        - Variable substitution for scaling
        - Bonus healing from effects and modifiers
        - Cannot heal beyond maximum hit points

    Usage Examples:
        - Healing Word (bonus action healing)
        - Lay on Hands (paladin healing pool)
        - Second Wind (fighter self-healing)
        - Cure Wounds (cleric/druid healing spells as abilities)
        - Regeneration abilities

    Example:
        ```python
        # Create a healing word ability
        healing_word = HealingAbility(
            name="Healing Word",
            type=ActionType.BONUS,
            description="Speak a word of healing to restore hit points",
            cooldown=0,
            maximum_uses=3,  # 3 uses per short rest
            heal_roll="1d4 + CHA",
            target_expr="",  # Single target
            effect=None
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
        heal_roll: str,
        effect: Effect | None = None,
        target_expr: str = "",
        target_restrictions: list[str] | None = None,
    ):
        """
        Initialize a new HealingAbility.

        Args:
            name: Display name of the ability
            type: Action type (STANDARD, BONUS, REACTION, etc.)
            description: Flavor text describing what the ability does
            cooldown: Turns to wait before reusing (0 = no cooldown)
            maximum_uses: Max uses per encounter/day (-1 = unlimited)
            heal_roll: Healing expression (e.g., "2d8 + WIS", "1d4 + LEVEL")
            effect: Optional effect applied to targets on use (like regeneration)
            target_expr: Expression determining number of targets ("" = single target)
            target_restrictions: Override default targeting if needed

        Healing Expression Examples:
            - "1d8 + 3": Fixed healing with static bonus
            - "2d4 + WIS": Healing scaled by Wisdom modifier
            - "LEVEL": Healing equal to character level
            - "1d4 + PROF": Healing scaled by proficiency bonus

        Raises:
            ValueError: If name is empty or required parameters are invalid

        Note:
            - Category is automatically set to HEALING
            - Invalid heal_roll expressions are corrected to "0"
            - Target restrictions default to allies only
        """
        try:
            super().__init__(
                name,
                type,
                ActionCategory.HEALING,
                description,
                cooldown,
                maximum_uses,
                effect,
                target_expr,
                target_restrictions,
            )

            # Validate heal_roll using helper
            self.heal_roll = ensure_string(
                heal_roll, "heal roll", "0", {"name": name}
            )

        except Exception as e:
            log_critical(
                f"Error initializing HealingAbility {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

    def execute(self, actor: Any, target: Any) -> bool:
        """
        Execute this healing ability on a target.

        This method handles the complete healing ability activation sequence
        from healing calculation through effect application.

        Execution Sequence:
            1. Validate cooldown and usage restrictions
            2. Calculate base healing from ability expression
            3. Apply healing modifiers from effects
            4. Restore hit points to target (capped at maximum)
            5. Apply optional effect to target
            6. Display results with appropriate verbosity

        Args:
            actor: The character using the ability (must have combat methods)
            target: The character being healed (must have combat methods)

        Returns:
            bool: True if ability was executed successfully, False on system errors

        Healing System:
            - Automatic success: No rolls needed, healing always applies
            - Variable healing: Uses dice expressions with scaling support
            - Capped healing: Cannot exceed target's maximum hit points
            - Effect application: Optional effects like regeneration

        Example:
            ```python
            # Execute a healing word ability
            if healing_word.execute(cleric, wounded_fighter):
                print("Healing word activated successfully")
            else:
                print("System error during ability execution")
            ```
        """
        actor_str, target_str = self._get_display_strings(actor, target)

        # Check cooldown and uses
        assert not actor.is_on_cooldown(self), f"Action {self.name} is on cooldown."

        # Roll healing amount
        variables = actor.get_expression_variables()
        healing_amount, healing_desc, _ = roll_and_describe(self.heal_roll, variables)

        # Apply healing to target
        old_hp = target.hp
        target.heal(healing_amount)
        actual_healing = target.hp - old_hp

        # Apply effects
        effect_applied = self._apply_common_effects(actor, target)

        # Display results
        self._display_execution_result(
            actor_str, target_str, healing_amount, actual_healing, 
            healing_desc, effect_applied
        )

        return True

    def _display_execution_result(
        self,
        actor_str: str,
        target_str: str,
        healing_amount: int,
        actual_healing: int,
        healing_desc: str,
        effect_applied: bool,
    ) -> None:
        """
        Display the results of the healing ability execution.

        Args:
            actor_str: Formatted actor name string
            target_str: Formatted target name string
            healing_amount: Amount of healing rolled
            actual_healing: Actual healing applied (may be less due to max HP)
            healing_desc: Description of the healing roll
            effect_applied: Whether effect was successfully applied
        """
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

    # ============================================================================
    # HEALING CALCULATION METHODS
    # ============================================================================

    def get_heal_expr(self, actor: Any) -> str:
        """
        Returns the healing expression with variables substituted.

        Args:
            actor: The character using the ability

        Returns:
            str: Complete healing expression with variables replaced by values
        """
        variables = actor.get_expression_variables()
        return substitute_variables(self.heal_roll, variables)

    def get_min_heal(self, actor: Any) -> int:
        """
        Returns the minimum possible healing value for the ability.

        Args:
            actor: The character using the ability

        Returns:
            int: Minimum healing amount
        """
        variables = actor.get_expression_variables()
        substituted = substitute_variables(self.heal_roll, variables)
        return parse_expr_and_assume_min_roll(substituted)

    def get_max_heal(self, actor: Any) -> int:
        """
        Returns the maximum possible healing value for the ability.

        Args:
            actor: The character using the ability

        Returns:
            int: Maximum healing amount
        """
        variables = actor.get_expression_variables()
        substituted = substitute_variables(self.heal_roll, variables)
        return parse_expr_and_assume_max_roll(substituted)

    # ============================================================================
    # SERIALIZATION METHODS
    # ============================================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the healing ability to a dictionary representation.

        Returns:
            dict: Complete dictionary representation suitable for JSON serialization
        """
        data = super().to_dict()
        data["heal_roll"] = self.heal_roll
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "HealingAbility":
        """
        Creates a HealingAbility instance from a dictionary.

        Args:
            data: Dictionary containing complete ability specification

        Returns:
            HealingAbility: Fully initialized healing ability instance

        Required Dictionary Keys:
            - name: Ability name (str)
            - type: ActionType enum value (str)
            - heal_roll: Healing expression (str)

        Optional Dictionary Keys:
            - description: Ability description (str, default: "")
            - cooldown: Turns between uses (int, default: 0)
            - maximum_uses: Max uses per encounter (int, default: -1)
            - effect: Effect dictionary (dict, default: None)
            - target_expr: Target count expression (str, default: "")
            - target_restrictions: Custom targeting rules (list, default: None)
        """
        return HealingAbility(
            name=data["name"],
            type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            heal_roll=data["heal_roll"],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
            target_expr=data.get("target_expr", ""),
            target_restrictions=data.get("target_restrictions"),
        )
