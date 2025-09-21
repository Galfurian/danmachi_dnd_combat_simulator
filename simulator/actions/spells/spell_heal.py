"""Healing spell implementation."""

from typing import Any

from core.constants import (
    GLOBAL_VERBOSE_LEVEL,
    ActionCategory,
)
from core.utils import (
    cprint,
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    roll_and_describe,
    simplify_expression,
    substitute_variables,
)
from pydantic import Field, model_validator

from actions.spells.base_spell import Spell


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

    @model_validator(mode="after")
    def validate_fields(self) -> "SpellHeal":
        """Validates fields after model initialization."""
        if not self.heal_roll or not isinstance(self.heal_roll, str):
            raise ValueError("heal_roll must be a non-empty string")
        # Remove spaces before and after '+' and '-'.
        self.heal_roll = self.heal_roll.replace(" +", "+").replace("+ ", "+")
        self.heal_roll = self.heal_roll.replace(" -", "-").replace("- ", "-")
        return self

    # ============================================================================
    # HEALING SPELL METHODS
    # ============================================================================

    def cast_spell(
        self,
        actor: Any,
        target: Any,
        rank: int,
    ) -> bool:
        """
        Execute a healing spell with automatic success and beneficial effects.

        Args:
            actor (Any):
                The character casting the spell.
            target (Any):
                The character targeted by the spell.
            rank (int):
                The spell level to cast at (affects cost and power).

        Returns:
            bool:
                True if spell was cast successfully, False on failure.

        """
        # Call the base class cast_spell to handle common checks.
        if not super().cast_spell(actor, target, rank):
            return False

        # Calculate healing with level scaling
        outcome = self._spell_roll_and_describe(
            self.heal_roll,
            actor,
            rank,
        )

        # Apply healing to target (limited by max HP)
        actual_healed = target.heal(outcome.value)

        # Apply optional effect
        effect_applied = self._spell_apply_effect(actor, target, rank)

        # Display healing results
        msg = f"    ✳️ {actor.colored_name} casts [bold]{self.name}[/] on {target.colored_name}"
        msg += f" healing for [bold green]{actual_healed}[/]"
        if GLOBAL_VERBOSE_LEVEL >= 1:
            msg += f" ({outcome.description})"
        if effect_applied and self.effect:
            msg += f" and applying [{self.effect.color}]{self.effect.name}[/]"
        elif self.effect and not effect_applied:
            msg += f" but failing to apply [{self.effect.color}]{self.effect.name}[/]"
        msg += "."
        cprint(msg)

        return True

    # ============================================================================
    # HEALING CALCULATION METHODS
    # ============================================================================

    def get_heal_expr(self, actor: Any, rank: int) -> str:
        """
        Get healing expression with variables substituted for display.

        Args:
            actor (Any):
                The character casting the spell.
            rank (int):
                The spell level to use for MIND variable substitution.

        Returns:
            str:
                Complete healing expression with variables substituted.

        """
        return simplify_expression(
            self.heal_roll,
            self.spell_get_variables(
                actor,
                rank,
            ),
        )

    def get_min_heal(self, actor: Any, rank: int) -> int:
        """Calculate the minimum possible healing for the spell.

        Args:
            actor (Any):
                The character casting the spell.
            rank (int):
                The spell level to use for scaling calculations.

        Returns:
            int:
                Minimum possible healing amount.

        """
        return parse_expr_and_assume_min_roll(
            substitute_variables(
                self.heal_roll,
                self.spell_get_variables(
                    actor,
                    rank,
                ),
            )
        )

    def get_max_heal(self, actor: Any, rank: int) -> int:
        """Calculate the maximum possible healing for the spell.

        Args:
            actor (Any):
                The character casting the spell.
            rank (int):
                The spell level to use for scaling calculations.

        Returns:
            int:
                Maximum possible healing amount.

        """
        return parse_expr_and_assume_max_roll(
            substitute_variables(
                self.heal_roll,
                self.spell_get_variables(
                    actor,
                    rank,
                ),
            )
        )
