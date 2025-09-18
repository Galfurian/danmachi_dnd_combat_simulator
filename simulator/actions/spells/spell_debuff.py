"""Detrimental spell debuff implementation."""

from typing import Any

from combat.damage import DamageComponent
from core.constants import ActionCategory, BonusType
from core.utils import (
    cprint,
    substitute_variables,
)
from effects.base_effect import Effect
from pydantic import Field

from actions.spells.base_spell import Spell


class SpellDebuff(Spell):
    """Detrimental spell that weakens enemies with negative effects.

    This class represents spells designed to apply debuffs or negative effects
    to enemies. It includes attributes for required effects and methods for
    applying those effects during combat.
    """

    category: ActionCategory = ActionCategory.DEBUFF

    # Assign the effect to the spell.
    effect: Effect = Field(
        description="The beneficial effect that this buff spell applies.",
    )

    # ============================================================================
    # DEBUFF SPELL METHODS
    # ============================================================================

    def cast_spell(self, actor: Any, target: Any, mind_level: int) -> bool:
        """Execute a debuff spell with automatic application and optional saves.

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

        # Apply the detrimental effect
        effect_applied = False
        save_result = None
        if self.effect:
            effect_applied = self._common_apply_effect(
                actor, target, self.effect, mind_level
            )

            # Check if target made a successful save (effect-dependent)
            if hasattr(self.effect, "save_type") and hasattr(self.effect, "save_dc"):
                # This would be handled within apply_effect, but we can track the result
                # for better feedback messages
                pass

        # Display debuff results with save information
        msg = f"    🔮 {actor_str} casts [bold]{self.name}[/] on {target_str} "
        if effect_applied:
            msg += f"applying [{self.effect.color}]{self.effect.name}[/]"
        else:
            msg += f"but fails to apply [{self.effect.color}]{self.effect.name}[/]"
            if save_result:
                msg += " (saved)"
        msg += "."

        cprint(msg)

        return True

    # ============================================================================
    # EFFECT ANALYSIS METHODS
    # ============================================================================

    def get_modifier_expressions(
        self, actor: Any, mind_level: int = 1
    ) -> dict[BonusType, str]:
        """Get modifier expressions with variables substituted for display.

        Args:
            actor (Any): The character casting the spell.
            mind_level (int | None): The spell level to use for MIND variable substitution.

        Returns:
            dict[BonusType, str]: Dictionary mapping bonus types to their expressions.

        """
        if mind_level is None:
            mind_level = 1

        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        expressions: dict[BonusType, str] = {}

        # Handle effects that have modifiers (ModifierEffect)
        if hasattr(self.effect, "modifiers"):
            modifiers = getattr(self.effect, "modifiers", [])
            for modifier in modifiers:
                bonus_type = modifier.bonus_type
                value = modifier.value
                if isinstance(value, DamageComponent):
                    expressions[bonus_type] = substitute_variables(
                        value.damage_roll, variables
                    )
                elif isinstance(value, str):
                    expressions[bonus_type] = substitute_variables(value, variables)
                else:
                    expressions[bonus_type] = str(value)

        return expressions
