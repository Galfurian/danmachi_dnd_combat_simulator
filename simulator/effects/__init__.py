"""
Effects system module for the DanMachi D&D Combat Simulator.

This module contains all game effects including buffs, debuffs, damage over time,
healing over time, incapacitating effects, and trigger-based effects that can
modify character behavior and combat mechanics.
"""

# Import base classes
from .base_effect import Effect, Modifier

# Import damage effects
from .damage_over_time_effect import DamageOverTimeEffect

# Import healing effects
from .healing_over_time_effect import HealingOverTimeEffect

# Import incapacitating effects
from .incapacitating_effect import IncapacitatingEffect

# Import modifier-based effects
from .modifier_effect import ModifierEffect

# Import trigger effects and related classes
from .trigger_effect import (
    ValidTriggerEffect,
    TriggerType,
    TriggerEvent,
    HitTriggerEvent,
    MissTriggerEvent,
    CriticalHitTriggerEvent,
    DamageTakenTriggerEvent,
    LowHealthTriggerEvent,
    HighHealthTriggerEvent,
    TurnStartTriggerEvent,
    TurnEndTriggerEvent,
    DeathTriggerEvent,
    KillTriggerEvent,
    HealTriggerEvent,
    SpellCastTriggerEvent,
    TriggerCondition,
    TriggerEffect,
)

__all__ = [
    # Base classes
    "Effect",
    "Modifier",
    # Modifier-based effects
    "ModifierEffect",
    # Damage effects
    "DamageOverTimeEffect",
    # Healing effects
    "HealingOverTimeEffect",
    # Incapacitating effects
    "IncapacitatingEffect",
    # Trigger effects
    "ValidTriggerEffect",
    "TriggerType",
    "TriggerEvent",
    "HitTriggerEvent",
    "MissTriggerEvent",
    "CriticalHitTriggerEvent",
    "DamageTakenTriggerEvent",
    "LowHealthTriggerEvent",
    "HighHealthTriggerEvent",
    "TurnStartTriggerEvent",
    "TurnEndTriggerEvent",
    "DeathTriggerEvent",
    "KillTriggerEvent",
    "HealTriggerEvent",
    "SpellCastTriggerEvent",
    "TriggerCondition",
    "TriggerEffect",
]
