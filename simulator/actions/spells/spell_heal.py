"""Healing spell implementation."""

from logging import debug
from typing import Any

from actions.spells.base_spell import Spell
from core.constants import (
    ActionCategory,
    ActionType,
    GLOBAL_VERBOSE_LEVEL,
    get_effect_color,
)
from core.utils import (
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    roll_and_describe,
    simplify_expression,
    substitute_variables,
    cprint,
)
from effects.base_effect import Effect, ensure_effect
from pydantic import Field


class SpellHeal(Spell):
    """Restorative spell that heals hit points and can apply beneficial effects.

    This class represents spells designed to restore health to allies. It includes
    attributes for healing expressions and optional beneficial effects, as well as
    methods for calculating and applying healing during combat.
    """
    
    category: ActionCategory = ActionCategory.HEALING

    heal_roll: str = Field(
        description="The expression used to calculate healing amount.",
    )
    effect: Effect | None = Field(
        None,
        description="An optional beneficial effect that this healing spell applies.",
    )

    # ============================================================================
    # HEALING SPELL METHODS
    # ============================================================================

    def cast_spell(self, actor: Any, target: Any, mind_level: int) -> bool:
        """Execute a healing spell with automatic success and beneficial effects.

        Args:
            actor (Any): The character casting the spell.
            target (Any): The character targeted by the spell.
            mind_level (int): The spell level to cast at (affects cost and power).

        Returns:
            bool: True if spell was cast successfully, False on failure.
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

    def get_heal_expr(self, actor: Any, mind_level: int = 1) -> str:
        """Get healing expression with variables substituted for display.

        Args:
            actor (Any): The character casting the spell.
            mind_level (int | None): The spell level to use for MIND variable substitution.

        Returns:
            str: Complete healing expression with variables substituted.
        """
        if mind_level is None:
            mind_level = 1

        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return simplify_expression(self.heal_roll, variables)

    def get_min_heal(self, actor: Any, mind_level: int = 1) -> int:
        """Calculate the minimum possible healing for the spell.

        Args:
            actor (Any): The character casting the spell.
            mind_level (int | None): The spell level to use for scaling calculations.

        Returns:
            int: Minimum possible healing amount.
        """
        if mind_level is None:
            mind_level = 1

        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return parse_expr_and_assume_min_roll(
            substitute_variables(self.heal_roll, variables)
        )

    def get_max_heal(self, actor: Any, mind_level: int = 1) -> int:
        """Calculate the maximum possible healing for the spell.

        Args:
            actor (Any): The character casting the spell.
            mind_level (int | None): The spell level to use for scaling calculations.

        Returns:
            int: Maximum possible healing amount.
        """
        if mind_level is None:
            mind_level = 1

        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return parse_expr_and_assume_max_roll(
            substitute_variables(self.heal_roll, variables)
        )
