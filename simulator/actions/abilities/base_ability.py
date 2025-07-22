"""
Base ability class for all special character abilities.

This module provides the abstract BaseAbility class that serves as the foundation
for all ability types including offensive, healing, buff, utility, and
DanMachi-specific development abilities.
"""

from abc import ABC, abstractmethod
from typing import Any

from actions.base_action import BaseAction
from combat.damage import DamageComponent, roll_damage_components_no_mind
from core.constants import (
    ActionCategory,
    ActionType,
    BonusType,
    GLOBAL_VERBOSE_LEVEL,
    apply_character_type_color,
    get_effect_color,
)
from core.error_handling import (
    log_critical,
    log_warning,
    ensure_string,
    ensure_list_of_type,
    validate_required_object,
)
from core.utils import (
    debug,
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    substitute_variables,
    cprint,
    evaluate_expression,
)
from effects.effect import Effect


class BaseAbility(BaseAction, ABC):
    """
    Abstract base class for all character abilities and special powers.

    BaseAbility represents special powers, racial abilities, monster attacks, and
    other unique actions that don't fall into standard weapon attacks or spells.
    These abilities typically have limited uses per encounter or cooldown periods
    rather than consuming spell slots or mind points.

    Key Characteristics:
        - Category-specific behavior (offensive, healing, utility, etc.)
        - No resource costs (no mind points or spell slots)
        - Often have uses per day/encounter or cooldown restrictions
        - Can affect single or multiple targets based on target_expr
        - May deal damage, heal, buff, or provide utility effects
        - Represent inherent powers rather than learned techniques

    Target System:
        - Single target: Empty or blank target_expr (default)
        - Multi-target: target_expr evaluates to number of targets
        - Example: target_expr="LEVEL//2" affects half character level targets

    Damage/Effect System:
        - Direct application (no attack rolls by default for most abilities)
        - Multiple damage/healing components supported
        - Integrates with effect manager for bonuses
        - Category-specific execution behavior

    Usage Context:
        - Dragon breath weapons (offensive)
        - Healing Word abilities (healing)
        - Bardic Inspiration (buff)
        - Detect Magic (utility)
        - DanMachi development abilities (development)

    Subclass Implementation:
        Each concrete ability type must implement:
        - execute(): Category-specific execution logic
        - Additional methods as needed for their category
    """

    def __init__(
        self,
        name: str,
        type: ActionType,
        category: ActionCategory,
        description: str,
        cooldown: int,
        maximum_uses: int,
        effect: Effect | None = None,
        target_expr: str = "",
        target_restrictions: list[str] | None = None,
    ):
        """
        Initialize a new BaseAbility.

        Args:
            name: Display name of the ability
            type: Action type (STANDARD, BONUS, REACTION, etc.)
            category: Action category (OFFENSIVE, HEALING, BUFF, UTILITY, etc.)
            description: Flavor text describing what the ability does
            cooldown: Turns to wait before reusing (0 = no cooldown)
            maximum_uses: Max uses per encounter/day (-1 = unlimited)
            effect: Optional effect applied to targets on use
            target_expr: Expression determining number of targets ("" = single target)
            target_restrictions: Override default targeting if needed

        Target Expression Examples:
            - "": Single target (default)
            - "3": Always affects 3 targets
            - "LEVEL//2": Affects half character level targets (minimum 1)
            - "CON": Affects targets equal to CON modifier

        Raises:
            ValueError: If name is empty or type/category are invalid

        Note:
            - Invalid effects are set to None with warnings
            - Invalid target_expr is corrected to empty string
            - Uses enhanced validation helpers for robust error handling
            - Concrete subclasses may add additional parameters
        """
        try:
            super().__init__(
                name,
                type,
                category,
                description,
                cooldown,
                maximum_uses,
                target_restrictions,
            )

            # Validate effect
            if effect is not None and not isinstance(effect, Effect):
                log_warning(
                    f"Ability {name} effect must be Effect or None, got: {effect.__class__.__name__}, setting to None",
                    {"name": name, "effect": effect},
                )
                effect = None

            # Validate target_expr using helper
            self.target_expr = ensure_string(
                target_expr, "target expression", "", {"name": name}
            )

            self.effect: Effect | None = effect

        except Exception as e:
            log_critical(
                f"Error initializing BaseAbility {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

    # ============================================================================
    # TARGETING SYSTEM METHODS (SHARED BY ALL ABILITIES)
    # ============================================================================

    def is_single_target(self) -> bool:
        """
        Check if the ability targets a single entity.

        Determines targeting mode based on the target_expr property. Empty or
        whitespace-only expressions indicate single-target abilities, while
        any meaningful expression indicates multi-target abilities.

        Returns:
            bool: True if ability targets one entity, False for multi-target

        Examples:
            ```python
            # Single target examples
            single_ability.target_expr = ""        # True
            single_ability.target_expr = "   "     # True

            # Multi-target examples
            multi_ability.target_expr = "3"        # False
            multi_ability.target_expr = "LEVEL"    # False
            ```
        """
        return not self.target_expr or self.target_expr.strip() == ""

    def target_count(self, actor: Any) -> int:
        """
        Calculate the number of targets this ability can affect.

        Evaluates the target_expr with the actor's current variables to determine
        the actual number of targets. This supports dynamic scaling based on
        character level, ability scores, or other factors.

        Args:
            actor: The character using the ability (must have expression variables)

        Returns:
            int: Number of targets (minimum 1, even for invalid expressions)

        Variable Substitution:
            - {LEVEL}: Character level
            - {STR}, {DEX}, {CON}, {INT}, {WIS}, {CHA}: Ability modifiers
            - {PROF}: Proficiency bonus
            - Custom variables from actor's get_expression_variables method

        Examples:
            ```python
            # Static target count
            ability.target_expr = "3"           # Always 3 targets

            # Level-scaled targeting
            ability.target_expr = "1 + LEVEL//4"  # 1 + (level / 4)

            # Ability score based
            ability.target_expr = "max(1, CHA)"   # CHA modifier minimum 1
            ```

        Error Handling:
            Returns 1 if target_expr is empty, invalid, or evaluates to 0 or less.
        """
        if self.target_expr:
            variables = actor.get_expression_variables()
            return max(1, int(evaluate_expression(self.target_expr, variables)))
        return 1

    # ============================================================================
    # COMMON EXECUTION HELPERS (SHARED BY ALL ABILITIES)
    # ============================================================================

    def _get_display_strings(self, actor: Any, target: Any) -> tuple[str, str]:
        """
        Get formatted display strings for actor and target.

        Args:
            actor: The character using the ability
            target: The target character

        Returns:
            tuple[str, str]: (actor_display, target_display)
        """
        actor_str = apply_character_type_color(actor.type, actor.name)
        target_str = apply_character_type_color(target.type, target.name)
        return actor_str, target_str

    def _apply_common_effects(self, actor: Any, target: Any) -> bool:
        """
        Apply the ability's inherent effect if present.

        Args:
            actor: The character using the ability
            target: The target character

        Returns:
            bool: True if effect was successfully applied, False otherwise
        """
        if self.effect:
            return self._common_apply_effect(actor, target, self.effect)
        return True

    def _roll_bonus_damage(self, actor: Any, target: Any) -> tuple[int, list[str]]:
        """
        Roll any bonus damage from effects.

        Args:
            actor: The character using the ability
            target: The target character

        Returns:
            tuple[int, list[str]]: (bonus_damage, damage_descriptions)
        """
        all_damage_modifiers = actor.effects_module.get_damage_modifiers()
        return roll_damage_components_no_mind(actor, target, all_damage_modifiers)

    # ============================================================================
    # ABSTRACT METHODS (MUST BE IMPLEMENTED BY SUBCLASSES)
    # ============================================================================

    @abstractmethod
    def execute(self, actor: Any, target: Any) -> bool:
        """
        Execute this ability against a target.

        This method must be implemented by each concrete ability subclass to
        handle their specific execution logic (damage dealing, healing, buffing, etc.).

        Args:
            actor: The character using the ability
            target: The target character

        Returns:
            bool: True if ability was executed successfully, False on system errors
        """
        pass
