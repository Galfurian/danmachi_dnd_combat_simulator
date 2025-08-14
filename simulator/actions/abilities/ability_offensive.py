"""Offensive abilities that deal damage to enemies."""

from typing import Any

from actions.abilities.base_ability import BaseAbility
from combat.damage import (
    DamageComponent,
    roll_damage_components_no_mind,
    roll_damage_components,
)
from core.constants import ActionCategory, ActionType, GLOBAL_VERBOSE_LEVEL
from core.constants import BonusType
from catchery import *
from core.utils import cprint
from effects.base_effect import Effect


class OffensiveAbility(BaseAbility):

    def __init__(
        self,
        name: str,
        action_type: ActionType,
        description: str,
        cooldown: int,
        maximum_uses: int,
        damage: list[DamageComponent],
        effect: Effect | None = None,
        target_expr: str = "",
        target_restrictions: list[str] | None = None,
        attack_roll: str = "",
    ):
        """Initialize a new OffensiveAbility.

        Args:
            name (str): Display name of the ability.
            action_type (ActionType): Action type (STANDARD, BONUS, REACTION, etc.).
            description (str): Flavor text describing what the ability does.
            cooldown (int): Turns to wait before reusing (0 = no cooldown).
            maximum_uses (int): Max uses per encounter/day (-1 = unlimited).
            damage (list[DamageComponent]): List of damage components to roll when used.
            effect (Effect | None): Optional effect applied to targets on successful hits.
            target_expr (str): Expression determining number of targets ("" = single target).
            target_restrictions (list[str] | None): Override default targeting if needed.

        Raises:
            ValueError: If name is empty or required parameters are invalid.
        """
        super().__init__(
            name,
            action_type,
            ActionCategory.OFFENSIVE,
            description,
            cooldown,
            maximum_uses,
            effect,
            target_expr,
            target_restrictions,
        )

        ctx = {"name": name}

        self.attack_roll: str = ensure_string(
            obj=attack_roll,
            name="OffensiveAbility.attack_roll",
            default="",
            context=ctx,
        )
        self.damage: list[DamageComponent] = ensure_list_of_type(
            values=damage,
            name="OffensiveAbility.damage",
            expected_type=DamageComponent,
            default=[],
            context=ctx,
        )

    def execute(self, actor: Any, target: Any) -> bool:
        """Execute this offensive ability against a target.

        Args:
            actor (Any): The character using the ability.
            target (Any): The character being damaged.

        Returns:
            bool: True if ability was executed successfully, False on system errors.
        """
        # =====================================================================
        # 1. VALIDATION AND PREPARATION
        # =====================================================================

        if not self._validate_character(actor):
            return False
        if not self._validate_character(target):
            return False
        # Validate cooldown.
        if actor.is_on_cooldown(self):
            log_critical(
                f"{actor.name} cannot use {self.name} yet, still on cooldown.",
                {"actor": actor.name, "ability": self.name},
            )
            return False

        actor_str, target_str = self._get_display_strings(actor, target)

        # =====================================================================
        # 2. ATTACK ROLL (TO-HIT, CRIT, FUMBLE)
        # =====================================================================
        # If the ability requires an attack roll, perform it. Otherwise, auto-hit.
        # This assumes a method self.requires_attack_roll() and self.roll_to_hit() exist or are inherited.
        is_critical = False
        is_fumble = False
        hit = True
        attack_roll_msg = ""
        if self.requires_attack_roll():
            hit, roll, is_critical, is_fumble, attack_roll_msg = self.roll_to_hit(
                actor, target
            )
            if not hit:
                msg = f"    ❌ {actor_str} uses [bold blue]{self.name}[/] on {target_str} but misses!"
                if attack_roll_msg:
                    msg += f" ({attack_roll_msg})"
                cprint(msg)
                return True

        # =====================================================================
        # 3. DAMAGE CALCULATION (INCLUDING CRIT/FUMBLE MODIFIERS)
        # =====================================================================
        # If fumble, set damage to 0. If crit, double damage.
        if is_fumble:
            base_damage = 0
            base_damage_details = ["Fumble: no damage"]
        elif is_critical:
            # Roll damage twice and sum for crit
            dmg1, details1 = roll_damage_components_no_mind(actor, target, self.damage)
            dmg2, details2 = roll_damage_components_no_mind(actor, target, self.damage)
            base_damage = dmg1 + dmg2
            base_damage_details = details1 + details2
        else:
            base_damage, base_damage_details = roll_damage_components_no_mind(
                actor, target, self.damage
            )

        # =============================
        # 3b. On-Hit Triggers & Bonus Damage from Effects (parity with BaseAttack)
        # =============================
        trigger_damage_bonuses, trigger_effects_with_levels, consumed_triggers = (
            self._trigger_on_hit_effects(actor, target)
        )
        for effect, mind_level in trigger_effects_with_levels:
            if effect.can_apply(actor, target):
                target.effects_module.add_effect(actor, effect, mind_level)

        bonus_damage, bonus_damage_details = self._roll_bonus_damage(actor, target)
        total_damage = (
            base_damage + bonus_damage + sum(trigger_damage_bonuses)
        )  # trigger_damage_bonuses is a list of ints
        damage_details = base_damage_details + bonus_damage_details

        # =============================
        # 4b. On-Hit Trigger Messaging (parity with BaseAttack)
        # =============================
        for trigger in consumed_triggers:
            trigger_msg = f"    ⚡ {actor_str}'s [bold yellow]{getattr(trigger, 'name', str(trigger))}[/] activates!"
            cprint(trigger_msg)

        # =====================================================================
        # 5. EFFECT APPLICATION
        # =====================================================================
        is_dead = not target.is_alive()
        effect_applied = self._common_apply_effect(actor, target, self.effect)

        # =====================================================================
        # 6. RESULT DISPLAY AND LOGGING
        # =====================================================================
        msg = f"    🔥 {actor_str} uses [bold blue]{self.name}[/] on {target_str}"
        if attack_roll_msg:
            msg += f" ({attack_roll_msg})"

        if GLOBAL_VERBOSE_LEVEL == 0:
            msg += f" dealing {total_damage} damage"
            if is_fumble:
                msg += " (fumble!)"
            elif is_critical:
                msg += " (critical hit!)"
            if is_dead:
                msg += f" defeating {target_str}"
            elif self.effect:
                if effect_applied:
                    msg += f" and applying"
                else:
                    msg += f" and failing to apply"
                msg += f" [bold yellow]{self.effect.name}[/]"
            msg += "."
        elif GLOBAL_VERBOSE_LEVEL >= 1:
            if damage_details:
                msg += f" dealing {total_damage} damage → "
                msg += " + ".join(damage_details)
            else:
                msg += f" dealing {total_damage} damage"
            if is_fumble:
                msg += " (fumble!)"
            elif is_critical:
                msg += " (critical hit!)"
            msg += ".\n"

            if is_dead:
                msg += f"        {target_str} is defeated."
            elif self.effect:
                if effect_applied:
                    msg += f"        {target_str} is affected by"
                else:
                    msg += f"        {target_str} resists"
                msg += f" [bold yellow]{self.effect.name}[/]."

        cprint(msg)

        # =====================================================================
        # 7. RETURN
        # =====================================================================
        return True

    # =========================================================================
    # BONUS DAMAGE AND TRIGGER METHODS (for full parity with BaseAttack)
    # =========================================================================
    def _roll_bonus_damage(self, actor: Any, target: Any) -> tuple[int, list[str]]:
        """Roll any bonus damage from effects (parity with BaseAttack)."""
        all_damage_modifiers = actor.effects_module.get_damage_modifiers()
        return roll_damage_components_no_mind(actor, target, all_damage_modifiers)

    def _trigger_on_hit_effects(self, actor: Any, target: Any):
        """Trigger on-hit effects and return (trigger_damage_bonuses, trigger_effects_with_levels, consumed_triggers)."""
        # This mirrors BaseAttack's use of effects_module.trigger_on_hit_effects
        return actor.effects_module.trigger_on_hit_effects(target)

    def requires_attack_roll(self) -> bool:
        """Return True if this ability requires an attack roll (i.e., attack_roll is set)."""
        return bool(getattr(self, "attack_roll", ""))

    def roll_to_hit(self, actor: Any, target: Any):
        """Perform an attack roll using the same logic as BaseAttack."""
        # Use _roll_attack_with_crit from BaseAction
        attack_modifier = actor.effects_module.get_modifier(
            getattr(BonusType, "ATTACK", "ATTACK")
        )
        attack_total, attack_roll_desc, d20_roll = self._roll_attack_with_crit(
            actor,
            self.attack_roll,
            attack_modifier if isinstance(attack_modifier, list) else [attack_modifier],
        )
        is_critical = d20_roll == 20
        is_fumble = d20_roll == 1
        hit = (attack_total >= getattr(target, "AC", 0)) or is_critical
        msg = f"rolled ({attack_roll_desc}) {attack_total} vs AC {getattr(target, 'AC', '?')}"
        return hit, attack_total, is_critical, is_fumble, msg

    # ============================================================================
    # DAMAGE CALCULATION METHODS
    # ============================================================================

    def get_damage_expr(self, actor: Any) -> str:
        """Returns the damage expression with variables substituted.

        Args:
            actor (Any): The character using the ability.

        Returns:
            str: Complete damage expression with variables replaced by values.
        """
        return super()._common_get_damage_expr(actor, self.damage)

    def get_min_damage(self, actor: Any) -> int:
        """Returns the minimum possible damage value for the ability.

        Args:
            actor (Any): The character using the ability.

        Returns:
            int: Minimum total damage across all damage components.
        """
        return super()._common_get_min_damage(actor, self.damage)

    def get_max_damage(self, actor: Any) -> int:
        """Returns the maximum possible damage value for the ability.

        Args:
            actor (Any): The character using the ability.

        Returns:
            int: Maximum total damage across all damage components.
        """
        return super()._common_get_max_damage(actor, self.damage)
