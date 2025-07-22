"""
Healing spell implementation.

This module contains the SpellHeal class for restorative magical spells
that restore hit points and can apply beneficial effects.
"""

from logging import debug
from typing import Any

from actions.spells.base_spell import Spell
from core.constants import (
    ActionCategory,
    ActionType,
    GLOBAL_VERBOSE_LEVEL,
    get_effect_color,
)
from core.error_handling import (
    log_error,
    log_warning,
    log_critical,
    ensure_string,
)
from core.utils import (
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    roll_and_describe,
    simplify_expression,
    substitute_variables,
    cprint,
)
from effects.effect import Effect


class SpellHeal(Spell):
    """
    Restorative spell that heals hit points and can apply beneficial effects.

    SpellHeal represents magical healing abilities that restore lost hit points
    to targets. Unlike offensive spells, healing spells automatically succeed
    without requiring attack rolls, making them reliable support options in
    combat and exploration scenarios.

    Core Mechanics:
        - Automatic Success: No attack rolls needed, healing always applies
        - Variable Healing: Uses dice expressions with level scaling support
        - Effect Integration: Can apply additional beneficial effects
        - Multi-Target Support: Can heal multiple allies simultaneously
        - Mind Cost Scaling: Higher levels provide more healing for increased cost

    Healing System:
        Each spell has a heal_roll expression that determines healing amount:
        - Dice notation: "2d8", "3d6+4", etc.
        - Level scaling: Can use MIND variable for spell level scaling
        - Character scaling: Can use caster stats (WIS, CHA, etc.)
        - Fixed modifiers: Static bonuses added to dice rolls

    Healing Resolution:
        1. Check mind point availability and cooldowns
        2. Handle concentration requirements if applicable
        3. Roll healing expression with level scaling
        4. Apply healing to target (limited by max HP)
        5. Apply optional beneficial effects
        6. Display healing feedback to players

    Level Scaling Examples:
        - "2d8 + 2": Static healing regardless of spell level
        - "1d8 + MIND": Adds spell level to healing
        - "MIND d8 + MIND": Both dice count and modifier scale
        - "2d8 + WIS": Healing scales with caster's Wisdom modifier

    Multi-Target Healing:
        SpellHeal supports healing multiple targets through target_expr:
        - Single target: target_expr = "" (most healing spells)
        - Group healing: target_expr = "3" or "MIND//2"
        - Mass healing: target_expr = "MIND + 2"
        - Each target receives full healing amount

    Effect Integration:
        Optional effects can provide additional benefits:
        - Temporary hit point bonuses
        - Resistance to damage types
        - Regeneration over time effects
        - Status condition removal (poison, disease, etc.)

    Attributes:
        heal_roll: Dice expression determining healing amount with scaling support
        effect: Optional beneficial effect applied alongside healing

    Note:
        SpellHeal inherits all spell mechanics (mind costs, concentration,
        targeting) from the base Spell class while adding healing-specific
        logic that always succeeds and cannot critically hit or fumble.
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
        heal_roll: str,
        effect: Effect | None = None,
        target_expr: str = "",
        requires_concentration: bool = False,
        target_restrictions: list[str] | None = None,
    ):
        """
        Initialize a new SpellHeal.

        Args:
            name: Display name of the spell
            type: Action type (ACTION, BONUS_ACTION, REACTION, etc.)
            description: Flavor text describing what the spell does
            cooldown: Turns to wait before reusing (0 = no cooldown)
            maximum_uses: Max uses per encounter/day (-1 = unlimited)
            level: Base spell level (1-9 for most spells, 0 for cantrips)
            mind_cost: List of mind point costs per casting level
            heal_roll: Healing expression with level scaling support
            effect: Optional beneficial effect applied alongside healing
            target_expr: Expression determining number of targets
            requires_concentration: Whether spell requires concentration
            target_restrictions: Override default targeting if needed

        Raises:
            ValueError: If heal_roll is invalid or other parameters are invalid
        """
        try:
            super().__init__(
                name,
                type,
                description,
                cooldown,
                maximum_uses,
                level,
                mind_cost,
                ActionCategory.HEALING,
                target_expr,
                requires_concentration,
                target_restrictions,
            )

            # Validate heal_roll expression using helper
            self.heal_roll = ensure_string(
                heal_roll, "heal roll expression", "", {"name": name}
            )
            if not self.heal_roll:
                log_critical(
                    f"SpellHeal {name} must have a valid heal_roll expression",
                    {"name": name, "heal_roll": heal_roll},
                )
                raise ValueError(
                    f"SpellHeal {name} must have a valid heal_roll expression"
                )

            # Validate optional effect
            if effect is not None and not isinstance(effect, Effect):
                log_warning(
                    f"SpellHeal {name} effect must be Effect or None, got: {type(effect).__name__}, setting to None",
                    {"name": name, "effect_type": type(effect).__name__},
                )
                effect = None

            self.effect = effect

        except Exception as e:
            log_critical(
                f"Error initializing SpellHeal {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

    # ============================================================================
    # HEALING SPELL METHODS
    # ============================================================================

    def cast_spell(self, actor: Any, target: Any, mind_level: int) -> bool:
        """
        Execute a healing spell with automatic success and beneficial effects.

        Args:
            actor: The character casting the spell
            target: The character targeted by the spell
            mind_level: The spell level to cast at (affects cost and power)

        Returns:
            bool: True if spell was cast successfully, False on failure
        """

        # Call the base class cast_spell to handle common checks.
        if super().cast_spell(actor, target, mind_level) is False:
            return False

        # Handle concentration requirements
        if self.requires_concentration:
            actor.concentration_module.break_concentration()

        # Format character strings for output.
        actor_str, target_str = self._get_display_strings(actor, target)

        # Calculate healing with level scaling
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        heal_value, heal_desc, _ = roll_and_describe(self.heal_roll, variables)

        # Apply healing to target (limited by max HP)
        actual_healed = target.heal(heal_value)

        # Apply optional effect
        effect_applied = False
        if self.effect:
            effect_applied = self._common_apply_effect(
                actor, target, self.effect, mind_level
            )

        # Display healing results
        msg = f"    ✳️ {actor_str} casts [bold]{self.name}[/] on {target_str}"
        msg += f" healing for [bold green]{actual_healed}[/]"
        if GLOBAL_VERBOSE_LEVEL >= 1:
            msg += f" ({heal_desc})"
        if effect_applied and self.effect:
            msg += (
                f" and applying [{get_effect_color(self.effect)}]{self.effect.name}[/]"
            )
        elif self.effect and not effect_applied:
            msg += f" but failing to apply [{get_effect_color(self.effect)}]{self.effect.name}[/]"
        msg += "."
        cprint(msg)

        return True

    # ============================================================================
    # HEALING CALCULATION METHODS
    # ============================================================================

    def get_heal_expr(self, actor: Any, mind_level: int | None = 1) -> str:
        """
        Get healing expression with variables substituted for display.

        Args:
            actor: The character casting the spell
            mind_level: The spell level to use for MIND variable substitution

        Returns:
            str: Complete healing expression with variables substituted
        """
        if mind_level is None:
            mind_level = 1

        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return simplify_expression(self.heal_roll, variables)

    def get_min_heal(self, actor: Any, mind_level: int | None = 1) -> int:
        """
        Calculate the minimum possible healing for the spell.

        Args:
            actor: The character casting the spell
            mind_level: The spell level to use for scaling calculations

        Returns:
            int: Minimum possible healing amount
        """
        if mind_level is None:
            mind_level = 1

        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return parse_expr_and_assume_min_roll(
            substitute_variables(self.heal_roll, variables)
        )

    def get_max_heal(self, actor: Any, mind_level: int | None = 1) -> int:
        """
        Calculate the maximum possible healing for the spell.

        Args:
            actor: The character casting the spell
            mind_level: The spell level to use for scaling calculations

        Returns:
            int: Maximum possible healing amount
        """
        if mind_level is None:
            mind_level = 1

        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return parse_expr_and_assume_max_roll(
            substitute_variables(self.heal_roll, variables)
        )
