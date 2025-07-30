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
from catchery import ensure_list_of_type, ensure_string, log_critical, log_warning
from core.utils import debug, cprint
from effects.base_effect import Effect


class BaseAttack(BaseAction):
    """Base class for all attack actions in the combat system.

    This class provides a foundation for implementing various types of attacks,
    such as weapon attacks and natural attacks. It includes shared functionality
    like damage calculation, targeting, and serialization, while allowing
    subclasses to extend or override specific behavior.
    """

    def __init__(
        self,
        name: str,
        action_type: ActionType,
        description: str,
        cooldown: int,
        maximum_uses: int,
        hands_required: int,
        attack_roll: str,
        damage: list[DamageComponent],
        effect: Effect | None = None,
        target_restrictions: list[str] | None = None,
    ):
        """Initialize a new BaseAttack.

        Args:
            name (str): The display name of the attack.
            type (ActionType): The type of action (usually ActionType.ATTACK).
            description (str): Description of what the attack does.
            cooldown (int): Turns to wait before reusing (0 = no cooldown).
            maximum_uses (int): Max uses per encounter/day (-1 = unlimited).
            hands_required (int): Number of hands needed.
            attack_roll (str): Attack bonus expression.
            damage (list[DamageComponent]): List of damage components.
            effect (Effect | None): Optional effect applied on successful hits.
            target_restrictions (list[str] | None): Override default offensive targeting if needed.

        Raises:
            ValueError: If name is empty or type/category are invalid.
        """
        try:
            super().__init__(
                name,
                action_type,
                ActionCategory.OFFENSIVE,
                description,
                cooldown,
                maximum_uses,
                target_restrictions,
            )

            # Validate attack_roll using helper
            self.attack_roll: str = ensure_string(
                attack_roll, "attack roll", "", {"name": name}
            )

            # Validate damage list using helper
            self.damage = ensure_list_of_type(
                damage,
                "damage components",
                DamageComponent,
                [],
                validator=lambda x: isinstance(x, DamageComponent),
                context={"name": name},
            )

            # Validate effect
            if effect is not None and not isinstance(effect, Effect):
                log_warning(
                    f"Attack {name} effect must be Effect or None, got: {effect.__class__.__name__}, setting to None",
                    {"name": name, "effect": effect},
                )
                effect = None

            self.effect: Effect | None = effect

        except Exception as e:
            log_critical(
                f"Error initializing BaseAttack {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
                True,
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
            log_warning(
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

    # ============================================================================
    # SERIALIZATION METHODS
    # ============================================================================

    def to_dict(self) -> dict[str, Any]:
        """Convert attack to dictionary representation using AttackSerializer.

        Returns:
            dict[str, Any]: Dictionary representation of the attack.
        """
        from actions.attacks.attack_serializer import AttackSerializer

        return AttackSerializer.serialize(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "BaseAttack":
        """Create BaseAttack from dictionary data using AttackDeserializer.

        Args:
            data (dict[str, Any]): Dictionary containing attack configuration data.

        Returns:
            BaseAttack: Configured attack instance.
        """
        from actions.attacks.attack_serializer import AttackDeserializer

        return AttackDeserializer._deserialize_base_attack(data)
