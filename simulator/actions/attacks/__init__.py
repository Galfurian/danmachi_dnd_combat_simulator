"""
Attack actions module.

This module contains all attack-related action classes including base attacks,
weapon attacks, natural attacks, and factory functions for creating attack
instances from data.
"""

from .base_attack import BaseAttack
from .natural_attack import NaturalAttack
from .weapon_attack import WeaponAttack

__all__ = [
    "BaseAttack",
    "NaturalAttack",
    "WeaponAttack",
]
