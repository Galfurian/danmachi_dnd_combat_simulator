"""
Factory pattern implementation for attack creation and serialization.

This module provides centralized factory classes for creating and serializing
attack instances, maintaining clean separation of concerns by removing
serialization logic from individual attack classes.
"""

from typing import Any

from actions.attacks.base_attack import BaseAttack
from actions.attacks.weapon_attack import WeaponAttack
from actions.attacks.natural_attack import NaturalAttack
from core.constants import ActionType
from actions.base_action import ActionSerializer
from catchery import log_critical
from combat.damage import DamageComponent
from effects.base_effect import Effect


class AttackDeserializer:
    """Factory for creating attack instances from dictionary data.

    This class provides methods to deserialize dictionary data into specific
    attack subclasses, such as `WeaponAttack` or `NaturalAttack`. It ensures
    proper instantiation of attack objects based on the provided configuration.
    """

    @staticmethod
    def deserialize(data: dict[str, Any]) -> BaseAttack | None:
        """
        Deserialize attack data from dictionary to appropriate attack instance.

        This method dynamically creates the correct attack subclass based on
        the 'class' field in the data dictionary.

        Args:
            data (dict[str, Any]): Dictionary containing attack configuration data.

        Returns:
            BaseAttack | None: Instance of the appropriate subclass, or None if not recognized.
        """
        try:
            attack_class = data.get("class", "")

            if attack_class == "BaseAttack":
                return AttackDeserializer._deserialize_base_attack(data)
            elif attack_class == "WeaponAttack":
                return AttackDeserializer._deserialize_weapon_attack(data)
            elif attack_class == "NaturalAttack":
                return AttackDeserializer._deserialize_natural_attack(data)
            else:
                # Not a recognized attack class - return None for other action types
                return None
        except Exception as e:
            attack_name = data.get("name", "Unknown")
            log_critical(
                f"Error creating attack '{attack_name}': {str(e)}",
                {"attack_name": attack_name, "error": str(e)},
                e,
                True,
            )

    @staticmethod
    def _deserialize_base_attack(data: dict[str, Any]) -> BaseAttack:
        """
        Create BaseAttack from dictionary data.

        Args:
            data (dict[str, Any]): Dictionary containing base attack configuration data.

        Returns:
            BaseAttack: Configured base attack instance.
        """
        return BaseAttack(
            name=data["name"],
            action_type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            attack_roll=data["attack_roll"],
            damage=[DamageComponent.from_dict(comp) for comp in data["damage"]],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
        )

    @staticmethod
    def _deserialize_weapon_attack(data: dict[str, Any]) -> WeaponAttack:
        """
        Create WeaponAttack from dictionary data.

        Args:
            data (dict[str, Any]): Dictionary containing weapon attack configuration data.

        Returns:
            WeaponAttack: Configured weapon attack instance.
        """
        return WeaponAttack(
            name=data["name"],
            action_type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            attack_roll=data["attack_roll"],
            damage=[DamageComponent.from_dict(comp) for comp in data["damage"]],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
        )

    @staticmethod
    def _deserialize_natural_attack(data: dict[str, Any]) -> NaturalAttack:
        """
        Create NaturalAttack from dictionary data.

        Args:
            data (dict[str, Any]): Dictionary containing natural attack configuration data.

        Returns:
            NaturalAttack: Configured natural attack instance.
        """
        return NaturalAttack(
            name=data["name"],
            action_type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            attack_roll=data["attack_roll"],
            damage=[DamageComponent.from_dict(comp) for comp in data["damage"]],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
        )


class AttackSerializer:
    """Serializer for converting attack instances to dictionary format.

    This class provides methods to serialize attack objects into dictionary
    representations, ensuring compatibility with external systems or storage.
    """

    @staticmethod
    def serialize(attack: BaseAttack) -> dict[str, Any]:
        """
        Serialize attack instance to dictionary format.

        This method handles common fields for all attack types and delegates
        specific serialization to the appropriate subclass methods.

        Args:
            attack (BaseAttack): The attack instance to serialize.

        Returns:
            dict[str, Any]: Dictionary representation of the attack.
        """
        if isinstance(attack, WeaponAttack):
            return AttackSerializer._serialize_weapon_attack(attack)
        elif isinstance(attack, NaturalAttack):
            return AttackSerializer._serialize_natural_attack(attack)
        elif isinstance(attack, BaseAttack):
            return AttackSerializer._serialize_base_attack(attack)
        else:
            raise ValueError(f"Unsupported attack type: {type(attack)}")

    @staticmethod
    def _serialize_base_attack(attack: BaseAttack) -> dict[str, Any]:
        """
        Serialize BaseAttack to dictionary format.

        Args:
            attack (BaseAttack): The base attack instance to serialize.

        Returns:
            dict[str, Any]: Dictionary representation of the base attack.
        """
        data = ActionSerializer.serialize(attack)
        data["attack_roll"] = attack.attack_roll
        data["damage"] = [component.to_dict() for component in attack.damage]
        if attack.effect:
            data["effect"] = attack.effect.to_dict()
        return data

    @staticmethod
    def _serialize_weapon_attack(attack: WeaponAttack) -> dict[str, Any]:
        """
        Serialize WeaponAttack to dictionary format.

        Args:
            attack (WeaponAttack): The weapon attack instance to serialize.

        Returns:
            dict[str, Any]: Dictionary representation of the weapon attack.
        """
        # WeaponAttack has same fields as BaseAttack
        return AttackSerializer._serialize_base_attack(attack)

    @staticmethod
    def _serialize_natural_attack(attack: NaturalAttack) -> dict[str, Any]:
        """
        Serialize NaturalAttack to dictionary format.

        Args:
            attack (NaturalAttack): The natural attack instance to serialize.

        Returns:
            dict[str, Any]: Dictionary representation of the natural attack.
        """
        # NaturalAttack has same fields as BaseAttack
        return AttackSerializer._serialize_base_attack(attack)
