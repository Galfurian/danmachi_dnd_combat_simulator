"""
Attack actions module.

This module contains all attack-related action classes including base attacks,
weapon attacks, natural attacks, and factory functions for creating attack
instances from data.
"""

from .base_attack import BaseAttack
from .weapon_attack import WeaponAttack
from .natural_attack import NaturalAttack
from .attack_factory import from_dict_attack

__all__ = [
    "BaseAttack",
    "WeaponAttack", 
    "NaturalAttack",
    "from_dict_attack"
]
