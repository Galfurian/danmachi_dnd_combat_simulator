from core.utils import *
from typing import Any
from core.constants import *
from combat.damage import *
from .modifier import Modifier


class Effect:
    def __init__(self, name: str, description: str = "", max_duration: int = 0, requires_concentration: bool = False):
        self.name: str = name
        self.description: str = description
        self.max_duration: int = max_duration
        self.requires_concentration: bool = requires_concentration

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.__class__.__name__,
            "name": self.name,
            "description": self.description,
            "max_duration": self.max_duration,
            "requires_concentration": self.requires_concentration,
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
        modifiers: list[Modifier],
        requires_concentration: bool = False,
    ):
        super().__init__(name, description, max_duration, requires_concentration)
        self.modifiers: list[Modifier] = modifiers
        self.validate()

    def validate(self):
        super().validate()
        assert isinstance(self.modifiers, list), "Modifiers must be a list."
        for modifier in self.modifiers:
            assert isinstance(
                modifier, Modifier
            ), f"Modifier '{modifier}' must be of type Modifier."

    def can_apply(self, actor: Any, target: Any) -> bool:
        if not target.is_alive():
            return False
        # Check if the target is already affected by the same modifiers.
        for modifier in self.modifiers:
            existing_modifiers = target.effect_manager.get_modifier(modifier.bonus_type)
            if not existing_modifiers:
                continue
            # Check if the target already has this exact modifier
            if modifier in existing_modifiers:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["modifiers"] = [modifier.to_dict() for modifier in self.modifiers]
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
        modifiers: list[Modifier],
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
        modifiers: list[Modifier] = []

        # Handle both old dict format and new list format for backward compatibility
        if "modifiers" in data:
            modifier_data = data["modifiers"]
            if isinstance(modifier_data, dict):
                # Old format: convert dict to list of Modifier objects
                for k, v in modifier_data.items():
                    bonus_type = BonusType[k.upper()]
                    if bonus_type == BonusType.DAMAGE:
                        value = DamageComponent.from_dict(v)
                    elif bonus_type in [
                        BonusType.HP,
                        BonusType.MIND,
                        BonusType.AC,
                        BonusType.INITIATIVE,
                    ]:
                        value = int(v)
                    elif bonus_type == BonusType.ATTACK:
                        value = str(v)
                    else:
                        value = str(v)
                    modifiers.append(Modifier(bonus_type, value))
            elif isinstance(modifier_data, list):
                # New format: list of modifier dicts
                modifiers = [Modifier.from_dict(mod_data) for mod_data in modifier_data]

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
        modifiers: list[Modifier],
    ):
        super().__init__(name, description, max_duration, modifiers)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Debuff":
        assert data is not None, "Data must not be None."
        modifiers: list[Modifier] = []

        # Handle both old dict format and new list format for backward compatibility
        if "modifiers" in data:
            modifier_data = data["modifiers"]
            if isinstance(modifier_data, dict):
                # Old format: convert dict to list of Modifier objects
                for k, v in modifier_data.items():
                    bonus_type = BonusType[k.upper()]
                    if bonus_type == BonusType.DAMAGE:
                        value = DamageComponent.from_dict(v)
                    elif bonus_type in [
                        BonusType.HP,
                        BonusType.MIND,
                        BonusType.AC,
                        BonusType.INITIATIVE,
                    ]:
                        value = int(v)
                    elif bonus_type == BonusType.ATTACK:
                        value = str(v)
                    else:
                        value = str(v)
                    modifiers.append(Modifier(bonus_type, value))
            elif isinstance(modifier_data, list):
                # New format: list of modifier dicts
                modifiers = [Modifier.from_dict(mod_data) for mod_data in modifier_data]

        return Debuff(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            modifiers=modifiers,
        )


class DoT(Effect):
    def __init__(
        self,
        name: str,
        description: str,
        max_duration: int,
        damage: DamageComponent,
    ):
        super().__init__(name, description, max_duration)
        self.damage: DamageComponent = damage

        self.validate()

    def turn_update(self, actor: Any, target: Any, mind_level: Optional[int] = 1):
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        # Calculate the damage amount using the provided expression.
        dot_value, dot_desc, _ = roll_and_describe(self.damage.damage_roll, variables)
        # Asser that the damage value is a positive integer.
        assert (
            isinstance(dot_value, int) and dot_value >= 0
        ), f"DoT '{self.name}' must have a non-negative integer damage value, got {dot_value}."
        # Apply the damage to the target.
        base, adjusted, taken = target.take_damage(dot_value, self.damage.damage_type)
        # If the damage value is positive, print the damage message.
        dot_str = f"    {get_effect_emoji(self)} "
        dot_str += apply_character_type_color(target.type, target.name) + " takes "
        # Create a damage string for display.
        dot_str += apply_damage_type_color(
            self.damage.damage_type,
            f"{taken} {get_damage_type_emoji(self.damage.damage_type)} ",
        )
        # If the base damage differs from the adjusted damage (due to resistances),
        # include the original and adjusted values in the damage string.
        if base != adjusted:
            dot_str += f"[dim](reduced: {base} → {adjusted})[/] "
        # Append the rolled damage expression to the damage string.
        dot_str += f"({dot_desc})"
        # Add the damage string to the list of damage details.
        cprint(dot_str)
        # If the target is defeated, print a message.
        if not target.is_alive():
            cprint(f"    [bold red]{target.name} has been defeated![/]")

    def validate(self):
        super().validate()
        assert self.max_duration > 0, "DoT duration must be greater than 0."
        assert isinstance(
            self.damage, DamageComponent
        ), "Damage must be of type DamageComponent."

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["damage"] = self.damage.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "DoT":
        assert data is not None, "Data must not be None."
        return DoT(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            damage=DamageComponent.from_dict(data["damage"]),
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
        cprint(message)

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
