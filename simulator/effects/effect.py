import json
from rich.console import Console
from pathlib import Path

from core.utils import *
from typing import Any
from core.constants import *
from combat.damage import *

console = Console()


class Effect:
    def __init__(self, name: str, description: str = "", max_duration: int = 0):
        self.name: str = name
        self.description: str = description
        self.max_duration: int = max_duration

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
        assert isinstance(self.description, str), "Effect description must be a string."

    def can_apply(self, actor: Any, target: Any) -> bool:
        """Check if the effect can be applied to the target.

        Args:
            actor (Any): The character applying the effect.
            target (Any): The character receiving the effect.

        Returns:
            bool: True if the effect can be applied, False otherwise.
        """
        return False

    def to_dict(self):
        return {
            "type": self.__class__.__name__,
            "name": self.name,
            "description": self.description,
            "max_duration": self.max_duration,
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
    def __init__(
        self,
        name: str,
        description: str,
        max_duration: int,
        modifiers: dict[BonusType, str],
    ):
        super().__init__(name, description, max_duration)
        self.modifiers: dict[BonusType, Any] = modifiers
        self.validate()

    def validate(self):
        super().validate()
        assert isinstance(self.modifiers, dict), "Modifiers must be a dictionary."
        for k, v in self.modifiers.items():
            assert isinstance(
                k, BonusType
            ), f"Modifier key '{k}' must be of type BonusType."
            if k == BonusType.DAMAGE:
                assert isinstance(
                    v, DamageComponent
                ), f"Modifier value for '{k}' must be a DamageComponent."
            elif k == BonusType.ATTACK:
                assert isinstance(
                    v, str
                ), f"Modifier value for '{k}' must be a string expression."
            else:
                # Should be a string expression that evaluates to an integer.
                int(v)

    def can_apply(self, actor: Any, target: Any) -> bool:
        if not target.is_alive():
            return False
        # Check if the target is already affected by the same group of modifiers.
        for bonus_type, modifier in self.modifiers.items():
            exhisting_modifiers = target.effect_manager.get_modifier(bonus_type)
            if not exhisting_modifiers:
                continue
            # If the target already has a modifier of this type, check if it is the same.
            if isinstance(modifier, str):
                # If the modifier is a string, check if it matches any existing modifier.
                if modifier in exhisting_modifiers:
                    return False
            if not target.effect_manager.has_modifier(bonus_type, modifier):
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["modifiers"] = {
            k.name.lower(): v.to_dict() if isinstance(v, DamageComponent) else str(v)
            for k, v in self.modifiers.items()
        }
        return data

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
        description: str,
        max_duration: int,
        modifiers: dict[BonusType, str],
        consume_on_hit: bool = False,
    ):
        super().__init__(name, description, max_duration, modifiers)
        self.consume_on_hit: bool = consume_on_hit

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["consume_on_hit"] = self.consume_on_hit
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Buff":
        assert data is not None, "Data must not be None."
        modifiers: dict[BonusType, Any] = {}
        for k, v in data["modifiers"].items():
            key = BonusType[k.upper()]
            if key in [
                BonusType.HP,
                BonusType.MIND,
                BonusType.AC,
                BonusType.INITIATIVE,
            ]:
                modifiers[key] = int(v)
            elif key == BonusType.DAMAGE:
                modifiers[key] = DamageComponent.from_dict(v)
            elif key == BonusType.ATTACK:
                modifiers[key] = str(v)
        return Buff(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            modifiers=modifiers,
            consume_on_hit=data.get("consume_on_hit", False),
        )


class Debuff(ModifierEffect):
    def __init__(
        self,
        name: str,
        description: str,
        max_duration: int,
        modifiers: dict[BonusType, str],
    ):
        super().__init__(name, description, max_duration, modifiers)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Debuff":
        assert data is not None, "Data must not be None."
        modifiers: dict[BonusType, Any] = {}
        for k, v in data["modifiers"].items():
            key = BonusType[k.upper()]
            if key in [
                BonusType.HP,
                BonusType.MIND,
                BonusType.AC,
                BonusType.INITIATIVE,
            ]:
                modifiers[key] = int(v)
            elif key == BonusType.DAMAGE:
                modifiers[key] = DamageComponent.from_dict(v)
            elif key == BonusType.ATTACK:
                modifiers[key] = str(v)
        return Debuff(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            modifiers=modifiers,
        )


class Armor(Effect):
    def __init__(
        self,
        name: str,
        description: str,
        ac: int,
        armor_slot: ArmorSlot,
        armor_type: ArmorType,
    ):
        super().__init__(name, description)
        self.ac = ac
        self.armor_slot: ArmorSlot = armor_slot
        self.armor_type: ArmorType = armor_type

        self.validate()

    def validate(self) -> None:
        assert self.ac >= 0, "Armor AC bonus must be a non-negative integer."
        assert isinstance(
            self.armor_slot, ArmorSlot
        ), f"Armor slot '{self.armor_slot}' must be of type ArmorSlot."
        # If armor type is specified, it must be of type ArmorType.
        assert isinstance(
            self.armor_type, ArmorType
        ), f"Armor type '{self.armor_type}' must be of type ArmorType."

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["ac"] = self.ac
        data["armor_slot"] = self.armor_slot.name
        data["armor_type"] = self.armor_type.name
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Armor":
        assert data is not None, "Data must not be None."
        return Armor(
            name=data["name"],
            description=data.get("description", ""),
            ac=data["ac"],
            armor_slot=ArmorSlot[data["armor_slot"]],
            armor_type=ArmorType[data["armor_type"]],
        )


class DoT(Effect):
    def __init__(
        self,
        name: str,
        description: str,
        max_duration: int,
        damage_per_turn: str,
        damage_type: DamageType,
    ):
        super().__init__(name, description, max_duration)
        self.damage_per_turn = damage_per_turn
        self.damage_type: DamageType = damage_type

        self.validate()

    def turn_update(self, actor: Any, target: Any, mind_level: Optional[int] = 1):
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        # Calculate the damage amount using the provided expression.
        dot_value, dot_desc, _ = roll_and_describe(self.damage_per_turn, variables)
        # Asser that the damage value is a positive integer.
        assert (
            isinstance(dot_value, int) and dot_value >= 0
        ), f"DoT '{self.name}' must have a non-negative integer damage value, got {dot_value}."
        # Apply the damage to the target.
        base, adjusted, taken = target.take_damage(dot_value, self.damage_type)
        # If the damage value is positive, print the damage message.
        dot_str = f"    {get_effect_emoji(self)} "
        dot_str += apply_character_type_color(target.type, target.name) + " takes "
        # Create a damage string for display.
        dot_str += apply_damage_type_color(
            self.damage_type,
            f"{taken} {get_damage_type_emoji(self.damage_type)} ",
        )
        # If the base damage differs from the adjusted damage (due to resistances),
        # include the original and adjusted values in the damage string.
        if base != adjusted:
            dot_str += f"[dim](reduced: {base} → {adjusted})[/] "
        # Append the rolled damage expression to the damage string.
        dot_str += f"({dot_desc})"
        # Add the damage string to the list of damage details.
        console.print(dot_str, markup=True)
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
        data = super().to_dict()
        data["damage_per_turn"] = self.damage_per_turn
        data["damage_type"] = self.damage_type.name
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "DoT":
        assert data is not None, "Data must not be None."
        return DoT(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            damage_per_turn=data["damage_per_turn"],
            damage_type=DamageType[data["damage_type"]],
        )


class HoT(Effect):
    def __init__(
        self,
        name: str,
        description: str,
        max_duration: int,
        heal_per_turn: str,
    ):
        super().__init__(name, description, max_duration)
        self.heal_per_turn = heal_per_turn

        self.validate()

    def turn_update(self, actor: Any, target: Any, mind_level: Optional[int] = 1):
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        # Calculate the heal amount using the provided expression.
        hot_value, hot_desc, _ = roll_and_describe(self.heal_per_turn, variables)
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
        data = super().to_dict()
        data["heal_per_turn"] = self.heal_per_turn
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "HoT":
        assert data is not None, "Data must not be None."
        return HoT(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            heal_per_turn=data["heal_per_turn"],
        )
