"""
Character system module for the DanMachi D&D Combat Simulator.

This module handles character creation, management, and behavior, including character classes,
races, stats, effects, inventory, actions, and serialization functionality.
"""

from .character_actions import CharacterActions
from .character_class import CharacterClass
from .character_display import CharacterDisplay
from .character_effects import CharacterEffects, TriggerResult
from .character_inventory import CharacterInventory
from .character_race import CharacterRace
from .character_stats import CharacterStats
from .main import Character, load_character, load_characters

__all__ = [
    # Import from character_actions.py
    "CharacterActions",
    # Import from character_class.py
    "CharacterClass",
    # Import from character_display.py
    "CharacterDisplay",
    # Import from character_effects.py
    "CharacterEffects",
    "TriggerResult",
    # Import from character_inventory.py
    "CharacterInventory",
    # Import from character_race.py
    "CharacterRace",
    # Import from character_stats.py
    "CharacterStats",
    # Import from main.py
    "Character",
    "load_character",
    "load_characters",
]
