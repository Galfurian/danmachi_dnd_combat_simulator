# Import base classes
from .base_effect import Effect, Modifier

# Import modifier-based effects
from .modifier_effect import ModifierEffect, BuffEffect, DebuffEffect

# Import damage effects
from .damage_over_time_effect import DamageOverTimeEffect

# Import healing effects
from .healing_over_time_effect import HealingOverTimeEffect

# Import incapacitating effects
from .incapacitating_effect import IncapacitatingEffect

# Import trigger effects and related classes
from .trigger_effect import (
    TriggerType,
    TriggerCondition,
    TriggerEffect,
    create_on_hit_trigger,
    create_low_health_trigger,
    create_spell_cast_trigger,
    create_damage_taken_trigger,
    create_turn_based_trigger,
    create_critical_hit_trigger,
    create_kill_trigger,
    create_custom_trigger,
    create_trigger_from_json_config,
)

# Import serialization module
from . import effect_serialization

__all__ = [
    # Base classes
    "Effect",
    "Modifier",
    
    # Modifier-based effects
    "ModifierEffect",
    "BuffEffect", 
    "DebuffEffect",
    
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
    
    # Serialization
    "effect_serialization",
]
