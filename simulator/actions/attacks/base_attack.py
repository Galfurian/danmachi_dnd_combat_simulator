from typing import Any

from actions.base_action import BaseAction
from combat.damage import (
    DamageComponent,
    roll_damage_components,
    roll_damage_components_no_mind,
)
from core.constants import (
    ActionCategory,
    ActionType,
    BonusType,
    GLOBAL_VERBOSE_LEVEL,
    get_effect_color,
)
from core.utils import debug, cprint
from effects.base_effect import Effect
from pydantic import Field


class BaseAttack(BaseAction):
    """Base class for all attack actions in the combat system.

    This class provides a foundation for implementing various types of attacks,
    such as weapon attacks and natural attacks. It includes shared functionality
    like damage calculation, targeting, and serialization, while allowing
    subclasses to extend or override specific behavior.
    """

    category: ActionCategory = ActionCategory.OFFENSIVE

    attack_roll: str = Field(
        description="The attack roll expression (e.g., '1d20 + 5')",
    )
    damage: list[DamageComponent] = Field(
        description="List of damage components for the attack",
    )
    effect: Effect | None = Field(
        default=None,
        description="Effect applied by this attack (if any)",
    )

    # ============================================================================
    # COMBAT EXECUTION METHODS
    # ============================================================================

    def execute(self, actor: Any, target: Any) -> bool:
        """Execute this attack against a target.

        Args:
            actor (Any): The character performing the attack.
            target (Any): The character being attacked.

        Returns:
            bool: True if attack was executed successfully, False on validation errors.
        """
        # =============================
        # 1. Validation and Setup
        # =============================
        if not self._validate_character(actor):
            return False
        if not self._validate_character(target):
            return False
        actor_str, target_str = self._get_display_strings(actor, target)
        debug(f"{actor.name} attempts a {self.name} on {target.name}.")

        # =============================
        # 2. Cooldown and Requirements
        # =============================
        if actor.is_on_cooldown(self):
            print(
                f"Action {self.name} is on cooldown",
                {"action": self.name, "actor": actor.name},
            )
            return False

        # =============================
        # 3. Attack Roll Calculation
        # =============================
        attack_modifier = actor.effects_module.get_modifier(BonusType.ATTACK)
        attack_total, attack_roll_desc, d20_roll = self._roll_attack_with_crit(
            actor, self.attack_roll, attack_modifier
        )
        is_crit = d20_roll == 20
        is_fumble = d20_roll == 1
        msg = f"    🎯 {actor_str} attacks {target_str} with [bold blue]{self.name}[/]"

        # =============================
        # 4. Miss/Fumble Handling
        # =============================
        if is_fumble:
            if GLOBAL_VERBOSE_LEVEL >= 1:
                msg += f" rolled ({attack_roll_desc}) [magenta]{attack_total}[/] vs AC [yellow]{target.AC}[/]"
            msg += " and [magenta]fumble![/]"
            cprint(msg)
            return True
        if attack_total < target.AC and not is_crit:
            if GLOBAL_VERBOSE_LEVEL >= 1:
                msg += f" rolled ({attack_roll_desc}) [red]{attack_total}[/] vs AC [yellow]{target.AC}[/]"
            msg += " and [red]miss![/]"
            cprint(msg)
            return True

        # =============================
        # 5. Damage Calculation (Base)
        # =============================
        base_damage, base_damage_details = roll_damage_components_no_mind(
            actor, target, self.damage
        )
        if is_crit:
            base_damage *= 2

        # =============================
        # 6. On-Hit Triggers & Effects
        # =============================
        trigger_damage_bonuses, trigger_effects_with_levels, consumed_triggers = (
            actor.effects_module.trigger_on_hit_effects(target)
        )
        for effect, mind_level in trigger_effects_with_levels:
            if effect.can_apply(actor, target):
                target.effects_module.add_effect(actor, effect, mind_level)

        # =============================
        # 7. Bonus Damage from Effects
        # =============================
        all_damage_modifiers = (
            actor.effects_module.get_damage_modifiers() + trigger_damage_bonuses
        )
        bonus_damage, bonus_damage_details = roll_damage_components(
            actor, target, all_damage_modifiers
        )
        total_damage = base_damage + bonus_damage
        damage_details = base_damage_details + bonus_damage_details

        # =============================
        # 8. Outcome Messaging & Effects
        # =============================
        is_dead = not target.is_alive()
        if GLOBAL_VERBOSE_LEVEL == 0:
            msg += f" dealing {total_damage} damage"
            if is_dead:
                msg += f" defeating {target_str}"
            elif self.effect:
                if self._common_apply_effect(actor, target, self.effect):
                    msg += f" and applying"
                else:
                    msg += f" and failing to apply"
                msg += f" [{get_effect_color(self.effect)}]{self.effect.name}[/]"
            msg += "."
        elif GLOBAL_VERBOSE_LEVEL >= 1:
            msg += f" rolled ({attack_roll_desc}) {attack_total} vs AC [yellow]{target.AC}[/] and "
            msg += f"[magenta]crit![/]\n" if is_crit else "[green]hit![/]\n"
            msg += f"        Dealing {total_damage} damage to {target_str} → "
            msg += " + ".join(damage_details) + ".\n"
            if is_dead:
                msg += f"        {target_str} is defeated."
            elif self.effect:
                if self._common_apply_effect(actor, target, self.effect):
                    msg += f"        {target_str} is affected by"
                else:
                    msg += f"        {target_str} is not affected by"
                msg += f" [{get_effect_color(self.effect)}]{self.effect.name}[/]."

        # =============================
        # 9. On-Hit Trigger Messaging
        # =============================
        for trigger in consumed_triggers:
            trigger_msg = f"    ⚡ {actor_str}'s [bold][{get_effect_color(trigger)}]{trigger.name}[/][/] activates!"
            cprint(trigger_msg)

        cprint(msg)
        return True

    # ============================================================================
    # DAMAGE CALCULATION METHODS
    # ============================================================================

    def get_damage_expr(self, actor: Any) -> str:
        """Returns the damage expression with variables substituted.

        Args:
            actor (Any): The character performing the action.

        Returns:
            str: Complete damage expression with variables replaced by values.
        """
        return super()._common_get_damage_expr(actor, self.damage)

    def get_min_damage(self, actor: Any) -> int:
        """Returns the minimum possible damage value for the attack.

        Args:
            actor (Any): The character performing the action.

        Returns:
            int: Minimum total damage across all damage components.
        """
        return super()._common_get_min_damage(actor, self.damage)

    def get_max_damage(self, actor: Any) -> int:
        """Returns the maximum possible damage value for the attack.

        Args:
            actor (Any): The character performing the action.

        Returns:
            int: Maximum total damage across all damage components.
        """
        return super()._common_get_max_damage(actor, self.damage)


def deserialze_attack(data: dict[str, Any]) -> BaseAttack | None:
    """Deserialize a dictionary into the appropriate BaseAttack subclass.

    Args:
        data (dict[str, Any]): The dictionary representation of the attack.

    Returns:
        BaseAttack: An instance of the appropriate BaseAttack subclass.

    Raises:
        ValueError: If the action type is unknown or missing.
    """

    from actions.attacks.weapon_attack import WeaponAttack
    from actions.attacks.natural_attack import NaturalAttack

    if "class" not in data:
        raise ValueError("Missing 'class' in attack data")

    if data["class"] == "WeaponAttack":
        return WeaponAttack(**data)
    if data["class"] == "NaturalAttack":
        return NaturalAttack(**data)

    return None
