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
from core.error_handling import log_critical
from combat.damage import DamageComponent
from effects.effect import Effect


class AttackDeserializer:
    """Factory for creating attack instances from dictionary data."""

    @staticmethod
    def deserialize(data: dict[str, Any]) -> Any | None:
        """
        Deserialize attack data from dictionary to appropriate attack instance.

        This method dynamically creates the correct attack subclass based on
        the 'class' field in the data dictionary.

        Args:
            data: Dictionary containing attack configuration data.

        Returns:
            BaseAttack instance of the appropriate subclass, or None if not recognized.
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
            )
            raise

    @staticmethod
    def _deserialize_base_attack(data: dict[str, Any]) -> BaseAttack:
        """Create BaseAttack from dictionary data."""
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

    @staticmethod
    def _deserialize_weapon_attack(data: dict[str, Any]) -> WeaponAttack:
        """Create WeaponAttack from dictionary data."""
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

    @staticmethod
    def _deserialize_natural_attack(data: dict[str, Any]) -> NaturalAttack:
        """Create NaturalAttack from dictionary data."""
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


class AttackSerializer:
    """Serializer for converting attack instances to dictionary format."""

    @staticmethod
    def serialize(attack: BaseAttack) -> dict[str, Any]:
        """
        Serialize attack instance to dictionary format.

        This method handles common fields for all attack types and delegates
        specific serialization to the appropriate subclass methods.

        Args:
            attack: The attack instance to serialize.

        Returns:
            dict: Dictionary representation of the attack.
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
        """Serialize BaseAttack to dictionary."""
        data = {
            "name": attack.name,
            "type": attack.type.name,
            "description": attack.description,
            "cooldown": attack.cooldown,
            "maximum_uses": attack.maximum_uses,
            "hands_required": attack.hands_required,
            "attack_roll": attack.attack_roll,
            "damage": [component.to_dict() for component in attack.damage],
        }
        
        if attack.effect:
            data["effect"] = attack.effect.to_dict()
            
        return data

    @staticmethod
    def _serialize_weapon_attack(attack: WeaponAttack) -> dict[str, Any]:
        """Serialize WeaponAttack to dictionary."""
        # WeaponAttack has same fields as BaseAttack
        return AttackSerializer._serialize_base_attack(attack)

    @staticmethod
    def _serialize_natural_attack(attack: NaturalAttack) -> dict[str, Any]:
        """Serialize NaturalAttack to dictionary."""
        # NaturalAttack has same fields as BaseAttack
        return AttackSerializer._serialize_base_attack(attack)
