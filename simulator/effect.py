import json
from rich.console import Console

from utils import *
from typing import Any
from constants import *

console = Console()


class Effect:
    def __init__(self, name: str, max_duration: int = -1):
        self.name: str = name
        self.max_duration: int = max_duration

    def apply(self, actor: Any, target: Any, mind_level: Optional[int] = 0) -> None:
        """Apply the effect to the target Any.

        Args:
            actor (Any): The character applying the effect.
            target (Any): The character receiving the effect.
            mind_level (int, optional): The mind level of the actor. Defaults to 0.
        """
        ...

    def remove(self, actor: Any, target: Any) -> None:
        """Remove the effect from the target character.

        Args:
            actor (Any): The character removing the effect.
            target (Any): The character from whom the effect is being removed.
        """
        ...

    def turn_update(self, actor: Any, target: Any, mind_level: int = 0) -> None:
        """Update the effect for the current turn.

        Args:
            actor (Any): The character applying the effect.
            target (Any): The character receiving the effect.
            mind_level (int, optional): The mind level of the actor. Defaults to 0.
        """
        ...

    def is_permanent(self) -> bool:
        """Check if the effect is permanent (i.e., has no duration).

        Returns:
            bool: True if the effect is permanent, False otherwise.
        """
        return self.max_duration <= 0

    def validate(self):
        """Validate the effect's properties."""
        assert self.name, "Effect name must not be empty."
        assert isinstance(self.name, str), "Effect name must be a string."

    def to_dict(self):
        return {
            "type": self.__class__.__name__,
            "name": self.name,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Effect":
        """Creates an Effect instance from a dictionary representation.

        Args:
            data (dict[str, Any]): The dictionary representation of the effect.

        Returns:
            Effect: An instance of the Effect class.
        """
        assert data is not None, "Data must not be None."
        if data.get("type") == "Buff":
            return Buff.from_dict(data)
        if data.get("type") == "Debuff":
            return Debuff.from_dict(data)
        if data.get("type") == "Armor":
            return Armor.from_dict(data)
        if data.get("type") == "DoT":
            return DoT.from_dict(data)
        if data.get("type") == "HoT":
            return HoT.from_dict(data)
        raise ValueError(f"Unknown effect type: {data.get('type')}")


class ModifierEffect(Effect):
    def __init__(self, name: str, max_duration: int, modifiers: dict[BonusType, str]):
        super().__init__(name, max_duration)

        self.modifiers: dict[BonusType, Any] = modifiers

        self.validate()

    def validate(self):
        super().validate()
        assert self.max_duration > 0, "ModifierEffect duration must be greater than 0."
        assert isinstance(self.modifiers, dict), "Modifiers must be a dictionary."
        for k, v in self.modifiers.items():
            assert isinstance(
                k, BonusType
            ), f"Modifier key '{k}' must be of type BonusType."
            if k == BonusType.DAMAGE:
                assert isinstance(
                    v, dict
                ), f"Modifier value for '{k}' must be a dictionary."
                assert (
                    "damage_roll" in v
                ), f"Modifier value for '{k}' must contain 'damage_roll'."
                assert (
                    "damage_type" in v
                ), f"Modifier value for '{k}' must contain 'damage_type'."
            elif k == BonusType.ATTACK:
                assert isinstance(
                    v, str
                ), f"Modifier value for '{k}' must be a string expression."
            else:
                # Should be a string expression that evaluates to an integer.
                int(v)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.__class__.__name__,
            "name": self.name,
            "max_duration": self.max_duration,
            "modifiers": {k.name.lower(): v for k, v in self.modifiers.items()},
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Buff | Debuff":
        assert data is not None, "Data must not be None."
        if data.get("type") == "Buff":
            return Buff.from_dict(data)
        if data.get("type") == "Debuff":
            return Debuff.from_dict(data)
        raise ValueError(f"Unknown modifier effect type: {data.get('type')}")


class Buff(ModifierEffect):
    def __init__(
        self,
        name: str,
        max_duration: int,
        modifiers: dict[BonusType, str],
    ):
        super().__init__(name, max_duration, modifiers)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Buff":
        assert data is not None, "Data must not be None."
        return Buff(
            name=data["name"],
            max_duration=data["max_duration"],
            modifiers={BonusType[k.upper()]: v for k, v in data["modifiers"].items()},
        )


class Debuff(ModifierEffect):
    def __init__(
        self,
        name: str,
        max_duration: int,
        modifiers: dict[BonusType, str],
    ):
        super().__init__(name, max_duration, modifiers)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Debuff":
        assert data is not None, "Data must not be None."
        return Debuff(
            name=data["name"],
            max_duration=data["max_duration"],
            modifiers={BonusType[k.upper()]: v for k, v in data["modifiers"].items()},
        )


class Armor(Effect):
    def __init__(
        self,
        name: str,
        ac: int,
        armor_slot: ArmorSlot,
        armor_type: Optional[ArmorType] = None,
    ):
        super().__init__(name, -1)
        self.ac = ac
        self.armor_slot: ArmorSlot = armor_slot
        self.armor_type: Optional[ArmorType] = armor_type

        self.validate()

    def validate(self) -> None:
        assert self.ac >= 0, "Armor AC bonus must be a non-negative integer."
        assert isinstance(
            self.armor_slot, ArmorSlot
        ), f"Armor slot '{self.armor_slot}' must be of type ArmorSlot."
        # If armor type is specified, it must be of type ArmorType.
        if self.armor_type is not None:
            assert isinstance(
                self.armor_type, ArmorType
            ), f"Armor type '{self.armor_type}' must be of type ArmorType."

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        data["type"] = "Armor"
        data["name"] = self.name
        data["ac"] = self.ac
        data["armor_slot"] = self.armor_slot.name
        if self.armor_type is not None:
            data["armor_type"] = self.armor_type.name
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Armor":
        assert data is not None, "Data must not be None."
        return Armor(
            name=data["name"],
            ac=data["ac"],
            armor_slot=ArmorSlot[data["armor_slot"]],
            armor_type=ArmorType[data["armor_type"]] if "armor_type" in data else None,
        )


class DoT(Effect):
    def __init__(
        self,
        name: str,
        max_duration: int,
        damage_per_turn: str,
        damage_type: DamageType,
    ):
        super().__init__(name, max_duration)
        self.damage_per_turn = damage_per_turn
        self.damage_type: DamageType = damage_type

        self.validate()

    def turn_update(self, actor: Any, target: Any, mind_level: int = 0):
        # Calculate the damage amount using the provided expression.
        dot_value, dot_desc = roll_and_describe(self.damage_per_turn, actor, mind_level)
        # Asser that the damage value is a positive integer.
        assert (
            isinstance(dot_value, int) and dot_value >= 0
        ), f"DoT '{self.name}' must have a non-negative integer damage value, got {dot_value}."
        # Apply the damage to the target.
        dot_value = target.take_damage(dot_value, self.damage_type)
        # If the damage value is positive, print the damage message.
        message = f"    {get_effect_emoji(self)} "
        message += apply_character_type_color(target.type, target.name) + " takes "
        message += apply_damage_type_color(self.damage_type, dot_value) + " "
        message += get_damage_type_emoji(self.damage_type) + " "
        message += f"([white]{dot_desc}[/]) hp from "
        message += apply_effect_color(self, self.name) + "."
        console.print(message, markup=True)
        # If the target is defeated, print a message.
        if not target.is_alive():
            console.print(
                f"    [bold red]{target.name} has been defeated![/]",
                markup=True,
            )

    def validate(self):
        super().validate()
        assert self.max_duration > 0, "DoT duration must be greater than 0."
        assert isinstance(
            self.damage_per_turn, str
        ), "Damage per turn must be a string expression."
        assert isinstance(
            self.damage_type, DamageType
        ), f"Damage type '{self.damage_type}' must be of type DamageType."

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "DoT",
            "name": self.name,
            "max_duration": self.max_duration,
            "damage_per_turn": self.damage_per_turn,
            "damage_type": self.damage_type.name,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "DoT":
        assert data is not None, "Data must not be None."
        return DoT(
            name=data["name"],
            max_duration=data["max_duration"],
            damage_per_turn=data["damage_per_turn"],
            damage_type=DamageType[data["damage_type"]],
        )


class HoT(Effect):
    def __init__(
        self,
        name: str,
        max_duration: int,
        heal_per_turn: str,
    ):
        super().__init__(name, max_duration)
        self.heal_per_turn = heal_per_turn

        self.validate()

    def turn_update(self, actor: Any, target: Any, mind_level: int = 0):
        # Calculate the heal amount using the provided expression.
        hot_value, hot_desc = roll_and_describe(self.heal_per_turn, actor, mind_level)
        # Assert that the heal value is a positive integer.
        assert (
            isinstance(hot_value, int) and hot_value >= 0
        ), f"HoT '{self.name}' must have a non-negative integer heal value, got {hot_value}."
        # Apply the heal to the target.
        hot_value = target.heal(hot_value)
        # If the heal value is positive, print the heal message.
        message = f"    {get_effect_emoji(self)} "
        message += apply_character_type_color(target.type, target.name)
        message += f" heals for {hot_value} ([white]{hot_desc}[/]) hp from "
        message += apply_effect_color(self, self.name) + "."
        console.print(message, markup=True)

    def validate(self):
        super().validate()
        assert self.max_duration > 0, "HoT duration must be greater than 0."
        assert isinstance(
            self.heal_per_turn, str
        ), "Heal per turn must be a string expression."

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "HoT",
            "name": self.name,
            "max_duration": self.max_duration,
            "heal_per_turn": self.heal_per_turn,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "HoT":
        assert data is not None, "Data must not be None."
        return HoT(
            name=data["name"],
            max_duration=data["max_duration"],
            heal_per_turn=data["heal_per_turn"],
        )


def load_effects(filename: str) -> dict[str, Effect]:
    """Loads an effect from a dictionary.

    Args:
        data (dict): The dictionary containing the effect data.

    Returns:
        Effect: The loaded effect.
    """
    effects: dict[str, Effect] = {}
    with open(filename, "r") as f:
        effect_data = json.load(f)
        for effect_data in effect_data:
            effect = Effect.from_dict(effect_data)
            effects[effect.name] = effect
    return effects
