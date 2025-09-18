"""
Character system module for the DanMachi D&D Combat Simulator.

This module handles character creation, management, and behavior, including character classes,
races, stats, effects, inventory, actions, and serialization functionality.
"""

# Import the main classes to make them available at the package level
from .main import Character, load_character, load_characters

__all__ = ["Character", "load_character", "load_characters"]
