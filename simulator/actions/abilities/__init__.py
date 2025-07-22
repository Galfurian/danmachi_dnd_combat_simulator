"""
Actions abilities package.

This package provides a modular system for character abilities including
offensive, healing, buff, and utility abilities. Each ability type has
specialized behavior while sharing common functionality through BaseAbility.
"""

from actions.abilities.ability_buff import BuffAbility
from actions.abilities.ability_serializer import AbilityDeserializer, AbilitySerializer
from actions.abilities.ability_healing import HealingAbility
from actions.abilities.ability_offensive import OffensiveAbility
from actions.abilities.ability_utility import UtilityAbility
from actions.abilities.base_ability import BaseAbility

__all__ = [
    # Base class
    "BaseAbility",
    
    # Concrete ability types
    "OffensiveAbility",
    "HealingAbility", 
    "BuffAbility",
    "UtilityAbility",
    
    # Factory function
    "AbilityDeserializer",
    "AbilitySerializer",
]
