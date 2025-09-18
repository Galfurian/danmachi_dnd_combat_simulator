"""
Character module - Modular character system for D&D combat simulation.

This package provides a modular character system with separate modules for:
- Stats and derived properties
- Combat actions and abilities  
- Inventory and equipment management
- Serialization and data loading
- Display and status formatting

The main Character class coordinates between these modules while maintaining
full backward compatibility with existing code.
"""

# Import the main classes to make them available at the package level
from .main import Character, load_character, load_characters

__all__ = ["Character", "load_character", "load_characters"]
