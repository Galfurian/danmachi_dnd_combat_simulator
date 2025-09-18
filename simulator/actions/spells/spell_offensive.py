"""Offensive spell attack implementation."""

from typing import Any

from combat.damage import DamageComponent, roll_damage_components
from core.constants import (
    GLOBAL_VERBOSE_LEVEL,
    ActionCategory,
    BonusType,
)
from core.utils import cprint
from pydantic import Field, model_validator

from actions.spells.base_spell import Spell


class SpellOffensive(Spell):
    """Offensive spell that deals damage through magical attacks.

    This class represents spells designed to inflict damage on targets using
    magical energy. It includes attributes for damage components, optional
    effects, and methods for calculating and applying damage during combat.
    """

    category: ActionCategory = ActionCategory.OFFENSIVE

    damage: list[DamageComponent] = Field(
        description="List of damage components for this ability",
    )

    @model_validator(mode="after")
    def validate_fields(self) -> "SpellOffensive":
        """Validates fields after model initialization."""
        if not self.damage or not isinstance(self.damage, list):
            raise ValueError("damage must be a non-empty list of DamageComponent")
        return self

    # ============================================================================
    # SPELL ATTACK METHODS
    # ============================================================================

    def cast_spell(self, actor: Any, target: Any, mind_level: int) -> bool:
        """Execute an offensive spell attack with complete combat resolution.

        Args:
            actor (Any): The character casting the spell.
            target (Any): The character being attacked.
            mind_level (int): The spell level to cast at (affects cost and damage).

        Returns:
            bool: True if spell was successfully cast (regardless of hit/miss).

        """
        # Call the base class cast_spell to handle common checks.
        if super().cast_spell(actor, target, mind_level) is False:
            return False

        # Handle concentration requirements
        if self.requires_concentration:
            actor.concentration_module.break_concentration()

        # Format character strings for output.
        actor_str, target_str = self._get_display_strings(actor, target)

        # Calculate spell attack components
        spell_attack_bonus = actor.get_spell_attack_bonus(self.level)
        attack_modifier = actor.effects_module.get_modifier(BonusType.ATTACK)

        # Roll spell attack vs target AC
        attack_total, attack_roll_desc, d20_roll = self._roll_attack_with_crit(
            actor, spell_attack_bonus, attack_modifier
        )

        # Determine special outcomes
        is_crit = d20_roll == 20
        is_fumble = d20_roll == 1

        msg = f"    🎯 {actor_str} casts [bold]{self.name}[/] on {target_str}"

        # Handle fumble (always misses)
        if is_fumble:
            if GLOBAL_VERBOSE_LEVEL >= 1:
                msg += f" rolled ({attack_roll_desc}) [magenta]{attack_total}[/] vs AC [yellow]{target.AC}[/]"
            msg += " and [magenta]fumble![/]"
            cprint(msg)
            return True

        # Handle miss (unless critical hit)
        if attack_total < target.AC and not is_crit:
            if GLOBAL_VERBOSE_LEVEL >= 1:
                msg += f" rolled ({attack_roll_desc}) [red]{attack_total}[/] vs AC [yellow]{target.AC}[/]"
            msg += " and [red]miss![/]"
            cprint(msg)
            return True

        # Handle successful hit - calculate and apply damage
        damage_components = [(component, mind_level) for component in self.damage]
        total_damage, damage_details = roll_damage_components(
            actor, target, damage_components
        )

        # Check if target was defeated
        is_dead = not target.is_alive()

        # Apply optional effect on successful hit
        effect_applied = False
        if self.effect:
            effect_applied = self._common_apply_effect(
                actor, target, self.effect, mind_level
            )

        # Display combat results with appropriate detail level
        if GLOBAL_VERBOSE_LEVEL == 0:
            msg += f" dealing {total_damage} damage"
            if is_dead:
                msg += f" defeating {target_str}"
            elif effect_applied and self.effect:
                msg += f" and applying [{self.effect.color}]{self.effect.name}[/]"
            msg += "."
        elif GLOBAL_VERBOSE_LEVEL >= 1:
            msg += f" rolled ({attack_roll_desc}) {attack_total} vs AC [yellow]{target.AC}[/] → "
            msg += "[magenta]crit![/]\n" if is_crit else "[green]hit![/]\n"
            msg += f"        Dealing {total_damage} damage to {target_str} → "
            msg += " + ".join(damage_details) + ".\n"
            if is_dead:
                msg += f"        {target_str} is defeated."
            elif effect_applied and self.effect:
                msg += f"        {target_str} is affected by "
                msg += f"[{self.effect.color}]{self.effect.name}[/]."
        cprint(msg)

        return True

    # ============================================================================
    # DAMAGE CALCULATION METHODS
    # ============================================================================

    def get_damage_expr(self, actor: Any, mind_level: int = 1) -> str:
        """Get damage expression with variables substituted for display.

        Args:
            actor (Any): The character casting the spell.
            mind_level (int): The spell level to use for MIND variable substitution.

        Returns:
            str: Complete damage expression with variables substituted.

        """
        return super()._common_get_damage_expr(actor, self.damage, {"MIND": mind_level})

    def get_min_damage(self, actor: Any, mind_level: int = 1) -> int:
        """Calculate the minimum possible damage for the spell.

        Args:
            actor (Any): The character casting the spell.
            mind_level (int): The spell level to use for scaling calculations.

        Returns:
            int: Minimum possible damage (sum of all components' minimums).

        """
        return super()._common_get_min_damage(actor, self.damage, {"MIND": mind_level})

    def get_max_damage(self, actor: Any, mind_level: int = 1) -> int:
        """Calculate the maximum possible damage for the spell.

        Args:
            actor (Any): The character casting the spell.
            mind_level (int): The spell level to use for scaling calculations.

        Returns:
            int: Maximum possible damage (sum of all components' maximums).

        """
        return super()._common_get_max_damage(actor, self.damage, {"MIND": mind_level})
