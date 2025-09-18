"""
Spell actions submodule for the DanMachi D&D Combat Simulator.

This submodule contains all spell-related action classes including offensive spells,
healing spells, buffs, and debuffs that characters can cast using mind points.
"""

from .base_spell import Spell
from .spell_buff import SpellBuff
from .spell_debuff import SpellDebuff
from .spell_heal import SpellHeal
from .spell_offensive import SpellOffensive

__all__ = [
    "Spell",
    "SpellBuff",
    "SpellDebuff",
    "SpellHeal",
    "SpellOffensive",
]
