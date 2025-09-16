"""
Attack actions module.

This module contains all attack-related action classes including base attacks,
weapon attacks, natural attacks, and factory functions for creating attack
instances from data.
"""

from .base_attack import BaseAttack
from .weapon_attack import WeaponAttack
from .natural_attack import NaturalAttack

__all__ = [
    "BaseAttack",
    "WeaponAttack", 
    "NaturalAttack",
]
