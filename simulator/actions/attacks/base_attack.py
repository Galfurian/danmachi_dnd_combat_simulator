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
    apply_character_type_color,
    get_effect_color,
    is_oponent,
)
from core.error_handling import (
    log_error,
    log_warning,
    log_critical,
    ensure_non_negative_int,
    ensure_string,
    ensure_list_of_type,
    safe_get_attribute,
    validate_required_object,
)
from core.utils import (
    debug,
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    substitute_variables,
    cprint,
)
from effects.effect import Effect


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
        type: ActionType,
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
                type,
                ActionCategory.OFFENSIVE,
                description,
                cooldown,
                maximum_uses,
                target_restrictions,
            )

            # Validate hands_required using helper
            self.hands_required = ensure_non_negative_int(
                hands_required, "hands required", 0, {"name": name}
            )

            # Validate attack_roll using helper
            self.attack_roll = ensure_string(
                attack_roll, "attack roll", "", {"name": name}
            )

            # Validate damage list using helper
            self.damage = ensure_list_of_type(
                damage,
                DamageComponent,
                "damage components",
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
            )
            raise

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
        if not self._validate_actor_and_target(actor, target):
            return False
        
        actor_str, target_str = self._get_display_strings(actor, target)

        debug(f"{actor.name} attempts a {self.name} on {target.name}.")

        # Check cooldown
        if not hasattr(actor, "is_on_cooldown"):
            log_error(
                f"Actor lacks is_on_cooldown method for {self.name}",
                {"action": self.name, "actor": actor.name},
            )
            return False

        if actor.is_on_cooldown(self):
            log_warning(
                f"Action {self.name} is on cooldown",
                {"action": self.name, "actor": actor.name},
            )
            return False

        # --- Build & resolve attack roll ---

        # Get attack modifier from the actor's effect manager.
        if not hasattr(actor, "effects_module"):
            log_error(
                f"Actor lacks effects_module for {self.name}",
                {"action": self.name, "actor": actor.name},
            )
            return False

        attack_modifier = actor.effects_module.get_modifier(BonusType.ATTACK)

        # Roll the attack.
        attack_total, attack_roll_desc, d20_roll = self._roll_attack_with_crit(
            actor, self.attack_roll, attack_modifier
        )

        # Detect crit and fumble.
        is_crit = d20_roll == 20
        is_fumble = d20_roll == 1

        msg = f"    🎯 {actor_str} attacks {target_str} with [bold blue]{self.name}[/]"

        # --- Outcome: MISS ---

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

        # --- Outcome: HIT ---

        # First roll the attack damage from the attack.
        base_damage, base_damage_details = roll_damage_components_no_mind(
            actor, target, self.damage
        )

        # If it's a crit, double the base damage.
        if is_crit:
            base_damage *= 2

        # Trigger OnHitTrigger effects (like Searing Smite)
        trigger_damage_bonuses, trigger_effects_with_levels, consumed_triggers = (
            actor.effects_module.trigger_on_hit_effects(target)
        )

        # Apply trigger effects to target with proper mind levels
        for effect, mind_level in trigger_effects_with_levels:
            if effect.can_apply(actor, target):
                target.effects_module.add_effect(actor, effect, mind_level)

        # Then roll any additional damage from effects (including triggered damage bonuses).
        all_damage_modifiers = (
            actor.effects_module.get_damage_modifiers() + trigger_damage_bonuses
        )
        bonus_damage, bonus_damage_details = roll_damage_components(
            actor, target, all_damage_modifiers
        )

        # Extend the total damage and details with bonus damage.
        total_damage = base_damage + bonus_damage
        damage_details = base_damage_details + bonus_damage_details

        # Is target still alive?
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

        # Display messages for consumed OnHitTrigger effects
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
