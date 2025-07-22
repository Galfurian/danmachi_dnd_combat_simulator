"""
Factory module for creating and serializing Effect instances.

This module contains all the from_dict and to_dict methods for Effect classes,
centralized for better maintainability and separation of concerns.
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


class EffectFactory:
    """Factory class for creating Effect instances from dictionaries."""

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Effect":
        """Creates an Effect instance from a dictionary representation.

        Args:
            data (Dict[str, Any]): The dictionary representation of the effect.

        Returns:
            Effect: An instance of the appropriate Effect subclass.

        Raises:
            ValueError: If the effect type is unknown.
        """
        assert data is not None, "Data must not be None."
        effect_type = data.get("type")

        if effect_type == "Buff":
            return EffectFactory._create_buff(data)
        elif effect_type == "Debuff":
            return EffectFactory._create_debuff(data)
        elif effect_type == "DoT":
            return EffectFactory._create_dot(data)
        elif effect_type == "HoT":
            return EffectFactory._create_hot(data)
        elif effect_type == "OnHitTrigger":
            return EffectFactory._create_on_hit_trigger(data)
        elif effect_type == "OnLowHealthTrigger":
            return EffectFactory._create_on_low_health_trigger(data)
        elif effect_type == "IncapacitatingEffect":
            return EffectFactory._create_incapacitating_effect(data)
        else:
            raise ValueError(f"Unknown effect type: {effect_type}")

    @staticmethod
    def _create_buff(data: Dict[str, Any]) -> "Buff":
        """Create a Buff instance from dictionary data."""
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
                    ModifierFactory.from_dict(mod_data) for mod_data in modifier_data
                ]

        return Buff(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            modifiers=modifiers,
        )

    @staticmethod
    def _create_debuff(data: Dict[str, Any]) -> "Debuff":
        """Create a Debuff instance from dictionary data."""
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
                    ModifierFactory.from_dict(mod_data) for mod_data in modifier_data
                ]

        return Debuff(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            modifiers=modifiers,
        )

    @staticmethod
    def _create_dot(data: Dict[str, Any]) -> "DoT":
        """Create a DoT (Damage over Time) instance from dictionary data."""
        from .effect import DoT

        return DoT(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            damage=DamageComponent.from_dict(data["damage"]),
        )

    @staticmethod
    def _create_hot(data: Dict[str, Any]) -> "HoT":
        """Create a HoT (Heal over Time) instance from dictionary data."""
        from .effect import HoT

        return HoT(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            heal_per_turn=data["heal_per_turn"],
        )

    @staticmethod
    def _create_on_hit_trigger(data: Dict[str, Any]) -> "OnHitTrigger":
        """Create an OnHitTrigger instance from dictionary data."""
        from .effect import OnHitTrigger

        # Parse trigger effects
        trigger_effects = []
        for effect_data in data.get("trigger_effects", []):
            trigger_effects.append(EffectFactory.from_dict(effect_data))

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
    def _create_on_low_health_trigger(data: Dict[str, Any]) -> "OnLowHealthTrigger":
        """Create an OnLowHealthTrigger instance from dictionary data."""
        from .effect import OnLowHealthTrigger

        # Parse trigger effects
        trigger_effects = []
        for effect_data in data.get("trigger_effects", []):
            trigger_effects.append(EffectFactory.from_dict(effect_data))

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
    def _create_incapacitating_effect(data: Dict[str, Any]) -> "IncapacitatingEffect":
        """Create an IncapacitatingEffect instance from dictionary data."""
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
    """Handles serialization of Effect instances to dictionaries."""

    @staticmethod
    def to_dict(effect) -> Dict[str, Any]:
        """Convert an Effect instance to dictionary representation.

        Args:
            effect: The Effect instance to serialize.

        Returns:
            Dict[str, Any]: Dictionary representation of the effect.
        """
        # Base effect data
        data = {
            "type": effect.__class__.__name__,
            "name": effect.name,
            "description": effect.description,
            "max_duration": effect.max_duration,
        }

        # Handle specific effect types using getattr for safe access
        if hasattr(effect, "modifiers"):
            # ModifierEffect subclasses (Buff, Debuff)
            data["modifiers"] = [
                ModifierSerializer.to_dict(modifier) for modifier in effect.modifiers
            ]

        if hasattr(effect, "damage"):
            # DoT
            data["damage"] = effect.damage.to_dict()

        if hasattr(effect, "heal_per_turn"):
            # HoT
            data["heal_per_turn"] = effect.heal_per_turn

        if hasattr(effect, "trigger_effects"):
            # OnHitTrigger, OnLowHealthTrigger
            data["trigger_effects"] = [
                EffectSerializer.to_dict(trigger_effect)
                for trigger_effect in effect.trigger_effects
            ]
            data["damage_bonus"] = [damage.to_dict() for damage in effect.damage_bonus]
            data["consumes_on_trigger"] = effect.consumes_on_trigger

        if hasattr(effect, "hp_threshold_percent"):
            # OnLowHealthTrigger
            data["hp_threshold_percent"] = effect.hp_threshold_percent
            data["has_triggered"] = effect.has_triggered

        if hasattr(effect, "incapacitation_type"):
            # IncapacitatingEffect
            data.update(
                {
                    "incapacitation_type": effect.incapacitation_type,
                    "save_ends": effect.save_ends,
                    "save_dc": effect.save_dc,
                    "save_stat": effect.save_stat,
                }
            )

        return data


class ModifierFactory:
    """Factory class for creating Modifier instances from dictionaries."""

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Modifier":
        """Create a Modifier instance from a dictionary representation."""

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
    """Handles serialization of Modifier instances to dictionaries."""

    @staticmethod
    def to_dict(modifier) -> Dict[str, Any]:
        """Convert the modifier to a dictionary representation."""
        return {
            "bonus_type": modifier.bonus_type.name.lower(),
            "value": (
                modifier.value.to_dict()
                if isinstance(modifier.value, DamageComponent)
                else str(modifier.value)
            ),
        }
