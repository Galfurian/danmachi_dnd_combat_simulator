"""Healing spell implementation."""

from typing import Any, Literal

from core.constants import (
    GLOBAL_VERBOSE_LEVEL,
    ActionCategory,
)
from core.utils import (
    cprint,
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    simplify_expression,
    substitute_variables,
)
from pydantic import Field

from actions.spells.base_spell import Spell


class SpellHeal(Spell):
    """Restorative spell that heals hit points and can apply beneficial effects.

    This class represents spells designed to restore health to allies. It includes
    attributes for healing expressions and optional beneficial effects, as well as
    methods for calculating and applying healing during combat.
    """

    action_type: Literal["SpellHeal"] = "SpellHeal"

    category: ActionCategory = ActionCategory.HEALING

    heal_roll: str = Field(
        description="The expression used to calculate healing amount.",
    )

    def model_post_init(self, _) -> None:
        """Validates fields after model initialization."""
        if not self.heal_roll or not isinstance(self.heal_roll, str):
            raise ValueError("heal_roll must be a non-empty string")
        # Remove spaces before and after '+' and '-'.
        self.heal_roll = self.heal_roll.replace(" +", "+").replace("+ ", "+")
        self.heal_roll = self.heal_roll.replace(" -", "-").replace("- ", "-")

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
        heal = self._spell_roll_and_describe(
            self.heal_roll,
            actor,
            rank,
        )

        # Apply healing to target (limited by max HP)
        actual_healing = target.heal(heal.value)

        # Apply the buffs.
        effects_applied, effects_not_applied = self._spell_apply_effects(
            actor=actor,
            target=target,
            rank=rank,
        )

        # Display the heal.
        msg = f"    🔮 {actor.colored_name} "
        msg += f"casts {self.colored_name} "
        msg += f"on {target.colored_name}"

        if GLOBAL_VERBOSE_LEVEL == 0:
            msg += f" healing {actual_healing} 💚"
            if effects_applied:
                msg += f" applying {self._effect_list_string(effects_applied)}"
            if effects_not_applied:
                msg += f" but fails to apply {self._effect_list_string(effects_not_applied)}"
            msg += "."
        elif GLOBAL_VERBOSE_LEVEL >= 1:
            if actual_healing != heal.value:
                msg += f" healing {actual_healing} 💚 (rolled {heal.value}, capped at max 💚)"
            else:
                msg += f" healing {actual_healing} 💚 → {heal.description}"
            msg += ".\n"
            if effects_applied:
                msg += f"        {target.colored_name} gains "
                msg += self._effect_list_string(effects_applied)
                msg += ".\n"

            if effects_not_applied:
                msg += f"        {target.colored_name} doesn't gain "
                msg += self._effect_list_string(effects_not_applied)
                msg += ".\n"
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
