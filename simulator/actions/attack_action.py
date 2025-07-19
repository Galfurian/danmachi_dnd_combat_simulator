from typing import Any, Optional

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
from core.error_handling import log_error, log_warning, log_critical
from core.utils import (
    debug,
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    substitute_variables,
    cprint,
)
from effects.effect import Effect


class BaseAttack(BaseAction):
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
        effect: Optional[Effect] = None,
        target_restrictions: list[str] | None = None,
    ):
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

            # Validate hands_required
            if not isinstance(hands_required, int) or hands_required < 0:
                log_warning(
                    f"Attack {name} hands_required must be non-negative integer, got: {hands_required}",
                    {"name": name, "hands_required": hands_required},
                )
                hands_required = max(
                    0,
                    (
                        int(hands_required)
                        if isinstance(hands_required, (int, float))
                        else 0
                    ),
                )

            # Validate attack_roll
            if not isinstance(attack_roll, str):
                log_error(
                    f"Attack {name} attack_roll must be string, got: {attack_roll.__class__.__name__}",
                    {"name": name, "attack_roll": attack_roll},
                )
                attack_roll = str(attack_roll) if attack_roll is not None else ""

            # Validate damage list
            if not isinstance(damage, list):
                log_error(
                    f"Attack {name} damage must be list, got: {damage.__class__.__name__}",
                    {"name": name, "damage": damage},
                )
                damage = []
            else:
                # Validate each damage component
                for i, dmg_comp in enumerate(damage):
                    if not isinstance(dmg_comp, DamageComponent):
                        log_error(
                            f"Attack {name} damage[{i}] must be DamageComponent, got: {dmg_comp.__class__.__name__}",
                            {
                                "name": name,
                                "damage_index": i,
                                "damage_component": dmg_comp,
                            },
                        )

            # Validate effect
            if effect is not None and not isinstance(effect, Effect):
                log_warning(
                    f"Attack {name} effect must be Effect or None, got: {effect.__class__.__name__}",
                    {"name": name, "effect": effect},
                )
                effect = None

            self.hands_required: int = hands_required
            self.attack_roll: str = attack_roll
            self.damage: list[DamageComponent] = damage
            self.effect: Optional[Effect] = effect

        except Exception as e:
            log_critical(
                f"Error initializing BaseAttack {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

    def execute(self, actor: Any, target: Any) -> bool:
        try:
            # Validate inputs
            if not actor:
                log_error(
                    f"Cannot execute {self.name}: actor is None", {"action": self.name}
                )
                return False

            if not target:
                log_error(
                    f"Cannot execute {self.name}: target is None",
                    {"action": self.name, "actor": getattr(actor, "name", "Unknown")},
                )
                return False

            # Validate required attributes
            if not hasattr(actor, "name") or not hasattr(actor, "type"):
                log_error(
                    f"Actor missing required attributes for {self.name}",
                    {"action": self.name, "actor": actor},
                )
                return False

            if not hasattr(target, "name") or not hasattr(target, "type"):
                log_error(
                    f"Target missing required attributes for {self.name}",
                    {"action": self.name, "target": target},
                )
                return False

            actor_str = apply_character_type_color(actor.type, actor.name)
            target_str = apply_character_type_color(target.type, target.name)

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
            if not hasattr(actor, "effect_manager"):
                log_error(
                    f"Actor lacks effect_manager for {self.name}",
                    {"action": self.name, "actor": actor.name},
                )
                return False

            attack_modifier = actor.effect_manager.get_modifier(BonusType.ATTACK)

            # Roll the attack.
            attack_total, attack_roll_desc, d20_roll = self.roll_attack_with_crit(
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
                actor.effect_manager.trigger_on_hit_effects(target)
            )

            # Apply trigger effects to target with proper mind levels
            for effect, mind_level in trigger_effects_with_levels:
                if effect.can_apply(actor, target):
                    target.effect_manager.add_effect(actor, effect, mind_level)

            # Then roll any additional damage from effects (including triggered damage bonuses).
            all_damage_modifiers = (
                actor.effect_manager.get_damage_modifiers() + trigger_damage_bonuses
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
                    if self.apply_effect(actor, target, self.effect):
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
                    if self.apply_effect(actor, target, self.effect):
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

        except Exception as e:
            log_error(
                f"Error executing attack {self.name}: {str(e)}",
                {
                    "action": self.name,
                    "error": str(e),
                    "actor": getattr(actor, "name", "Unknown"),
                    "target": getattr(target, "name", "Unknown"),
                },
                e,
            )
            return False

    def get_damage_expr(self, actor: Any) -> str:
        """Returns the damage expression with variables substituted.

        Args:
            actor (Any): The character performing the action.

        Returns:
            str: The damage expression with variables substituted.
        """
        return " + ".join(
            substitute_variables(component.damage_roll, actor)
            for component in self.damage
        )

    def get_min_damage(self, actor: Any) -> int:
        """Returns the minimum damage value for the attack.

        Args:
            actor (Any): The character performing the action.

        Returns:
            int: The minimum damage value for the attack.
        """
        return sum(
            parse_expr_and_assume_min_roll(
                substitute_variables(component.damage_roll, actor)
            )
            for component in self.damage
        )

    def get_max_damage(self, actor: Any) -> int:
        """Returns the maximum damage value for the attack.

        Args:
            actor (Any): The character performing the action.

        Returns:
            int: The maximum damage value for the attack.
        """
        return sum(
            parse_expr_and_assume_max_roll(
                substitute_variables(component.damage_roll, actor)
            )
            for component in self.damage
        )

    def to_dict(self) -> dict[str, Any]:
        # Get the base dictionary representation.
        data = super().to_dict()
        # Add specific fields for BaseAttack
        data["hands_required"] = self.hands_required
        data["attack_roll"] = self.attack_roll
        data["damage"] = [component.to_dict() for component in self.damage]
        # Include the effect if it exists.
        if self.effect:
            data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "BaseAttack":
        """
        Creates a BaseAttack instance from a dictionary.
        Args:
            data (dict): Dictionary containing the action data.
        Returns:
            BaseAttack: An instance of BaseAttack.
        """
        return BaseAttack(
            name=data["name"],
            type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            hands_required=data.get("hands_required", 0),
            attack_roll=data["attack_roll"],
            damage=[DamageComponent.from_dict(comp) for comp in data["damage"]],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
        )


class WeaponAttack(BaseAttack):
    """A weapon-based attack that can be equipped and unequipped."""

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
        effect: Optional[Effect] = None,
    ):
        super().__init__(
            name,
            type,
            description,
            cooldown,
            maximum_uses,
            hands_required,
            attack_roll,
            damage,
            effect,
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "WeaponAttack":
        """Creates a WeaponAttack instance from a dictionary."""
        return WeaponAttack(
            name=data["name"],
            type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            hands_required=data.get("hands_required", 0),
            attack_roll=data["attack_roll"],
            damage=[DamageComponent.from_dict(comp) for comp in data["damage"]],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
        )


class NaturalAttack(BaseAttack):
    """A natural/innate attack that is part of a creature's biology."""

    def __init__(
        self,
        name: str,
        type: ActionType,
        description: str,
        cooldown: int,
        maximum_uses: int,
        attack_roll: str,
        damage: list[DamageComponent],
        effect: Optional[Effect] = None,
    ):
        super().__init__(
            name,
            type,
            description,
            cooldown,
            maximum_uses,
            0,  # Natural attacks don't require hands
            attack_roll,
            damage,
            effect,
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "NaturalAttack":
        """Creates a NaturalAttack instance from a dictionary."""
        return NaturalAttack(
            name=data["name"],
            type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            attack_roll=data["attack_roll"],
            damage=[DamageComponent.from_dict(comp) for comp in data["damage"]],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
        )


def from_dict_attack(data: dict[str, Any]) -> Optional[BaseAttack]:
    """
    Creates a BaseAttack instance from a dictionary.
    Args:
        data (dict): Dictionary containing the action data.
    Returns:
        BaseAttack: An instance of BaseAttack or its subclass.
    """
    attack_class = data.get("class", "BaseAttack")

    if attack_class == "WeaponAttack":
        return WeaponAttack.from_dict(data)
    elif attack_class == "NaturalAttack":
        return NaturalAttack.from_dict(data)
    elif attack_class == "BaseAttack":
        return BaseAttack.from_dict(data)

    return None
