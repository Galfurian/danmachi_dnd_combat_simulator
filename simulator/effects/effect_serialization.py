"""
Factory pattern implementation for effect creation and serialization.

This module provides centraliz        if isinstance(modifiers_data, dict):
            for bonus_type_str, value in modifiers_data.items():
                try:
                    bonus_type = BonusType[bonus_type_str.upper()]
                    if bonus_type == BonusType.DAMAGE and isinstance(value, dict):
                        damage_comp = DamageComponent.from_dict(value)
                        modifiers.append(Modifier(bonus_type, damage_comp))
                    else:
                        modifiers.append(Modifier(bonus_type, value))
                except (KeyError, ValueError) as e:
                    log_error(
                        f"Invalid modifier in buff '{data.get('name', 'Unknown')}': {bonus_type_str}",
                        {"bonus_type_str": bonus_type_str, "value": value},
                        e,
                    )
                    # Skip invalid modifiers rather than failing entirely
                    continues for creating and serializing
effect instances, maintaining clean separation of concerns by removing
serialization logic from individual effect classes.
"""

from typing import Any, Dict, Union, TYPE_CHECKING

from core.constants import BonusType, DamageType
from core.error_handling import log_critical, log_error
from combat.damage import DamageComponent

if TYPE_CHECKING:
    from .effect import (
        Effect,
        BuffEffect,
        DebuffEffect,
        DamageOverTimeEffect,
        HealingOverTimeEffect,
        OnTriggerEffect,
        IncapacitatingEffect,
        ModifierEffect,
        Modifier,
        TriggerCondition,
    )


class EffectDeserializer:
    """Factory for creating effect instances from dictionary data."""

    @staticmethod
    def deserialize(data: Dict[str, Any]) -> "Effect | None":
        """
        Deserialize effect data from dictionary to appropriate effect instance.

        This method dynamically creates the correct effect subclass based on
        the 'type' field in the data dictionary, with backward compatibility
        for legacy effect names.

        Args:
            data (Dict[str, Any]): Dictionary containing effect configuration data.

        Returns:
            Effect | None: Instance of the appropriate subclass, or None if not recognized.
        """
        try:
            if data is None:
                return None
                
            effect_type = data.get("type")
            if not effect_type:
                raise ValueError("Effect data must have a 'type' field")

            # Handle new effect names and legacy names for backward compatibility
            if effect_type in ["Buff", "BuffEffect"]:
                return EffectDeserializer._deserialize_buff_effect(data)
            elif effect_type in ["Debuff", "DebuffEffect"]:
                return EffectDeserializer._deserialize_debuff_effect(data)
            elif effect_type in ["DoT", "DamageOverTimeEffect"]:
                return EffectDeserializer._deserialize_damage_over_time_effect(data)
            elif effect_type in ["HoT", "HealingOverTimeEffect"]:
                return EffectDeserializer._deserialize_healing_over_time_effect(data)
            elif effect_type == "OnTriggerEffect":
                return EffectDeserializer._deserialize_on_trigger_effect(data)
            elif effect_type == "UniversalTrigger":  # Legacy name compatibility
                return EffectDeserializer._deserialize_on_trigger_effect(data)
            elif effect_type == "IncapacitatingEffect":
                return EffectDeserializer._deserialize_incapacitating_effect(data)
            elif effect_type == "OnHitTrigger":
                # Convert legacy OnHitTrigger to OnTriggerEffect
                return EffectDeserializer._convert_legacy_on_hit_trigger(data)
            elif effect_type == "OnLowHealthTrigger":
                # Convert legacy OnLowHealthTrigger to OnTriggerEffect
                return EffectDeserializer._convert_legacy_low_health_trigger(data)
            else:
                raise ValueError(f"Unknown effect type: {effect_type}")
                
        except Exception as e:
            effect_name = data.get("name", "Unknown") if data else "Unknown"
            log_critical(
                f"Error creating effect '{effect_name}': {str(e)}",
                {"effect_name": effect_name, "error": str(e)},
                e,
            )
            raise

    @staticmethod
    def _deserialize_buff_effect(data: Dict[str, Any]) -> "BuffEffect":
        """
        Create a BuffEffect instance from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary containing buff configuration data.
            
        Returns:
            BuffEffect: A BuffEffect instance.
        """
        from .effect import BuffEffect, Modifier

        # Parse modifiers
        modifiers = []
        modifiers_data = data.get("modifiers", {})
        
        if isinstance(modifiers_data, dict):
            for bonus_type_str, value in modifiers_data.items():
                try:
                    bonus_type = BonusType[bonus_type_str.upper()]
                    if bonus_type == BonusType.DAMAGE and isinstance(value, dict):
                        damage_comp = DamageComponent.from_dict(value)
                        modifiers.append(Modifier(bonus_type, damage_comp))
                    else:
                        modifiers.append(Modifier(bonus_type, value))
                except (KeyError, ValueError) as e:
                    log_error(
                        f"Invalid modifier in buff '{data.get('name', 'Unknown')}': {bonus_type_str}",
                        {"bonus_type": bonus_type_str, "value": value},
                        e,
                    )
                    # Skip invalid modifiers rather than failing entirely
                    continue
        elif isinstance(modifiers_data, list):
            for mod_data in modifiers_data:
                modifier = ModifierDeserializer.deserialize(mod_data)
                if modifier:
                    modifiers.append(modifier)

        return BuffEffect(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            modifiers=modifiers,
        )

    @staticmethod
    def _deserialize_debuff_effect(data: Dict[str, Any]) -> "DebuffEffect":
        """
        Create a DebuffEffect instance from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary containing debuff configuration data.
            
        Returns:
            DebuffEffect: A DebuffEffect instance.
        """
        from .effect import DebuffEffect, Modifier

        # Parse modifiers (same logic as BuffEffect)
        modifiers = []
        modifiers_data = data.get("modifiers", {})
        
        if isinstance(modifiers_data, dict):
            for bonus_type_str, value in modifiers_data.items():
                try:
                    bonus_type = BonusType[bonus_type_str.upper()]
                    if bonus_type == BonusType.DAMAGE and isinstance(value, dict):
                        damage_comp = DamageComponent.from_dict(value)
                        modifiers.append(Modifier(bonus_type, damage_comp))
                    else:
                        modifiers.append(Modifier(bonus_type, value))
                except (KeyError, ValueError) as e:
                    log_error(
                        f"Invalid modifier in debuff '{data.get('name', 'Unknown')}': {bonus_type_str}",
                        {"bonus_type_str": bonus_type_str, "value": value},
                        e,
                    )
                    continue
        elif isinstance(modifiers_data, list):
            for mod_data in modifiers_data:
                modifier = ModifierDeserializer.deserialize(mod_data)
                if modifier:
                    modifiers.append(modifier)

        return DebuffEffect(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            modifiers=modifiers,
        )

    @staticmethod
    def _deserialize_damage_over_time_effect(data: Dict[str, Any]) -> "DamageOverTimeEffect":
        """
        Create a DamageOverTimeEffect instance from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary containing DoT configuration data.
            
        Returns:
            DamageOverTimeEffect: A DamageOverTimeEffect instance.
        """
        from .effect import DamageOverTimeEffect

        return DamageOverTimeEffect(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            damage=DamageComponent.from_dict(data["damage"]),
        )

    @staticmethod
    def _deserialize_healing_over_time_effect(data: Dict[str, Any]) -> "HealingOverTimeEffect":
        """
        Create a HealingOverTimeEffect instance from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary containing HoT configuration data.
            
        Returns:
            HealingOverTimeEffect: A HealingOverTimeEffect instance.
        """
        from .effect import HealingOverTimeEffect

        return HealingOverTimeEffect(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            heal_per_turn=data["heal_per_turn"],
        )

    @staticmethod
    def _deserialize_on_trigger_effect(data: Dict[str, Any]) -> "OnTriggerEffect":
        """
        Create an OnTriggerEffect instance from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary containing trigger configuration data.
            
        Returns:
            OnTriggerEffect: An OnTriggerEffect instance.
        """
        from .effect import OnTriggerEffect, TriggerCondition, TriggerType, Effect

        # Deserialize trigger condition
        condition_data = data["trigger_condition"]
        trigger_type = TriggerType(condition_data["trigger_type"])
        condition = TriggerCondition(
            trigger_type=trigger_type,
            threshold=condition_data.get("threshold"),
            damage_type=None,  # Would need to resolve from string if present
            spell_category=None,  # Would need to resolve from string if present
            description=condition_data.get("description", ""),
        )

        # Deserialize trigger effects
        trigger_effects = []
        for effect_data in data.get("trigger_effects", []):
            effect = EffectDeserializer.deserialize(effect_data)
            if effect:
                trigger_effects.append(effect)

        # Deserialize damage bonuses
        damage_bonus = []
        for dmg_data in data.get("damage_bonus", []):
            damage_bonus.append(DamageComponent.from_dict(dmg_data))

        return OnTriggerEffect(
            name=data["name"],
            description=data["description"],
            max_duration=data["max_duration"],
            trigger_condition=condition,
            trigger_effects=trigger_effects,
            damage_bonus=damage_bonus,
            consumes_on_trigger=data.get("consumes_on_trigger", True),
            cooldown_turns=data.get("cooldown_turns", 0),
            max_triggers=data.get("max_triggers", -1),
        )

    @staticmethod
    def _deserialize_incapacitating_effect(data: Dict[str, Any]) -> "IncapacitatingEffect":
        """
        Create an IncapacitatingEffect instance from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary containing incapacitating effect configuration data.
            
        Returns:
            IncapacitatingEffect: An IncapacitatingEffect instance.
        """
        from .effect import IncapacitatingEffect

        return IncapacitatingEffect(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            incapacitation_type=data.get("incapacitation_type", "general"),
            save_ends=data.get("save_ends", False),
            save_dc=data.get("save_dc", 0),
            save_stat=data.get("save_stat", "CON"),
        )

    @staticmethod
    def _convert_legacy_on_hit_trigger(data: Dict[str, Any]) -> "OnTriggerEffect":
        """
        Convert legacy OnHitTrigger data to OnTriggerEffect.
        
        Args:
            data (Dict[str, Any]): Legacy OnHitTrigger data.
            
        Returns:
            OnTriggerEffect: Converted OnTriggerEffect instance.
        """
        from .effect import OnTriggerEffect, TriggerCondition, TriggerType

        # Create on-hit trigger condition
        condition = TriggerCondition(
            trigger_type=TriggerType.ON_HIT,
            description="when hitting with an attack"
        )

        # Parse legacy trigger effects
        trigger_effects = []
        for effect_data in data.get("trigger_effects", []):
            effect = EffectDeserializer.deserialize(effect_data)
            if effect:
                trigger_effects.append(effect)

        # Parse legacy damage bonus
        damage_bonus = []
        for dmg_data in data.get("damage_bonus", []):
            damage_bonus.append(DamageComponent.from_dict(dmg_data))

        return OnTriggerEffect(
            name=data["name"],
            description=data["description"],
            max_duration=data["max_duration"],
            trigger_condition=condition,
            trigger_effects=trigger_effects,
            damage_bonus=damage_bonus,
            consumes_on_trigger=data.get("consumes_on_trigger", True),
            cooldown_turns=0,
            max_triggers=-1,
        )

    @staticmethod
    def _convert_legacy_low_health_trigger(data: Dict[str, Any]) -> "OnTriggerEffect":
        """
        Convert legacy OnLowHealthTrigger data to OnTriggerEffect.
        
        Args:
            data (Dict[str, Any]): Legacy OnLowHealthTrigger data.
            
        Returns:
            OnTriggerEffect: Converted OnTriggerEffect instance.
        """
        from .effect import OnTriggerEffect, TriggerCondition, TriggerType

        # Create low health trigger condition
        threshold = data.get("hp_threshold_percent", 0.25)
        condition = TriggerCondition(
            trigger_type=TriggerType.ON_LOW_HEALTH,
            threshold=threshold,
            description=f"when HP drops below {threshold * 100:.0f}%"
        )

        # Parse legacy trigger effects
        trigger_effects = []
        for effect_data in data.get("trigger_effects", []):
            effect = EffectDeserializer.deserialize(effect_data)
            if effect:
                trigger_effects.append(effect)

        return OnTriggerEffect(
            name=data["name"],
            description=data["description"],
            max_duration=0,  # Low health triggers are usually permanent
            trigger_condition=condition,
            trigger_effects=trigger_effects,
            damage_bonus=[],
            consumes_on_trigger=data.get("consumes_on_trigger", True),
            cooldown_turns=0,
            max_triggers=-1,
        )


class EffectSerializer:
    """Serializer for converting effect instances to dictionary format."""

    @staticmethod
    def serialize(effect: "Effect") -> Dict[str, Any]:
        """
        Serialize effect instance to dictionary format.

        This method handles all effect types and delegates to the appropriate
        subclass serialization methods.

        Args:
            effect (Effect): The effect instance to serialize.

        Returns:
            Dict[str, Any]: Dictionary representation of the effect.
        """
        # Import effect classes for isinstance checks
        from .effect import (
            BuffEffect,
            DebuffEffect,
            DamageOverTimeEffect,
            HealingOverTimeEffect,
            OnTriggerEffect,
            IncapacitatingEffect,
        )

        if isinstance(effect, BuffEffect):
            return EffectSerializer._serialize_buff_effect(effect)
        elif isinstance(effect, DebuffEffect):
            return EffectSerializer._serialize_debuff_effect(effect)
        elif isinstance(effect, DamageOverTimeEffect):
            return EffectSerializer._serialize_damage_over_time_effect(effect)
        elif isinstance(effect, HealingOverTimeEffect):
            return EffectSerializer._serialize_healing_over_time_effect(effect)
        elif isinstance(effect, OnTriggerEffect):
            return EffectSerializer._serialize_on_trigger_effect(effect)
        elif isinstance(effect, IncapacitatingEffect):
            return EffectSerializer._serialize_incapacitating_effect(effect)
        else:
            raise ValueError(f"Unsupported effect type: {type(effect)}")

    @staticmethod
    def _serialize_base_effect(effect: "Effect") -> Dict[str, Any]:
        """
        Serialize common base effect fields.
        
        Args:
            effect (Effect): The effect instance to serialize.
            
        Returns:
            Dict[str, Any]: Dictionary with common effect fields.
        """
        return {
            "type": effect.__class__.__name__,
            "name": effect.name,
            "description": effect.description,
            "max_duration": effect.max_duration,
        }

    @staticmethod
    def _serialize_buff_effect(effect: "BuffEffect") -> Dict[str, Any]:
        """
        Serialize BuffEffect to dictionary format.
        
        Args:
            effect (BuffEffect): The BuffEffect instance to serialize.
            
        Returns:
            Dict[str, Any]: Dictionary representation of the BuffEffect.
        """
        data = EffectSerializer._serialize_base_effect(effect)
        data["modifiers"] = [
            ModifierSerializer.serialize(modifier) for modifier in effect.modifiers
        ]
        return data

    @staticmethod
    def _serialize_debuff_effect(effect: "DebuffEffect") -> Dict[str, Any]:
        """
        Serialize DebuffEffect to dictionary format.
        
        Args:
            effect (DebuffEffect): The DebuffEffect instance to serialize.
            
        Returns:
            Dict[str, Any]: Dictionary representation of the DebuffEffect.
        """
        data = EffectSerializer._serialize_base_effect(effect)
        data["modifiers"] = [
            ModifierSerializer.serialize(modifier) for modifier in effect.modifiers
        ]
        return data

    @staticmethod
    def _serialize_damage_over_time_effect(effect: "DamageOverTimeEffect") -> Dict[str, Any]:
        """
        Serialize DamageOverTimeEffect to dictionary format.
        
        Args:
            effect (DamageOverTimeEffect): The DamageOverTimeEffect to serialize.
            
        Returns:
            Dict[str, Any]: Dictionary representation of the DamageOverTimeEffect.
        """
        data = EffectSerializer._serialize_base_effect(effect)
        data["damage"] = effect.damage.to_dict()
        return data

    @staticmethod
    def _serialize_healing_over_time_effect(effect: "HealingOverTimeEffect") -> Dict[str, Any]:
        """
        Serialize HealingOverTimeEffect to dictionary format.
        
        Args:
            effect (HealingOverTimeEffect): The HealingOverTimeEffect to serialize.
            
        Returns:
            Dict[str, Any]: Dictionary representation of the HealingOverTimeEffect.
        """
        data = EffectSerializer._serialize_base_effect(effect)
        data["heal_per_turn"] = effect.heal_per_turn
        return data

    @staticmethod
    def _serialize_on_trigger_effect(effect: "OnTriggerEffect") -> Dict[str, Any]:
        """
        Serialize OnTriggerEffect to dictionary format.
        
        Args:
            effect (OnTriggerEffect): The OnTriggerEffect to serialize.
            
        Returns:
            Dict[str, Any]: Dictionary representation of the OnTriggerEffect.
        """
        data = EffectSerializer._serialize_base_effect(effect)
        data["trigger_condition"] = TriggerConditionSerializer.serialize(effect.trigger_condition)
        data["trigger_effects"] = [
            EffectSerializer.serialize(trigger_effect) for trigger_effect in effect.trigger_effects
        ]
        data["damage_bonus"] = [
            dmg_comp.to_dict() for dmg_comp in effect.damage_bonus
        ]
        data["consumes_on_trigger"] = effect.consumes_on_trigger
        data["cooldown_turns"] = effect.cooldown_turns
        data["max_triggers"] = effect.max_triggers
        return data

    @staticmethod
    def _serialize_incapacitating_effect(effect: "IncapacitatingEffect") -> Dict[str, Any]:
        """
        Serialize IncapacitatingEffect to dictionary format.
        
        Args:
            effect (IncapacitatingEffect): The IncapacitatingEffect to serialize.
            
        Returns:
            Dict[str, Any]: Dictionary representation of the IncapacitatingEffect.
        """
        data = EffectSerializer._serialize_base_effect(effect)
        data["incapacitation_type"] = effect.incapacitation_type
        data["save_ends"] = effect.save_ends
        data["save_dc"] = effect.save_dc
        data["save_stat"] = effect.save_stat
        return data


class ModifierDeserializer:
    """Factory for creating modifier instances from dictionary data."""

    @staticmethod
    def deserialize(data: Dict[str, Any]) -> "Modifier | None":
        """
        Deserialize modifier data from dictionary to Modifier instance.

        Args:
            data (Dict[str, Any]): Dictionary containing modifier configuration data.

        Returns:
            Modifier | None: Modifier instance, or None if invalid.
        """
        from .effect import Modifier

        try:
            bonus_type = BonusType[data["bonus_type"].upper()]
            value = data["value"]
            
            if bonus_type == BonusType.DAMAGE and isinstance(value, dict):
                value = DamageComponent.from_dict(value)
            
            return Modifier(bonus_type, value)
        except (KeyError, ValueError) as e:
            log_error(
                f"Invalid modifier data: {data}",
                {"modifier_data": data},
                e,
            )
            return None


class ModifierSerializer:
    """Serializer for converting modifier instances to dictionary format."""

    @staticmethod
    def serialize(modifier: "Modifier") -> Dict[str, Any]:
        """
        Serialize modifier instance to dictionary format.

        Args:
            modifier (Modifier): The modifier instance to serialize.

        Returns:
            Dict[str, Any]: Dictionary representation of the modifier.
        """
        data: Dict[str, Any] = {
            "bonus_type": modifier.bonus_type.name,
        }

        if isinstance(modifier.value, DamageComponent):
            data["value"] = modifier.value.to_dict()
        else:
            data["value"] = modifier.value

        return data


class TriggerConditionSerializer:
    """Handles serialization of TriggerCondition objects to/from JSON."""

    @staticmethod
    def serialize(condition: "TriggerCondition") -> Dict[str, Any]:
        """Convert a TriggerCondition to a JSON-serializable dictionary."""
        data: Dict[str, Any] = {
            "trigger_type": condition.trigger_type.value,
            "description": condition.description,
        }

        if condition.threshold is not None:
            data["threshold"] = condition.threshold
        if condition.damage_type is not None:
            data["damage_type"] = (
                condition.damage_type.name
                if hasattr(condition.damage_type, "name")
                else str(condition.damage_type)
            )
        if condition.spell_category is not None:
            data["spell_category"] = (
                condition.spell_category.name
                if hasattr(condition.spell_category, "name")
                else str(condition.spell_category)
            )

        # Note: custom_condition functions cannot be serialized to JSON
        # They would need to be recreated programmatically

        return data

    @staticmethod
    def deserialize(data: Dict[str, Any]) -> "TriggerCondition":
        """Create a TriggerCondition from a JSON dictionary."""
        from .effect import TriggerCondition, TriggerType

        trigger_type = TriggerType(data["trigger_type"])

        # Handle optional fields
        threshold = data.get("threshold")
        damage_type = None
        spell_category = None

        # These would need to be resolved from string names to actual enum values
        # This would typically be done by the content loading system
        if "damage_type" in data:
            # damage_type = DamageType[data["damage_type"]]  # Example
            pass
        if "spell_category" in data:
            # spell_category = SpellCategory[data["spell_category"]]  # Example
            pass

        return TriggerCondition(
            trigger_type=trigger_type,
            threshold=threshold,
            damage_type=damage_type,
            spell_category=spell_category,
            description=data.get("description", ""),
        )
