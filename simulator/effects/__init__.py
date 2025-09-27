"""
Effects system module for the DanMachi D&D Combat Simulator.

This module contains all game effects including buffs, debuffs, damage over time,
healing over time, incapacitating effects, and trigger-based effects that can
modify character behavior and combat mechanics.
"""

# Import base classes
from .base_effect import Effect

# Import damage effects
from .damage_over_time_effect import DamageOverTimeEffect

# Import healing effects
from .healing_over_time_effect import HealingOverTimeEffect

# Import incapacitating effects
from .incapacitating_effect import IncapacitatingEffect

# Import modifier-based effects
from .modifier_effect import Modifier, ModifierEffect

# Import trigger effects and related classes
from .trigger_effect import (
    TriggerCondition,
    TriggerEffect,
    ValidTriggerEffect,
)

# Import the event system.

from .event_system import (
    EventType,
    CombatEvent,
    HitEvent,
    MissEvent,
    CriticalHitEvent,
    DamageTakenEvent,
    LowHealthEvent,
    HighHealthEvent,
    TurnStartEvent,
    TurnEndEvent,
    DeathEvent,
    KillEvent,
    HealEvent,
    SpellCastEvent,
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
    "TriggerCondition",
    "TriggerEffect",
    # Event system
    "EventType",
    "CombatEvent",
    "HitEvent",
    "MissEvent",
    "CriticalHitEvent",
    "DamageTakenEvent",
    "LowHealthEvent",
    "HighHealthEvent",
    "TurnStartEvent",
    "TurnEndEvent",
    "DeathEvent",
    "KillEvent",
    "HealEvent",
    "SpellCastEvent",
]
