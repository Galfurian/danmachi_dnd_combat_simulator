"""
Factory pattern implementation for ability creation and serialization.

This module provides centralized factory classes for creating and serializing
ability instances, maintaining clean separation of concerns by removing
serialization logic from individual ability classes.
"""

from typing import Any

from actions.abilities.ability_buff import BuffAbility
from actions.abilities.ability_healing import HealingAbility
from actions.abilities.ability_offensive import OffensiveAbility
from actions.abilities.ability_utility import UtilityAbility
from actions.abilities.base_ability import BaseAbility
from core.constants import ActionCategory, ActionType
from core.error_handling import log_critical
from combat.damage import DamageComponent
from effects.base_effect import Effect


class AbilityDeserializer:
    """Factory for creating ability instances from dictionary data."""

    @staticmethod
    def deserialize(data: dict[str, Any]) -> BaseAbility | None:
        """
        Deserialize ability data from dictionary to appropriate ability instance.

        This method dynamically creates the correct ability subclass based on
        the 'class' field in the data dictionary.

        Args:
            data (dict[str, Any]): Dictionary containing ability configuration data.

        Returns:
            BaseAbility | None: Instance of the appropriate subclass, or None if not recognized.
        """
        try:
            ability_class = data.get("class", "")

            if ability_class == "BaseAbility":
                # For backward compatibility, default to OffensiveAbility
                return AbilityDeserializer._deserialize_offensive_ability(data)
            elif ability_class == "OffensiveAbility":
                return AbilityDeserializer._deserialize_offensive_ability(data)
            elif ability_class == "HealingAbility":
                return AbilityDeserializer._deserialize_healing_ability(data)
            elif ability_class == "BuffAbility":
                return AbilityDeserializer._deserialize_buff_ability(data)
            elif ability_class == "UtilityAbility":
                return AbilityDeserializer._deserialize_utility_ability(data)
            else:
                # Not a recognized ability class - return None for other action types
                return None
        except Exception as e:
            ability_name = data.get("name", "Unknown")
            log_critical(
                f"Error creating ability '{ability_name}': {str(e)}",
                {"ability_name": ability_name, "error": str(e)},
                e,
            )
            raise

    @staticmethod
    def _deserialize_offensive_ability(data: dict[str, Any]) -> OffensiveAbility:
        """
        Create OffensiveAbility from dictionary data.

        Args:
            data (dict[str, Any]): Dictionary containing offensive ability configuration data.

        Returns:
            OffensiveAbility: Configured offensive ability instance.
        """
        return OffensiveAbility(
            name=data["name"],
            action_type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            damage=[DamageComponent.from_dict(comp) for comp in data["damage"]],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
            target_expr=data.get("target_expr", ""),
            target_restrictions=data.get("target_restrictions"),
        )

    @staticmethod
    def _deserialize_healing_ability(data: dict[str, Any]) -> HealingAbility:
        """
        Create HealingAbility from dictionary data.

        Args:
            data (dict[str, Any]): Dictionary containing healing ability configuration data.

        Returns:
            HealingAbility: Configured healing ability instance.
        """
        return HealingAbility(
            name=data["name"],
            action_type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            heal_roll=data["heal_roll"],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
            target_expr=data.get("target_expr", ""),
            target_restrictions=data.get("target_restrictions"),
        )

    @staticmethod
    def _deserialize_buff_ability(data: dict[str, Any]) -> BuffAbility:
        """
        Create BuffAbility from dictionary data.

        Args:
            data (dict[str, Any]): Dictionary containing buff ability configuration data.

        Returns:
            BuffAbility: Configured buff ability instance.

        Raises:
            ValueError: If required effect data is missing.
        """
        if "effect" not in data or data["effect"] is None:
            raise ValueError(
                f"BuffAbility {data.get('name', 'Unknown')} requires a valid effect"
            )
        effect = Effect.from_dict(data["effect"])
        if not effect:
            raise ValueError(
                f"BuffAbility {data.get('name', 'Unknown')} has an invalid effect"
            )
        return BuffAbility(
            name=data["name"],
            action_type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            effect=effect,  # Ensure effect is valid
            target_expr=data.get("target_expr", ""),
            target_restrictions=data.get("target_restrictions"),
        )

    @staticmethod
    def _deserialize_utility_ability(data: dict[str, Any]) -> UtilityAbility:
        """
        Create UtilityAbility from dictionary data.

        Args:
            data (dict[str, Any]): Dictionary containing utility ability configuration data.

        Returns:
            UtilityAbility: Configured utility ability instance.
        """
        return UtilityAbility(
            name=data["name"],
            action_type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            utility_function=data.get("utility_function", ""),
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
            target_expr=data.get("target_expr", ""),
            target_restrictions=data.get("target_restrictions"),
        )


class AbilitySerializer:
    """Serializer for converting ability instances to dictionary format."""

    @staticmethod
    def serialize(ability: BaseAbility) -> dict[str, Any]:
        """
        Serialize ability instance to dictionary format.

        This method handles common fields for all ability types and delegates
        specific serialization to the appropriate subclass methods.

        Args:
            ability (BaseAbility): The ability instance to serialize.

        Returns:
            dict[str, Any]: Dictionary representation of the ability.
        """
        if isinstance(ability, OffensiveAbility):
            return AbilitySerializer._serialize_offensive_ability(ability)
        elif isinstance(ability, HealingAbility):
            return AbilitySerializer._serialize_healing_ability(ability)
        elif isinstance(ability, BuffAbility):
            return AbilitySerializer._serialize_buff_ability(ability)
        elif isinstance(ability, UtilityAbility):
            return AbilitySerializer._serialize_utility_ability(ability)
        else:
            raise ValueError(f"Unsupported ability type: {type(ability)}")

    @staticmethod
    def _serialize_base_ability(ability: BaseAbility) -> dict[str, Any]:
        """
        Serialize common BaseAbility fields to dictionary.

        Args:
            ability (BaseAbility): The base ability instance to serialize.

        Returns:
            dict[str, Any]: Dictionary containing common ability fields.
        """
        data = {
            "class": ability.__class__.__name__,
            "name": ability.name,
            "type": ability.action_type.name,
            "description": ability.description,
            "cooldown": ability.cooldown,
            "maximum_uses": ability.maximum_uses,
        }
        if ability.target_expr:
            data["target_expr"] = ability.target_expr
        if ability.target_restrictions is not None:
            data["target_restrictions"] = ability.target_restrictions
        if ability.effect:
            data["effect"] = ability.effect.to_dict()

        return data

    @staticmethod
    def _serialize_offensive_ability(ability: OffensiveAbility) -> dict[str, Any]:
        """
        Serialize OffensiveAbility to dictionary format.

        Args:
            ability (OffensiveAbility): The offensive ability instance to serialize.

        Returns:
            dict[str, Any]: Dictionary representation of the offensive ability.
        """
        data = AbilitySerializer._serialize_base_ability(ability)
        data["damage"] = [component.to_dict() for component in ability.damage]
        return data

    @staticmethod
    def _serialize_healing_ability(ability: HealingAbility) -> dict[str, Any]:
        """
        Serialize HealingAbility to dictionary format.

        Args:
            ability (HealingAbility): The healing ability instance to serialize.

        Returns:
            dict[str, Any]: Dictionary representation of the healing ability.
        """
        data = AbilitySerializer._serialize_base_ability(ability)
        data["heal_roll"] = ability.heal_roll
        return data

    @staticmethod
    def _serialize_buff_ability(ability: BuffAbility) -> dict[str, Any]:
        """
        Serialize BuffAbility to dictionary format.

        Args:
            ability (BuffAbility): The buff ability instance to serialize.

        Returns:
            dict[str, Any]: Dictionary representation of the buff ability.
        """
        data = AbilitySerializer._serialize_base_ability(ability)
        # Effect is guaranteed for BuffAbility
        assert ability.effect is not None, "BuffAbility must have an effect"
        data["effect"] = ability.effect.to_dict()
        return data

    @staticmethod
    def _serialize_utility_ability(ability: UtilityAbility) -> dict[str, Any]:
        """
        Serialize UtilityAbility to dictionary format.

        Args:
            ability (UtilityAbility): The utility ability instance to serialize.

        Returns:
            dict[str, Any]: Dictionary representation of the utility ability
        """
        data = AbilitySerializer._serialize_base_ability(ability)
        if ability.utility_function:
            data["utility_function"] = ability.utility_function
        return data
