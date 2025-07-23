"""
Factory pattern implementation for effect creation and serialization.

This module provides centralized factory classes for creating and serializing
effect instances, maintaining clean separation of concerns by removing
serialization logic from individual effect classes.
"""

from typing import Any, Dict, Union, TYPE_CHECKING
from core.constants import BonusType
from combat.damage import DamageComponent

if TYPE_CHECKING:
    from .effect import (
        Effect,
        Buff,
        Debuff,
        DoT,
        HoT,
        OnHitTrigger,
        OnLowHealthTrigger,
        IncapacitatingEffect,
        Modifier,
    )


class EffectDeserializer:
    """Factory for creating effect instances from dictionary data."""

    @staticmethod
    def deserialize(data: Dict[str, Any]) -> Any | None:
        """
        Deserialize effect data from dictionary to appropriate effect instance.

        This method dynamically creates the correct effect subclass based on
        the 'type' field in the data dictionary.

        Args:
            data: Dictionary containing effect configuration data.

        Returns:
            Effect instance of the appropriate subclass, or None if not recognized.
        """
        try:
            assert data is not None, "Data must not be None."
            effect_type = data.get("type")

            if effect_type == "Buff":
                return EffectDeserializer._deserialize_buff(data)
            elif effect_type == "Debuff":
                return EffectDeserializer._deserialize_debuff(data)
            elif effect_type == "DoT":
                return EffectDeserializer._deserialize_dot(data)
            elif effect_type == "HoT":
                return EffectDeserializer._deserialize_hot(data)
            elif effect_type == "OnHitTrigger":
                return EffectDeserializer._deserialize_on_hit_trigger(data)
            elif effect_type == "OnLowHealthTrigger":
                return EffectDeserializer._deserialize_on_low_health_trigger(data)
            elif effect_type == "IncapacitatingEffect":
                return EffectDeserializer._deserialize_incapacitating_effect(data)
            else:
                raise ValueError(f"Unknown effect type: {effect_type}")
        except Exception as e:
            effect_name = data.get("name", "Unknown")
            raise ValueError(f"Error creating effect '{effect_name}': {str(e)}") from e

    @staticmethod
    def _deserialize_buff(data: Dict[str, Any]) -> "Buff":
        """
        Create a Buff instance from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary containing buff configuration data.
            
        Returns:
            Buff: A Buff effect instance.
        """
        from .effect import Buff, Modifier

        modifiers = []
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
                modifiers = [
                    ModifierDeserializer.deserialize(mod_data)
                    for mod_data in modifier_data
                ]

        return Buff(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            modifiers=modifiers,
        )

    @staticmethod
    def _deserialize_debuff(data: Dict[str, Any]) -> "Debuff":
        """
        Create a Debuff instance from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary containing debuff configuration data.
            
        Returns:
            Debuff: A Debuff effect instance.
        """
        from .effect import Debuff, Modifier

        modifiers = []
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
                modifiers = [
                    ModifierDeserializer.deserialize(mod_data)
                    for mod_data in modifier_data
                ]

        return Debuff(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            modifiers=modifiers,
        )

    @staticmethod
    def _deserialize_dot(data: Dict[str, Any]) -> "DoT":
        """
        Create a DoT (Damage over Time) instance from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary containing DoT configuration data.
            
        Returns:
            DoT: A DoT effect instance.
        """
        from .effect import DoT

        return DoT(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            damage=DamageComponent.from_dict(data["damage"]),
        )

    @staticmethod
    def _deserialize_hot(data: Dict[str, Any]) -> "HoT":
        """
        Create a HoT (Heal over Time) instance from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary containing HoT configuration data.
            
        Returns:
            HoT: A HoT effect instance.
        """
        from .effect import HoT

        return HoT(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            heal_per_turn=data["heal_per_turn"],
        )

    @staticmethod
    def _deserialize_on_hit_trigger(data: Dict[str, Any]) -> "OnHitTrigger":
        """
        Create an OnHitTrigger instance from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary containing OnHitTrigger configuration data.
            
        Returns:
            OnHitTrigger: An OnHitTrigger effect instance.
        """
        from .effect import OnHitTrigger

        # Parse trigger effects
        trigger_effects = []
        for effect_data in data.get("trigger_effects", []):
            trigger_effects.append(EffectDeserializer.deserialize(effect_data))

        # Parse damage bonus components
        damage_bonus = []
        for damage_data in data.get("damage_bonus", []):
            damage_bonus.append(DamageComponent.from_dict(damage_data))

        return OnHitTrigger(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            trigger_effects=trigger_effects,
            damage_bonus=damage_bonus,
            consumes_on_trigger=data.get("consumes_on_trigger", True),
        )

    @staticmethod
    def _deserialize_on_low_health_trigger(
        data: Dict[str, Any],
    ) -> "OnLowHealthTrigger":
        """
        Create an OnLowHealthTrigger instance from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary containing OnLowHealthTrigger configuration data.
            
        Returns:
            OnLowHealthTrigger: An OnLowHealthTrigger effect instance.
        """
        from .effect import OnLowHealthTrigger

        # Parse trigger effects
        trigger_effects = []
        for effect_data in data.get("trigger_effects", []):
            trigger_effects.append(EffectDeserializer.deserialize(effect_data))

        # Parse damage bonus components
        damage_bonus = []
        for damage_data in data.get("damage_bonus", []):
            damage_bonus.append(DamageComponent.from_dict(damage_data))

        trigger = OnLowHealthTrigger(
            name=data["name"],
            description=data.get("description", ""),
            hp_threshold_percent=data.get("hp_threshold_percent", 0.25),
            trigger_effects=trigger_effects,
            damage_bonus=damage_bonus,
            consumes_on_trigger=data.get("consumes_on_trigger", True),
        )

        # Restore triggered state if loading from save
        trigger.has_triggered = data.get("has_triggered", False)

        return trigger

    @staticmethod
    def _deserialize_incapacitating_effect(
        data: Dict[str, Any],
    ) -> "IncapacitatingEffect":
        """
        Create an IncapacitatingEffect instance from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary containing IncapacitatingEffect configuration data.
            
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


class EffectSerializer:
    """Serializer for converting effect instances to dictionary format."""

    @staticmethod
    def serialize(effect: "Effect") -> Dict[str, Any]:
        """
        Serialize effect instance to dictionary format.

        This method handles common fields for all effect types and delegates
        specific serialization to the appropriate subclass methods.

        Args:
            effect (Effect): The effect instance to serialize.

        Returns:
            Dict[str, Any]: Dictionary representation of the effect.
        """
        # Import effect classes for isinstance checks
        from .effect import (
            Buff,
            Debuff,
            DoT,
            HoT,
            OnHitTrigger,
            OnLowHealthTrigger,
            IncapacitatingEffect,
        )

        if isinstance(effect, Buff):
            return EffectSerializer._serialize_buff(effect)
        elif isinstance(effect, Debuff):
            return EffectSerializer._serialize_debuff(effect)
        elif isinstance(effect, DoT):
            return EffectSerializer._serialize_dot(effect)
        elif isinstance(effect, HoT):
            return EffectSerializer._serialize_hot(effect)
        elif isinstance(effect, OnHitTrigger):
            return EffectSerializer._serialize_on_hit_trigger(effect)
        elif isinstance(effect, OnLowHealthTrigger):
            return EffectSerializer._serialize_on_low_health_trigger(effect)
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
    def _serialize_buff(effect: "Buff") -> Dict[str, Any]:
        """
        Serialize Buff to dictionary.
        
        Args:
            effect (Buff): The buff effect to serialize.
            
        Returns:
            Dict[str, Any]: Dictionary representation of the buff.
        """
        data = EffectSerializer._serialize_base_effect(effect)
        data["modifiers"] = [
            ModifierSerializer.serialize(modifier) for modifier in effect.modifiers
        ]
        return data

    @staticmethod
    def _serialize_debuff(effect: "Debuff") -> Dict[str, Any]:
        """
        Serialize Debuff to dictionary.
        
        Args:
            effect (Debuff): The debuff effect to serialize.
            
        Returns:
            Dict[str, Any]: Dictionary representation of the debuff.
        """
        data = EffectSerializer._serialize_base_effect(effect)
        data["modifiers"] = [
            ModifierSerializer.serialize(modifier) for modifier in effect.modifiers
        ]
        return data

    @staticmethod
    def _serialize_dot(effect: "DoT") -> Dict[str, Any]:
        """
        Serialize DoT (Damage over Time) to dictionary.
        
        Args:
            effect (DoT): The DoT effect to serialize.
            
        Returns:
            Dict[str, Any]: Dictionary representation of the DoT effect.
        """
        data = EffectSerializer._serialize_base_effect(effect)
        data["damage"] = effect.damage.to_dict()
        return data

    @staticmethod
    def _serialize_hot(effect: "HoT") -> Dict[str, Any]:
        """
        Serialize HoT (Heal over Time) to dictionary.
        
        Args:
            effect (HoT): The HoT effect to serialize.
            
        Returns:
            Dict[str, Any]: Dictionary representation of the HoT effect.
        """
        data = EffectSerializer._serialize_base_effect(effect)
        data["heal_per_turn"] = effect.heal_per_turn
        return data

    @staticmethod
    def _serialize_on_hit_trigger(effect: "OnHitTrigger") -> Dict[str, Any]:
        """
        Serialize OnHitTrigger to dictionary.
        
        Args:
            effect (OnHitTrigger): The OnHitTrigger effect to serialize.
            
        Returns:
            Dict[str, Any]: Dictionary representation of the OnHitTrigger effect.
        """
        data = EffectSerializer._serialize_base_effect(effect)
        data["trigger_effects"] = [
            EffectSerializer.serialize(trigger_effect)
            for trigger_effect in effect.trigger_effects
        ]
        data["damage_bonus"] = [damage.to_dict() for damage in effect.damage_bonus]
        data["consumes_on_trigger"] = effect.consumes_on_trigger
        return data

    @staticmethod
    def _serialize_on_low_health_trigger(effect: "OnLowHealthTrigger") -> Dict[str, Any]:
        """
        Serialize OnLowHealthTrigger to dictionary.
        
        Args:
            effect (OnLowHealthTrigger): The OnLowHealthTrigger effect to serialize.
            
        Returns:
            Dict[str, Any]: Dictionary representation of the OnLowHealthTrigger effect.
        """
        data = EffectSerializer._serialize_base_effect(effect)
        data["trigger_effects"] = [
            EffectSerializer.serialize(trigger_effect)
            for trigger_effect in effect.trigger_effects
        ]
        data["damage_bonus"] = [damage.to_dict() for damage in effect.damage_bonus]
        data["consumes_on_trigger"] = effect.consumes_on_trigger
        data["hp_threshold_percent"] = effect.hp_threshold_percent
        data["has_triggered"] = effect.has_triggered
        return data

    @staticmethod
    def _serialize_incapacitating_effect(effect: "IncapacitatingEffect") -> Dict[str, Any]:
        """
        Serialize IncapacitatingEffect to dictionary.
        
        Args:
            effect (IncapacitatingEffect): The IncapacitatingEffect to serialize.
            
        Returns:
            Dict[str, Any]: Dictionary representation of the IncapacitatingEffect.
        """
        data = EffectSerializer._serialize_base_effect(effect)
        data.update(
            {
                "incapacitation_type": effect.incapacitation_type,
                "save_ends": effect.save_ends,
                "save_dc": effect.save_dc,
                "save_stat": effect.save_stat,
            }
        )
        return data


class ModifierDeserializer:
    """Factory for creating modifier instances from dictionary data."""

    @staticmethod
    def deserialize(data: Dict[str, Any]) -> "Modifier":
        """
        Create a Modifier instance from a dictionary representation.
        
        Args:
            data (Dict[str, Any]): Dictionary containing modifier configuration data.
            
        Returns:
            Modifier: A Modifier instance.
            
        Raises:
            ValueError: If the bonus type is unknown.
        """
        from .effect import Modifier

        assert data is not None, "Data must not be None."

        bonus_type = BonusType[data["bonus_type"].upper()]
        value_data = data["value"]

        if bonus_type == BonusType.DAMAGE:
            value = DamageComponent.from_dict(value_data)
        elif bonus_type == BonusType.ATTACK:
            value = str(value_data)
        elif bonus_type in [
            BonusType.HP,
            BonusType.MIND,
            BonusType.AC,
            BonusType.INITIATIVE,
        ]:
            # Try to convert to int if possible, otherwise keep as string
            try:
                value = int(value_data)
            except (ValueError, TypeError):
                value = str(value_data)
        else:
            raise ValueError(f"Unknown bonus type: {bonus_type}")

        return Modifier(bonus_type, value)


class ModifierSerializer:
    """Serializer for converting modifier instances to dictionary format."""

    @staticmethod
    def serialize(modifier: "Modifier") -> Dict[str, Any]:
        """
        Convert the modifier to a dictionary representation.
        
        Args:
            modifier (Modifier): The modifier instance to serialize.
            
        Returns:
            Dict[str, Any]: Dictionary representation of the modifier.
        """
        return {
            "bonus_type": modifier.bonus_type.name.lower(),
            "value": (
                modifier.value.to_dict()
                if isinstance(modifier.value, DamageComponent)
                else str(modifier.value)
            ),
        }
