"""
Base spell classes for the magical combat system.

This module contains the abstract Spell base class that all magical abilities
inherit from. It defines core spell mechanics like mind costs, concentration,
level scaling, and targeting systems.
"""

from abc import abstractmethod
from logging import debug
from typing import Any

from actions.base_action import BaseAction
from core.constants import ActionCategory, ActionType
from core.error_handling import (
    log_error,
    log_warning,
    log_critical,
    ensure_non_negative_int,
    ensure_string,
    ensure_list_of_type,
    safe_get_attribute,
)
from core.utils import evaluate_expression
from effects.effect import Effect


class Spell(BaseAction):
    """
    Abstract base class for all magical spells in the combat system.

    Spells represent magical abilities that consume mind points (mana) and can target
    single or multiple entities. Unlike physical attacks or innate abilities, spells
    have complex mechanics including level scaling, mind costs, concentration requirements,
    and sophisticated targeting systems.

    Core Spell Mechanics:
        - Mind Cost System: Each spell has costs per level (mind_cost list)
        - Level Scaling: Higher levels consume more mind but increase effectiveness
        - Concentration: Some spells require ongoing mental focus to maintain
        - Target Expressions: Dynamic targeting based on character stats and spell level

    Spell Categories:
        - SpellAttack: Offensive spells that deal damage (Fireball, Magic Missile)
        - SpellHeal: Restorative spells that recover HP (Cure Wounds, Heal)
        - SpellBuff: Beneficial spells that enhance targets (Bless, Haste)
        - SpellDebuff: Detrimental spells that hinder targets (Hold Person, Slow)

    Mind Cost System:
        The mind_cost list contains the mind point cost for each spell level:
        - Index 0: Cost for level 1 casting
        - Index 1: Cost for level 2 casting
        - etc.

    Target Expression System:
        - Empty string "": Single target (most spells)
        - "3": Always affects exactly 3 targets
        - "LEVEL": Affects targets equal to caster level
        - "1 + MIND//2": Dynamic scaling based on spell level

    Concentration Mechanics:
        - Only one concentration spell can be active per caster
        - Casting a new concentration spell breaks the previous one
        - Damage or specific effects can break concentration

    Abstract Methods:
        Subclasses must implement cast_spell() to define their specific behavior.

    Note:
        This class inherits targeting logic from BaseAction but adds spell-specific
        mechanics like mind costs, concentration, and level-based scaling.
    """

    def __init__(
        self,
        name: str,
        type: ActionType,
        description: str,
        cooldown: int,
        maximum_uses: int,
        level: int,
        mind_cost: list[int],
        category: ActionCategory,
        target_expr: str = "",
        requires_concentration: bool = False,
        target_restrictions: list[str] | None = None,
    ):
        """
        Initialize a new Spell.

        Args:
            name: Display name of the spell
            type: Action type (ACTION, BONUS_ACTION, REACTION, etc.)
            description: Flavor text describing what the spell does
            cooldown: Turns to wait before reusing (0 = no cooldown)
            maximum_uses: Max uses per encounter/day (-1 = unlimited)
            level: Base spell level (1-9 for most spells, 0 for cantrips)
            mind_cost: List of mind point costs per casting level [level1, level2, ...]
            category: Spell category (OFFENSIVE, HEALING, SUPPORT, DEBUFF)
            target_expr: Expression determining number of targets ("" = single target)
            requires_concentration: Whether spell requires ongoing mental focus
            target_restrictions: Override default targeting if needed

        Mind Cost Examples:
            - [3, 5, 7]: Level 1 costs 3, level 2 costs 5, level 3 costs 7
            - [0]: Cantrip, always costs 0 mind points
            - [4, 6, 8, 10, 12]: Spell scalable up to level 5

        Target Expression Examples:
            - "": Single target (default)
            - "3": Always affects 3 targets
            - "MIND": Affects targets equal to spell level used
            - "1 + LEVEL//3": Scales with caster level
            - "max(1, CHA)": At least 1, up to CHA modifier targets

        Raises:
            ValueError: If name is empty or type/category are invalid

        Note:
            - Uses enhanced validation helpers for robust error handling
            - Invalid mind_cost values are corrected with warnings
            - Invalid target_expr is corrected to empty string
            - Concentration flag is auto-corrected to boolean
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

            # Validate level using helper
            self.level = ensure_non_negative_int(
                level, "spell level", 0, {"name": name}
            )

            # Validate mind_cost list using helper
            self.mind_cost = ensure_list_of_type(
                mind_cost,
                int,
                "mind cost",
                [0],
                converter=lambda x: (
                    max(0, int(x)) if isinstance(x, (int, float)) else 0
                ),
                validator=lambda x: isinstance(x, int) and x >= 0,
                context={"name": name},
            )

            # Validate target_expr using helper
            self.target_expr = ensure_string(
                target_expr, "target expression", "", {"name": name}
            )

            # Validate requires_concentration
            if not isinstance(requires_concentration, bool):
                log_warning(
                    f"Spell {name} requires_concentration must be boolean, got: {requires_concentration.__class__.__name__}, setting to False",
                    {"name": name, "requires_concentration": requires_concentration},
                )
                requires_concentration = False

            self.requires_concentration = requires_concentration

        except Exception as e:
            log_critical(
                f"Error initializing Spell {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

    # ============================================================================
    # TARGETING SYSTEM METHODS
    # ============================================================================

    def is_single_target(self) -> bool:
        """
        Check if the spell targets a single entity.

        Determines targeting mode based on the target_expr property. Empty or
        whitespace-only expressions indicate single-target spells, while
        any meaningful expression indicates multi-target spells.

        Returns:
            bool: True if spell targets one entity, False for multi-target

        Examples:
            ```python
            # Single target examples
            single_spell.target_expr = ""        # True
            single_spell.target_expr = "   "     # True

            # Multi-target examples
            multi_spell.target_expr = "3"        # False
            multi_spell.target_expr = "MIND"     # False
            ```
        """
        return not self.target_expr or self.target_expr.strip() == ""

    def target_count(self, actor: Any, mind_level: int) -> int:
        """
        Calculate the number of targets this spell can affect.

        Evaluates the target_expr with the actor's current variables and the
        specified mind level to determine the actual number of targets. This
        supports dynamic scaling based on character level, spell level, ability
        scores, or other factors.

        Args:
            actor: The character casting the spell (must have expression variables)
            mind_level: The spell level being used for casting

        Returns:
            int: Number of targets (minimum 1, even for invalid expressions)

        Variable Substitution:
            - {MIND}: The mind level (spell level) being used
            - {LEVEL}: Character level
            - {STR}, {DEX}, {CON}, {INT}, {WIS}, {CHA}: Ability modifiers
            - {PROF}: Proficiency bonus
            - Custom variables from actor's get_expression_variables method

        Examples:
            ```python
            # Static target count
            spell.target_expr = "3"           # Always 3 targets

            # Spell level scaling
            spell.target_expr = "MIND"        # 1 target per spell level
            spell.target_expr = "1 + MIND//2" # Extra target every 2 levels

            # Character level based
            spell.target_expr = "1 + LEVEL//4" # Scales with character level

            # Ability score based
            spell.target_expr = "max(1, CHA)" # CHA modifier minimum 1
            ```

        Error Handling:
            Returns 1 if target_expr is empty, invalid, or evaluates to 0 or less.
        """
        if self.target_expr:
            variables = actor.get_expression_variables()
            variables["MIND"] = mind_level
            # Evaluate the multi-target expression to get the number of targets.
            return evaluate_expression(self.target_expr, variables)
        return 1

    # ============================================================================
    # SPELL SYSTEM METHODS
    # ============================================================================

    def execute(self, actor: Any, target: Any) -> bool:
        """
        Execute spell - delegates to cast_spell method.

        This method is required by the BaseAction interface but for spells we use
        the cast_spell method instead, which takes an additional mind_level parameter
        for spell level scaling.

        Args:
            actor: The character casting the spell
            target: The target of the spell

        Returns:
            bool: Always False - use cast_spell() instead

        Raises:
            NotImplementedError: Always raised to enforce using cast_spell()

        Note:
            Spells should always be cast using the cast_spell() method which allows
            specifying the spell level for proper mind cost and scaling calculations.
        """
        raise NotImplementedError("Spells must use the cast_spell method.")

    @abstractmethod
    def cast_spell(self, actor: Any, target: Any, mind_level: int) -> bool:
        """
        Abstract method for casting spells with level-specific behavior.

        This is the primary method for executing spells. Unlike the base execute()
        method, cast_spell() takes a mind_level parameter that determines the
        spell's power level, mind cost, and scaling effects.

        Args:
            actor: The character casting the spell (must have mind points)
            target: The character targeted by the spell
            mind_level: The spell level to cast at (1-9, affects cost and power)

        Returns:
            bool: True if spell was cast successfully, False on failure

        Implementation Requirements:
            Subclasses must implement this method to define their specific behavior:
            - Check mind point availability against mind_cost[mind_level-1]
            - Validate cooldowns and usage restrictions
            - Apply level-specific scaling to damage/healing/effects
            - Handle concentration requirements if applicable
            - Display appropriate combat messages
            - Return success/failure status

        Mind Level System:
            The mind_level parameter indexes into the mind_cost array:
            - mind_level=1 uses mind_cost[0]
            - mind_level=2 uses mind_cost[1]
            - etc.

        Example Implementation Pattern:
            ```python
            def cast_spell(self, actor, target, mind_level):
                # Validate mind cost
                if actor.mind < self.mind_cost[mind_level-1]:
                    return False

                # Apply spell effects with level scaling
                damage = base_damage + (mind_level * scaling)

                # Deduct mind cost and apply effects
                actor.mind -= self.mind_cost[mind_level-1]
                return True
            ```
        """
        pass

    # ============================================================================
    # SERIALIZATION METHODS
    # ============================================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the spell to a dictionary representation.

        Creates a complete serializable representation of the spell including
        all properties from the base class plus spell-specific data like
        level, mind costs, concentration requirements, and targeting expressions.

        Returns:
            dict: Complete dictionary representation suitable for JSON serialization

        Dictionary Structure:
            - Base properties: name, type, description, cooldown, maximum_uses
            - Spell properties: level, mind_cost, requires_concentration
            - Optional: target_expr if multi-target
        """
        data = super().to_dict()
        # Add specific fields for Spell
        data["level"] = self.level
        data["mind_cost"] = self.mind_cost
        data["requires_concentration"] = self.requires_concentration
        # Include the multi-target expression if it exists.
        if self.target_expr:
            data["target_expr"] = self.target_expr
        return data
