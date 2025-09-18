"""
Core system module for the DanMachi D&D Combat Simulator.

This module contains the fundamental components and utilities that power the combat simulator,
including game constants, dice rolling mechanics, content loading, and display utilities.
"""

# Import key classes for package-level access
from .constants import BonusType, DamageType
from .utils import cprint

__all__ = ["BonusType", "DamageType", "cprint"]
