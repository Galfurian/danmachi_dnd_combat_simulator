from typing import Any, Optional

from combat.damage import *
from core.utils import *
from core.constants import *
from actions.base_action import *
from effects.effect import *


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
    ):
        super().__init__(
            name, type, ActionCategory.OFFENSIVE, description, cooldown, maximum_uses
        )
        self.hands_required: int = hands_required
        self.attack_roll: str = attack_roll
        self.damage: list[DamageComponent] = damage
        self.effect: Optional[Effect] = effect

    def execute(self, actor: Any, target: Any):
        actor_str = apply_character_type_color(actor.type, actor.name)
        target_str = apply_character_type_color(target.type, target.name)

        debug(f"{actor.name} attempts a {self.name} on {target.name}.")

        # If the action has a cooldown, add it to the actor's cooldowns.
        assert not actor.is_on_cooldown(self), f"Action {self.name} is on cooldown."

        # --- Build & resolve attack roll ---

        # Get attack modifier from the actor's effect manager.
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

        # Then roll any additional damage from effects.
        bonus_damage, bonus_damage_details = roll_damage_components(
            actor, target, actor.effect_manager.get_damage_modifiers()
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
        cprint(msg)

        return True

    def is_valid_target(self, actor: Any, target: Any) -> bool:
        """Checks if the target is valid for the action.

        Args:
            actor (Any): The character performing the action.
            target (Any): The character targeted by the action.

        Returns:
            bool: True if the target is valid, False otherwise.
        """
        # A target is valid if:
        # - It is not the actor itself.
        # - Both actor and target are alive.
        # - If the actor and the enemy are not both allies or enemies.
        if target == actor:
            return False
        if not actor.is_alive() or not target.is_alive():
            return False
        if not is_oponent(actor.type, target.type):
            return False
        return True

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
            name, type, description, cooldown, maximum_uses, 
            hands_required, attack_roll, damage, effect
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
            name, type, description, cooldown, maximum_uses, 
            0,  # Natural attacks don't require hands
            attack_roll, damage, effect
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
