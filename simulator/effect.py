from logging import info, debug, warning, error

from rich.console import Console

from utils import *
from character import Character
from constants import *

console = Console()


class Effect:
    def __init__(self, name: str):
        self.name = name

    def apply(self, actor: Character, target: Character) -> None:
        pass

    def remove(self, actor: Character, target: Character) -> None:
        pass

    def turn_update(self, actor: Character, target: Character) -> bool:
        return False

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

        assert self.duration > 0, "Duration must be greater than 0."
        assert isinstance(self.modifiers, dict), "modifiers must be a dictionary."
        for key in self.modifiers.keys():
            assert isinstance(
                key, BonusType
            ), f"Bonus key '{key}' must be of type BonusType."

    def apply(self, actor: Character, target: Character):
        debug(f"Applying buff '{self.name}' to {target.name}.")

        for bonus_type, bonus_expr in self.modifiers.items():
            if bonus_type == BonusType.HP_MAX:
                bonus = get_prop_value(actor, bonus_expr, self.mind)
                target.hp_max += bonus
                target.hp += bonus
            elif bonus_type == BonusType.MIND_MAX:
                bonus = get_prop_value(actor, bonus_expr, self.mind)
                target.mind_max += bonus
                target.mind += bonus
            elif bonus_type == BonusType.AC:
                bonus = get_prop_value(actor, bonus_expr, self.mind)
                target.ac += bonus
            elif bonus_type == BonusType.ATTACK_BONUS:
                target.attack_modifiers[self.name] = bonus_expr
            elif bonus_type == BonusType.DAMAGE_BONUS:
                target.damage_modifiers[self.name] = bonus_expr

    def remove(self, actor: Character, target: Character):
        debug(f"Removing buff '{self.name}' from {target.name}.")

        for bonus_type, bonus_expr in self.modifiers.items():
            if bonus_type == BonusType.HP_MAX:
                bonus = get_prop_value(actor, bonus_expr, self.mind)
                target.hp_max -= bonus
                target.hp = min(target.hp, target.hp_max)
            elif bonus_type == BonusType.MIND_MAX:
                bonus = get_prop_value(actor, bonus_expr, self.mind)
                target.mind_max -= bonus
                target.mind = min(target.mind, target.mind_max)
            elif bonus_type == BonusType.AC:
                bonus = get_prop_value(actor, bonus_expr, self.mind)
                target.ac -= bonus
            elif bonus_type == BonusType.ATTACK_BONUS:
                if self.name in target.attack_modifiers:
                    del target.attack_modifiers[self.name]
            elif bonus_type == BonusType.DAMAGE_BONUS:
                if self.name in target.damage_modifiers:
                    del target.damage_modifiers[self.name]

    def turn_update(self, actor: Character, target: Character) -> bool:
        debug(f"Updating buff '{self.name}' for {target.name}.")
        self.duration -= 1
        if self.duration <= 0:
            console.print(
                f"[bold yellow]{self.name}[/] has expired on [bold]{target.name}[/]."
            )
            self.remove(actor, target)
            return True
        return False

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
    def __init__(self, name: str, ac_bonus: int):
        super().__init__(name)
        self.ac_bonus = ac_bonus

        assert self.ac_bonus > 0, "AC bonus must be greater than 0."

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
        }

    @staticmethod
    def from_dict(data):
        return Armor(
            name=data["name"],
            ac_bonus=data["ac_bonus"],
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

    def turn_update(self, actor: Character, target: Character) -> bool:
        damage_amount = roll_expression(self.damage_per_turn, actor, self.mind)
        if damage_amount > 0:
            actual_amount = target.take_damage(damage_amount, self.damage_type)
            console.print(
                f"[bold]{target.name}[/] takes {actual_amount} [bold]{self.damage_type.name.lower()}[/] damage from [bold]{self.name}[/]."
            )
        else:
            debug(
                f"DoT '{self.name}' had zero or negative magnitude for this turn on {target.name}."
            )
        self.duration -= 1
        if self.duration <= 0:
            console.print(
                f"[bold yellow]{self.name}[/] has expired on [bold]{target.name}[/]."
            )
            return True
        return False

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

    def turn_update(self, actor: Character, target: Character) -> bool:
        magnitude_amount = roll_expression(self.heal_per_turn, actor, self.mind)
        if magnitude_amount > 0:
            actual_amount = target.heal(magnitude_amount)
            console.print(
                f"[bold]{target.name}[/] heals for {actual_amount} hp from [bold]{self.name}[/]."
            )
        else:
            debug(
                f"HoT '{self.name}' had zero or negative magnitude for this turn on {target.name}."
            )
        self.duration -= 1
        if self.duration <= 0:
            console.print(
                f"[bold yellow]{self.name}[/] has expired on [bold]{target.name}[/]."
            )
            return True
        return False

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
