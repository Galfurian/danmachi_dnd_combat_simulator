"""
Actions abilities package.

This package provides a modular system for character abilities including
offensive, healing, buff, and utility abilities. Each ability type has
specialized behavior while sharing common functionality through BaseAbility.
"""

from actions.abilities.ability_buff import AbilityBuff
from actions.abilities.ability_debuff import AbilityDebuff
from actions.abilities.ability_heal import AbilityHeal
from actions.abilities.ability_offensive import AbilityOffensive
from actions.abilities.base_ability import BaseAbility

__all__ = [
    "AbilityBuff",
    "AbilityDebuff",
    "AbilityHeal",
    "AbilityOffensive",
    "BaseAbility",
]
