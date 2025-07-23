"""
Factory pattern implementation for effect creation and serialization.

This module provides centralized serialization and deserialization for all effect types,
following the same pattern as ability_serializer.py for clean separation of concerns.
"""

from typing import Any, Optional

from core.constants import BonusType
from core.error_handling import log_error, log_warning
from combat.damage import DamageComponent

# Import all effect classes from their new locations
from .base_effect import Effect, Modifier
from .modifier_effect import ModifierEffect, BuffEffect, DebuffEffect
from .damage_over_time_effect import DamageOverTimeEffect
from .healing_over_time_effect import HealingOverTimeEffect
from .incapacitating_effect import IncapacitatingEffect
from .trigger_effect import TriggerType, TriggerCondition, TriggerEffect


class EffectSerializer:
    """Centralized serialization for all effect types."""

    @staticmethod
    def serialize(effect: Effect) -> dict[str, Any]:
        """
        Serialize an effect to dictionary format.

        Args:
            effect (Effect): The effect to serialize.

        Returns:
            dict[str, Any]: Dictionary representation of the effect.
        """
        if isinstance(effect, BuffEffect):
            return EffectSerializer._serialize_buff(effect)
        elif isinstance(effect, DebuffEffect):
            return EffectSerializer._serialize_debuff(effect)
        elif isinstance(effect, DamageOverTimeEffect):
            return EffectSerializer._serialize_damage_over_time(effect)
        elif isinstance(effect, HealingOverTimeEffect):
            return EffectSerializer._serialize_healing_over_time(effect)
        elif isinstance(effect, TriggerEffect):
            return EffectSerializer._serialize_on_trigger(effect)
        elif isinstance(effect, IncapacitatingEffect):
            return EffectSerializer._serialize_incapacitating(effect)
        elif isinstance(effect, ModifierEffect):
            return EffectSerializer._serialize_modifier(effect)
        else:
            # Base effect serialization
            return {
                "class": "Effect",
                "name": effect.name,
                "description": effect.description,
                "max_duration": effect.max_duration,
            }

    @staticmethod
    def _serialize_buff(effect: BuffEffect) -> dict[str, Any]:
        """Serialize a BuffEffect."""
        return {
            "class": "BuffEffect",
            "name": effect.name,
            "description": effect.description,
            "max_duration": effect.max_duration,
            "modifiers": [ModifierSerializer.serialize(mod) for mod in effect.modifiers],
        }

    @staticmethod
    def _serialize_debuff(effect: DebuffEffect) -> dict[str, Any]:
        """Serialize a DebuffEffect."""
        return {
            "class": "DebuffEffect",
            "name": effect.name,
            "description": effect.description,
            "max_duration": effect.max_duration,
            "modifiers": [ModifierSerializer.serialize(mod) for mod in effect.modifiers],
        }

    @staticmethod
    def _serialize_modifier(effect: ModifierEffect) -> dict[str, Any]:
        """Serialize a ModifierEffect."""
        return {
            "class": "ModifierEffect",
            "name": effect.name,
            "description": effect.description,
            "max_duration": effect.max_duration,
            "modifiers": [ModifierSerializer.serialize(mod) for mod in effect.modifiers],
        }

    @staticmethod
    def _serialize_damage_over_time(effect: DamageOverTimeEffect) -> dict[str, Any]:
        """Serialize a DamageOverTimeEffect."""
        return {
            "class": "DamageOverTimeEffect",
            "name": effect.name,
            "description": effect.description,
            "max_duration": effect.max_duration,
            "damage": effect.damage.to_dict(),
        }

    @staticmethod
    def _serialize_healing_over_time(effect: HealingOverTimeEffect) -> dict[str, Any]:
        """Serialize a HealingOverTimeEffect."""
        return {
            "class": "HealingOverTimeEffect",
            "name": effect.name,
            "description": effect.description,
            "max_duration": effect.max_duration,
            "heal_per_turn": effect.heal_per_turn,
        }

    @staticmethod
    def _serialize_on_trigger(effect: TriggerEffect) -> dict[str, Any]:
        """Serialize an TriggerEffect."""
        return {
            "class": "TriggerEffect",
            "name": effect.name,
            "description": effect.description,
            "max_duration": effect.max_duration,
            "trigger_condition": TriggerConditionSerializer.serialize(effect.trigger_condition),
            "trigger_effects": [EffectSerializer.serialize(te) for te in effect.trigger_effects],
            "damage_bonus": [dmg.to_dict() for dmg in effect.damage_bonus],
            "consumes_on_trigger": effect.consumes_on_trigger,
            "cooldown_turns": effect.cooldown_turns,
            "max_triggers": effect.max_triggers,
        }

    @staticmethod
    def _serialize_incapacitating(effect: IncapacitatingEffect) -> dict[str, Any]:
        """Serialize an IncapacitatingEffect."""
        return {
            "class": "IncapacitatingEffect",
            "name": effect.name,
            "description": effect.description,
            "max_duration": effect.max_duration,
            "incapacitation_type": effect.incapacitation_type,
            "save_ends": effect.save_ends,
            "save_dc": effect.save_dc,
            "save_stat": effect.save_stat,
        }


class EffectDeserializer:
    """Factory for creating effect instances from dictionary data."""

    @staticmethod
    def deserialize(data: dict[str, Any]) -> Effect | None:
        """
        Deserialize effect data from dictionary to appropriate effect instance.

        Args:
            data (dict[str, Any]): Dictionary containing effect data.

        Returns:
            Effect | None: The deserialized effect instance, or None if deserialization fails.
        """
        if not isinstance(data, dict):
            log_error("Effect data must be a dictionary", {"data": data})
            return None

        # Support only "class" field
        effect_class = data.get("class")
        if not effect_class:
            log_error("Effect data must have 'class' field", {"data": data})
            return None

        try:
            # Use only the new class names
            if effect_class == "BuffEffect":
                return EffectDeserializer._deserialize_buff(data)
            elif effect_class == "DebuffEffect":
                return EffectDeserializer._deserialize_debuff(data)
            elif effect_class == "DamageOverTimeEffect":
                return EffectDeserializer._deserialize_damage_over_time(data)
            elif effect_class == "HealingOverTimeEffect":
                return EffectDeserializer._deserialize_healing_over_time(data)
            elif effect_class == "TriggerEffect":
                return EffectDeserializer._deserialize_on_trigger(data)
            elif effect_class == "IncapacitatingEffect":
                return EffectDeserializer._deserialize_incapacitating(data)
            elif effect_class == "ModifierEffect":
                return EffectDeserializer._deserialize_modifier(data)
            else:
                log_warning(f"Unknown effect class: {effect_class}", {"data": data})
                return None

        except Exception as e:
            log_error(f"Failed to deserialize effect: {str(e)}", {"data": data}, e)
            return None

    @staticmethod
    def _deserialize_buff(data: dict[str, Any]) -> BuffEffect:
        """Deserialize a BuffEffect."""
        modifiers = ModifierDeserializer.deserialize_list(data.get("modifiers", []))
        return BuffEffect(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            modifiers=modifiers,
        )

    @staticmethod
    def _deserialize_debuff(data: dict[str, Any]) -> DebuffEffect:
        """Deserialize a DebuffEffect."""
        modifiers = ModifierDeserializer.deserialize_list(data.get("modifiers", []))
        return DebuffEffect(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            modifiers=modifiers,
        )

    @staticmethod
    def _deserialize_modifier(data: dict[str, Any]) -> ModifierEffect:
        """Deserialize a ModifierEffect."""
        modifiers = ModifierDeserializer.deserialize_list(data.get("modifiers", []))
        return ModifierEffect(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            modifiers=modifiers,
        )

    @staticmethod
    def _deserialize_damage_over_time(data: dict[str, Any]) -> DamageOverTimeEffect:
        """Deserialize a DamageOverTimeEffect."""
        damage_data = data.get("damage", {})
        damage = DamageComponent.from_dict(damage_data) if damage_data else None
        if not damage:
            raise ValueError(f"Invalid damage data for DoT effect: {damage_data}")

        return DamageOverTimeEffect(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 1),
            damage=damage,
        )

    @staticmethod
    def _deserialize_healing_over_time(data: dict[str, Any]) -> HealingOverTimeEffect:
        """Deserialize a HealingOverTimeEffect."""
        return HealingOverTimeEffect(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 1),
            heal_per_turn=data.get("heal_per_turn", "1"),
        )

    @staticmethod
    def _deserialize_on_trigger(data: dict[str, Any]) -> TriggerEffect:
        """Deserialize an TriggerEffect."""
        # Deserialize trigger condition
        trigger_condition_data = data.get("trigger_condition", {})
        trigger_condition = TriggerConditionDeserializer.deserialize(trigger_condition_data)
        if not trigger_condition:
            raise ValueError(f"Invalid trigger condition data: {trigger_condition_data}")

        # Deserialize trigger effects
        trigger_effects = []
        for te_data in data.get("trigger_effects", []):
            effect = EffectDeserializer.deserialize(te_data)
            if effect:
                trigger_effects.append(effect)

        # Deserialize damage bonuses
        damage_bonus = []
        for dmg_data in data.get("damage_bonus", []):
            damage = DamageComponent.from_dict(dmg_data)
            if damage:
                damage_bonus.append(damage)

        return TriggerEffect(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            trigger_condition=trigger_condition,
            trigger_effects=trigger_effects,
            damage_bonus=damage_bonus,
            consumes_on_trigger=data.get("consumes_on_trigger", True),
            cooldown_turns=data.get("cooldown_turns", 0),
            max_triggers=data.get("max_triggers", -1),
        )

    @staticmethod
    def _deserialize_incapacitating(data: dict[str, Any]) -> IncapacitatingEffect:
        """Deserialize an IncapacitatingEffect."""
        return IncapacitatingEffect(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 1),
            incapacitation_type=data.get("incapacitation_type", "general"),
            save_ends=data.get("save_ends", False),
            save_dc=data.get("save_dc", 0),
            save_stat=data.get("save_stat", "CON"),
        )


class ModifierSerializer:
    """Handles serialization of Modifier instances."""

    @staticmethod
    def serialize(modifier: Modifier) -> dict[str, Any]:
        """
        Serialize a modifier to dictionary format.

        Args:
            modifier (Modifier): The modifier to serialize.

        Returns:
            dict[str, Any]: Dictionary representation of the modifier.
        """
        result: dict[str, Any] = {
            "bonus_type": modifier.bonus_type.name,
        }

        if isinstance(modifier.value, DamageComponent):
            result["value"] = modifier.value.to_dict()
        else:
            result["value"] = modifier.value

        return result


class ModifierDeserializer:
    """Handles deserialization of Modifier instances."""

    @staticmethod
    def deserialize(data: dict[str, Any]) -> Modifier | None:
        """
        Deserialize modifier data from dictionary.

        Args:
            data (dict[str, Any]): Dictionary containing modifier data.

        Returns:
            Modifier | None: The deserialized modifier, or None if deserialization fails.
        """
        try:
            bonus_type = BonusType[data["bonus_type"]]
            value = data["value"]

            if bonus_type == BonusType.DAMAGE and isinstance(value, dict):
                damage_comp = DamageComponent.from_dict(value)
                return Modifier(bonus_type, damage_comp)
            else:
                return Modifier(bonus_type, value)

        except (KeyError, ValueError) as e:
            log_error(f"Failed to deserialize modifier: {str(e)}", {"data": data}, e)
            return None

    @staticmethod
    def deserialize_list(modifiers_data: list[dict[str, Any]]) -> list[Modifier]:
        """
        Deserialize a list of modifiers from dictionary data.
        
        Format: [{"bonus_type": "ATTACK", "value": "1D4"}]

        Args:
            modifiers_data: List of modifier data.

        Returns:
            list[Modifier]: List of deserialized modifiers.
        """
        modifiers = []
        
        # Handle only new format: [{"bonus_type": "ATTACK", "value": "1D4"}]
        if isinstance(modifiers_data, list):
            for mod_data in modifiers_data:
                modifier = ModifierDeserializer.deserialize(mod_data)
                if modifier:
                    modifiers.append(modifier)
        else:
            log_error("Modifiers data must be a list", {"modifiers_data": modifiers_data})
                    
        return modifiers


class TriggerConditionSerializer:
    """Handles serialization of TriggerCondition instances."""

    @staticmethod
    def serialize(condition: TriggerCondition) -> dict[str, Any]:
        """
        Serialize a trigger condition to dictionary format.

        Args:
            condition (TriggerCondition): The trigger condition to serialize.

        Returns:
            dict[str, Any]: Dictionary representation of the trigger condition.
        """
        result: dict[str, Any] = {
            "trigger_type": condition.trigger_type.value,
            "description": condition.description,
        }

        if condition.threshold is not None:
            result["threshold"] = condition.threshold

        if condition.damage_type is not None:
            result["damage_type"] = condition.damage_type.name if hasattr(condition.damage_type, 'name') else str(condition.damage_type)

        if condition.spell_category is not None:
            result["spell_category"] = condition.spell_category.name if hasattr(condition.spell_category, 'name') else str(condition.spell_category)

        # Note: custom_condition functions cannot be serialized
        if condition.custom_condition is not None:
            result["has_custom_condition"] = True

        return result


class TriggerConditionDeserializer:
    """Handles deserialization of TriggerCondition instances."""

    @staticmethod
    def deserialize(data: dict[str, Any]) -> TriggerCondition | None:
        """
        Deserialize trigger condition data from dictionary.

        Args:
            data (dict[str, Any]): Dictionary containing trigger condition data.

        Returns:
            TriggerCondition | None: The deserialized trigger condition, or None if deserialization fails.
        """
        try:
            trigger_type = TriggerType(data["trigger_type"])
            
            return TriggerCondition(
                trigger_type=trigger_type,
                threshold=data.get("threshold"),
                damage_type=data.get("damage_type"),  # Would need to convert string back to enum
                spell_category=data.get("spell_category"),  # Would need to convert string back to enum
                custom_condition=None,  # Cannot deserialize custom functions
                description=data.get("description", ""),
            )

        except (KeyError, ValueError) as e:
            log_error(f"Failed to deserialize trigger condition: {str(e)}", {"data": data}, e)
            return None
