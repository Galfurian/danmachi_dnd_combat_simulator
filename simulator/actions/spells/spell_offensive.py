"""
Spell offensive module for the simulator.

Defines offensive spells that deal damage to enemies, including
direct damage spells, area effects, and magical attacks.
"""

from typing import Any, Literal

from actions.spells.base_spell import BaseSpell
from combat.damage import DamageComponent
from core.constants import GLOBAL_VERBOSE_LEVEL, ActionCategory, BonusType
from core.utils import cprint
from pydantic import Field


class SpellOffensive(BaseSpell):
    """Offensive spell that deals damage through magical attacks.

    This class represents spells designed to inflict damage on targets using
    magical energy. It includes attributes for damage components, optional
    effects, and methods for calculating and applying damage during combat.
    """

    action_type: Literal["SpellOffensive"] = "SpellOffensive"

    category: ActionCategory = ActionCategory.OFFENSIVE

    damage: list[DamageComponent] = Field(
        description="List of damage components for this ability",
    )

    def model_post_init(self, _: Any) -> None:
        """Validates fields after model initialization."""
        if not self.damage or not isinstance(self.damage, list):
            raise ValueError("damage must be a non-empty list of DamageComponent")

    # ============================================================================
    # SPELL ATTACK METHODS
    # ============================================================================

    def cast_spell(self, actor: Any, target: Any, rank: int) -> bool:
        """Execute an offensive spell attack with complete combat resolution.

        Args:
            actor (Any):
                The character casting the spell.
            target (Any):
                The character being attacked.
            rank (int):
                The rank at which the spell is being cast.

        Returns:
            bool:
                True if spell was successfully cast (regardless of hit/miss).

        """
        from character.main import Character

        # Call the base class cast_spell to handle common checks.
        if not super().cast_spell(actor, target, rank):
            return False

        assert isinstance(actor, Character), "Actor must be a Character."

        # Calculate spell attack components
        spell_attack_bonus = actor.get_spell_attack_bonus(self.level)
        attack_modifier = actor.effects.get_base_modifier(BonusType.ATTACK)

        # Roll spell attack vs target AC
        attack = self._roll_attack(
            actor,
            str(spell_attack_bonus),
            attack_modifier,
        )
        assert attack.rolls, "Attack roll must contain at least one die roll."
        d20_roll = attack.rolls[0]
        is_crit = d20_roll == 20
        is_fumble = d20_roll == 1

        msg = f"    🎯 {actor.colored_name} casts [bold]{self.name}[/] on {target.colored_name}"

        # Handle fumble (always misses)
        if is_fumble:
            if GLOBAL_VERBOSE_LEVEL >= 1:
                msg += f" rolled ({attack.description}) [magenta]{attack.value}[/] vs AC [yellow]{target.AC}[/]"
            msg += " and [magenta]fumble![/]"
            cprint(msg)
            return True

        # Handle miss (unless critical hit)
        if attack.value < target.AC and not is_crit:
            if GLOBAL_VERBOSE_LEVEL >= 1:
                msg += f" rolled ({attack.description}) [red]{attack.value}[/] vs AC [yellow]{target.AC}[/]"
            msg += " and [red]miss![/]"
            cprint(msg)
            return True

        # Handle successful hit - calculate and apply damage
        total_damage, damage_details = self._spell_roll_damage_components(
            actor,
            target,
            rank,
            self.damage,
        )

        # Check if target was defeated
        is_dead = not target.is_alive()

        # Apply the buffs.
        effects_applied, effects_not_applied = self._spell_apply_effects(
            actor=actor,
            target=target,
            rank=rank,
        )

        # Display combat results with appropriate detail level
        if GLOBAL_VERBOSE_LEVEL == 0:
            msg += f" dealing {total_damage} damage"
            if effects_applied:
                msg += f" applying {self._effect_list_string(effects_applied)}"
            if effects_not_applied:
                msg += f" but fails to apply {self._effect_list_string(effects_not_applied)}"
            if is_dead:
                msg += f" defeating {target.colored_name}"
            msg += "."
        elif GLOBAL_VERBOSE_LEVEL >= 1:
            msg += f" rolled ({attack.description}) {attack.value} vs AC [yellow]{target.AC}[/] → "
            msg += "[magenta]crit![/]\n" if is_crit else "[green]hit![/]\n"
            msg += f"        Dealing {total_damage} damage to {target.colored_name} → "
            msg += " + ".join(damage_details) + ".\n"
            if effects_applied:
                msg += f"        {target.colored_name} gains "
                msg += self._effect_list_string(effects_applied)
                msg += ".\n"
            if effects_not_applied:
                msg += f"        {target.colored_name} doesn't gain "
                msg += self._effect_list_string(effects_not_applied)
                msg += ".\n"
            if is_dead:
                msg += f"        {target.colored_name} is defeated."
        cprint(msg)

        return True

    # ============================================================================
    # DAMAGE CALCULATION METHODS
    # ============================================================================

    def get_damage_expr(self, actor: Any, rank: int) -> str:
        """Get damage expression with variables substituted for display.

        Args:
            actor (Any):
                The character casting the spell.
            rank (int):
                The spell rank to use for variable substitution.

        Returns:
            str:
                Complete damage expression with variables substituted.

        """
        return super()._common_get_damage_expr(
            actor,
            self.damage,
            self.spell_get_variables(
                actor,
                rank,
            ),
        )

    def get_min_damage(self, actor: Any, rank: int) -> int:
        """Calculate the minimum possible damage for the spell.

        Args:
            actor (Any):
                The character casting the spell.
            rank (int):
                The spell rank to use for scaling calculations.

        Returns:
            int: Minimum possible damage (sum of all components' minimums).

        """
        return super()._common_get_min_damage(
            actor,
            self.damage,
            self.spell_get_variables(
                actor,
                rank,
            ),
        )

    def get_max_damage(self, actor: Any, rank: int) -> int:
        """Calculate the maximum possible damage for the spell.

        Args:
            actor (Any): The character casting the spell.
            rank (int): The spell rank to use for scaling calculations.

        Returns:
            int: Maximum possible damage (sum of all components' maximums).

        """
        return super()._common_get_max_damage(
            actor,
            self.damage,
            self.spell_get_variables(
                actor,
                rank,
            ),
        )
