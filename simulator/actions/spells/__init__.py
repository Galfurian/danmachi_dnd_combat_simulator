"""
Spell system package for magical combat abilities.

This package contains all spell classes and utilities for the magical combat system.
Spells are complex actions that consume mind points and can scale with spell level.

Available Classes:
    - Spell: Abstract base class for all spells
    - SpellAttack: Offensive spells that deal damage
    - SpellHeal: Restorative spells that restore hit points
    - SpellBuff: Beneficial spells that enhance targets
    - SpellDebuff: Detrimental spells that weaken targets

Factory Functions:
    - from_dict_spell: Create spell instances from dictionaries

Usage:
    ```python
    from actions.spells import SpellAttack, SpellHeal, SpellBuff, SpellDebuff
    
    # Create spells
    fireball = SpellAttack(name="Fireball", ...)
    cure_wounds = SpellHeal(name="Cure Wounds", ...)
    bless = SpellBuff(name="Bless", ...)
    bane = SpellDebuff(name="Bane", ...)
    ```
"""

from actions.spells.base_spell import Spell
from actions.spells.spell_attack import SpellAttack
from actions.spells.spell_heal import SpellHeal
from actions.spells.spell_buff import SpellBuff
from actions.spells.spell_debuff import SpellDebuff
from actions.spells.spell_factory import from_dict_spell

__all__ = [
    "Spell",
    "SpellAttack", 
    "SpellHeal",
    "SpellBuff",
    "SpellDebuff",
    "from_dict_spell",
]
