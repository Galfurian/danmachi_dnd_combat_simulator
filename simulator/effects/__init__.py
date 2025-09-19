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
    TriggerCondition,
    TriggerEffect,
    TriggerType,
    create_critical_hit_trigger,
    create_custom_trigger,
    create_damage_taken_trigger,
    create_kill_trigger,
    create_low_health_trigger,
    create_on_hit_trigger,
    create_spell_cast_trigger,
    create_trigger_from_json_config,
    create_turn_based_trigger,
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
    "TriggerType",
    "TriggerCondition",
    "TriggerEffect",
    # Trigger factory functions
    "create_on_hit_trigger",
    "create_low_health_trigger",
    "create_spell_cast_trigger",
    "create_damage_taken_trigger",
    "create_turn_based_trigger",
    "create_critical_hit_trigger",
    "create_kill_trigger",
    "create_custom_trigger",
    "create_trigger_from_json_config",
]
