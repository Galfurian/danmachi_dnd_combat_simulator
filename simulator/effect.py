from logging import info, debug, warning, error
from rich.console import Console
from abc import ABC, abstractmethod
from utils import *
from character import Character
from constants import *

console = Console()


class Effect:
    def __init__(self, name: str):
        self.name = name

    def apply(self, actor: Character, target: Character, mind_level: int = 0) -> None:
        """Apply the effect to the target character.

        Args:
            actor (Character): The character applying the effect.
            target (Character): The character receiving the effect.
            mind_level (int, optional): The mind level of the actor. Defaults to 0.
        """
        ...

    def remove(self, actor: Character, target: Character) -> None:
        """Remove the effect from the target character.

        Args:
            actor (Character): The character removing the effect.
            target (Character): The character from whom the effect is being removed.
        """
        ...

    def turn_update(
        self, actor: Character, target: Character, mind_level: int = 0
    ) -> None:
        """Update the effect for the current turn.

        Args:
            actor (Character): The character applying the effect.
            target (Character): The character receiving the effect.
            mind_level (int, optional): The mind level of the actor. Defaults to 0.
        """
        ...

    def to_dict(self):
        return {
            "type": self.__class__.__name__,
            "name": self.name,
        }

    @staticmethod
    def from_dict(data):
        if not data:
            return None
        if data.get("type") == "Buff":
            return Buff.from_dict(data)
        if data.get("type") == "Armor":
            return Armor.from_dict(data)
        if data.get("type") == "DoT":
            return DoT.from_dict(data)
        if data.get("type") == "HoT":
            return HoT.from_dict(data)
        if data.get("type") == "Effect":
            return Effect(data["name"])
        return None


class Buff(Effect):
    def __init__(self, name: str, mind: int, duration: int, modifiers: dict):
        super().__init__(name)
        self.mind = mind
        self.duration = duration
        self.modifiers = modifiers
        self._cached_values: dict[BonusType, int] = {}

        assert self.duration > 0, "Duration must be greater than 0."
        assert isinstance(self.modifiers, dict), "modifiers must be a dictionary."
        for key in self.modifiers.keys():
            assert isinstance(
                key, BonusType
            ), f"Bonus key '{key}' must be of type BonusType."

    def apply(self, actor: Character, target: Character, mind_level: int = 0):
        debug(f"Applying buff '{self.name}' to {target.name}.")
        # Use the effect mind level, or the one provided.
        mind_level = max(self.mind, mind_level)
        # Evaluate each modifier and apply it to the target
        for bonus_type, bonus_expr in self.modifiers.items():
            if bonus_type == BonusType.HP_MAX:
                bonus = evaluate_expression(bonus_expr, actor, mind_level)
                self._cached_values[bonus_type] = bonus
                target.hp_max += bonus
                target.hp += bonus
            elif bonus_type == BonusType.MIND_MAX:
                bonus = evaluate_expression(bonus_expr, actor, mind_level)
                self._cached_values[bonus_type] = bonus
                target.mind_max += bonus
                target.mind += bonus
            elif bonus_type == BonusType.AC:
                bonus = evaluate_expression(bonus_expr, actor, mind_level)
                self._cached_values[bonus_type] = bonus
                target.ac += bonus
            elif bonus_type == BonusType.ATTACK_BONUS:
                self._cached_values[bonus_type] = bonus_expr
                target.attack_modifiers[self.name] = bonus_expr
            elif bonus_type == BonusType.DAMAGE_BONUS:
                self._cached_values[bonus_type] = bonus_expr
                target.damage_modifiers[self.name] = bonus_expr

    def remove(self, actor: Character, target: Character):
        debug(f"Removing buff '{self.name}' from {target.name}.")
        for bonus_type, bonus in self._cached_values.items():
            if bonus_type == BonusType.HP_MAX:
                target.hp_max -= bonus
                target.hp = min(target.hp, target.hp_max)
            elif bonus_type == BonusType.MIND_MAX:
                target.mind_max -= bonus
                target.mind = min(target.mind, target.mind_max)
            elif bonus_type == BonusType.AC:
                target.ac -= bonus
            elif bonus_type == BonusType.ATTACK_BONUS:
                if self.name in target.attack_modifiers:
                    del target.attack_modifiers[self.name]
            elif bonus_type == BonusType.DAMAGE_BONUS:
                if self.name in target.damage_modifiers:
                    del target.damage_modifiers[self.name]
        self._cached_values.clear()

    def to_dict(self):
        return {
            "type": "Buff",
            "name": self.name,
            "mind": self.mind,
            "duration": self.duration,
            "modifiers": {k.name: v for k, v in self.modifiers.items()},
        }

    @staticmethod
    def from_dict(data):
        modifiers = {BonusType[k]: v for k, v in data["modifiers"].items()}
        return Buff(
            name=data["name"],
            mind=data["mind"],
            duration=data["duration"],
            modifiers=modifiers,
        )


class Armor(Effect):
    def __init__(self, name: str, ac_bonus: int, armor_slot: ArmorSlot):
        super().__init__(name)
        self.ac_bonus = ac_bonus
        self.armor_slot: ArmorSlot = armor_slot

        assert self.ac_bonus > 0, "AC bonus must be greater than 0."
        assert isinstance(armor_slot, ArmorSlot), "armor_slot must be ArmorSlot enum."

    def wear(self, actor: Character):
        debug(f"{actor.name} wears armor '{self.name}' with AC bonus {self.ac_bonus}.")
        actor.ac += self.ac_bonus

    def strip(self, actor: Character):
        debug(f"{actor.name} strips armor '{self.name}' with AC bonus {self.ac_bonus}.")
        actor.ac -= self.ac_bonus

    def to_dict(self):
        return {
            "type": "Armor",
            "name": self.name,
            "ac_bonus": self.ac_bonus,
            "armor_slot": self.armor_slot.name,
        }

    @staticmethod
    def from_dict(data):
        return Armor(
            name=data["name"],
            ac_bonus=data["ac_bonus"],
            armor_slot=ArmorSlot[data["armor_slot"]],
        )


class DoT(Effect):
    def __init__(
        self,
        name: str,
        mind: int,
        duration: int,
        damage_per_turn: str,
        damage_type: DamageType,
    ):
        super().__init__(name)
        self.mind = mind
        self.duration = duration
        self.damage_per_turn = damage_per_turn
        self.damage_type: DamageType = damage_type

        assert self.duration > 0, "Duration must be greater than 0."
        assert self.damage_per_turn, "Damage per turn must be a valid string."
        assert isinstance(
            self.damage_type, DamageType
        ), f"Damage type '{self.damage_type}' must be of type DamageType."

    def turn_update(self, actor: Character, target: Character, mind_level: int = 0):
        # Compute the actually used mind level, which is the maximum of the effect's mind and the actor's mind.
        mind_level = max(self.mind, mind_level)
        # Calculate the damage amount using the provided expression.
        dot_value, dot_desc = roll_and_describe(self.damage_per_turn, actor, mind_level)
        # Asser that the damage value is a positive integer.
        assert (
            isinstance(dot_value, int) and dot_value >= 0
        ), f"DoT '{self.name}' must have a non-negative integer damage value, got {dot_value}."
        # Apply the damage to the target.
        dot_value = target.take_damage(dot_value, self.damage_type)
        # If the damage value is positive, print the damage message.
        console.print(
            f"    :fire: [bold]{target.name}[/] takes {dot_value} ([white]{dot_desc}[/]) [bold]{self.damage_type.name.lower()}[/] damage from [bold]{self.name}[/]."
        )

    def to_dict(self):
        return {
            "type": "DoT",
            "name": self.name,
            "mind": self.mind,
            "duration": self.duration,
            "damage_per_turn": self.damage_per_turn,
            "damage_type": self.damage_type.name,
        }

    @staticmethod
    def from_dict(data):
        return DoT(
            name=data["name"],
            mind=data["mind"],
            duration=data["duration"],
            damage_per_turn=data["damage_per_turn"],
            damage_type=DamageType[data["damage_type"]],
        )


class HoT(Effect):
    def __init__(
        self,
        name: str,
        mind: int,
        duration: int,
        heal_per_turn: str,
    ):
        super().__init__(name)
        self.mind = mind
        self.duration = duration
        self.heal_per_turn = heal_per_turn

        assert self.duration > 0, "Duration must be greater than 0."

    def turn_update(self, actor: Character, target: Character, mind_level: int = 0):
        # Compute the actually used mind level, which is the maximum of the effect's mind and the actor's mind.
        mind_level = max(self.mind, mind_level)
        # Calculate the heal amount using the provided expression.
        hot_value, hot_desc = roll_and_describe(self.heal_per_turn, actor, mind_level)
        # Asser that the heal value is a positive integer.
        assert (
            isinstance(hot_value, int) and hot_value >= 0
        ), f"HoT '{self.name}' must have a non-negative integer heal value, got {hot_value}."
        # Apply the heal to the target.
        hot_value = target.heal(hot_value)
        # If the heal value is positive, print the heal message.
        console.print(
            f"    :heavy_plus_sign: [bold green]{target.name}[/] heals for {hot_value} ([white]{hot_desc}[/]) hp from [bold]{self.name}[/]."
        )

    def to_dict(self):
        return {
            "type": "HoT",
            "name": self.name,
            "mind": self.mind,
            "duration": self.duration,
            "heal_per_turn": self.heal_per_turn,
        }

    @staticmethod
    def from_dict(data):
        return HoT(
            name=data["name"],
            mind=data["mind"],
            duration=data["duration"],
            heal_per_turn=data["heal_per_turn"],
        )
