"""Offensive spell attack implementation."""

from logging import debug
from typing import Any

from actions.spells.base_spell import Spell
from combat.damage import DamageComponent, roll_damage_components
from core.constants import (
    ActionCategory,
    ActionType,
    BonusType,
    GLOBAL_VERBOSE_LEVEL,
    get_effect_color,
)
from core.error_handling import (
    log_error,
    log_warning,
    log_critical,
    ensure_list_of_type,
)
from core.utils import (
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    substitute_variables,
    cprint,
)
from effects.effect import Effect


class SpellAttack(Spell):
    """Offensive spell that deals damage through magical attacks.

    This class represents spells designed to inflict damage on targets using
    magical energy. It includes attributes for damage components, optional
    effects, and methods for calculating and applying damage during combat.
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
        damage: list[DamageComponent],
        effect: Effect | None = None,
        target_expr: str = "",
        requires_concentration: bool = False,
        target_restrictions: list[str] | None = None,
    ):
        """Initialize a new SpellAttack.
        
        Args:
            name (str): Display name of the spell.
            type (ActionType): Action type (ACTION, BONUS_ACTION, REACTION, etc.).
            description (str): Flavor text describing the spell's appearance/effects.
            cooldown (int): Turns to wait before reusing (0 = no cooldown).
            maximum_uses (int): Max uses per encounter/day (-1 = unlimited).
            level (int): Base spell level determining scaling and prerequisites.
            mind_cost (list[int]): List of mind point costs per casting level.
            damage (list[DamageComponent]): List of damage components with scaling expressions.
            effect (Effect | None): Optional effect applied on successful spell attacks.
            target_expr (str): Expression for multi-target spells.
            requires_concentration (bool): Whether spell needs ongoing mental focus.
            target_restrictions (list[str] | None): Override default targeting restrictions.
        
        Raises:
            ValueError: If damage list is empty or contains invalid components.
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
                ActionCategory.OFFENSIVE,
                target_expr,
                requires_concentration,
                target_restrictions,
            )

            # Validate damage components using helper
            if not damage or not isinstance(damage, list) or len(damage) == 0:
                log_critical(
                    f"SpellAttack {name} must have at least one damage component",
                    {"name": name, "damage": damage},
                )
                raise ValueError(
                    f"SpellAttack {name} must have at least one damage component"
                )

            self.damage = ensure_list_of_type(
                damage,
                DamageComponent,
                "damage components",
                context={"name": name},
            )

            # Validate optional effect
            if effect is not None and not isinstance(effect, Effect):
                log_warning(
                    f"SpellAttack {name} effect must be Effect or None, got: {type(effect).__name__}, setting to None",
                    {"name": name, "effect_type": type(effect).__name__},
                )
                effect = None

            self.effect = effect

        except Exception as e:
            log_critical(
                f"Error initializing SpellAttack {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

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
                msg += f" and applying [{get_effect_color(self.effect)}]{self.effect.name}[/]"
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
                msg += f"[{get_effect_color(self.effect)}]{self.effect.name}[/]."
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
