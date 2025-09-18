"""
Spell system package for magical combat abilities.

This package contains all spell classes and utilities for the magical combat system.
Spells are complex actions that consume mind points and can scale with spell level.

Available Classes:
    - Spell: Abstract base class for all spells
    - SpellOffensive: Offensive spells that deal damage
    - SpellHeal: Restorative spells that restore hit points
    - SpellBuff: Beneficial spells that enhance targets
    - SpellDebuff: Detrimental spells that weaken targets

Usage:
    ```python
    from actions.spells import SpellOffensive, SpellHeal, SpellBuff, SpellDebuff

    # Create spells
    fireball = SpellOffensive(name="Fireball", ...)
    cure_wounds = SpellHeal(name="Cure Wounds", ...)
    bless = SpellBuff(name="Bless", ...)
    bane = SpellDebuff(name="Bane", ...)
    ```
"""

from actions.spells.base_spell import Spell
from actions.spells.spell_buff import SpellBuff
from actions.spells.spell_debuff import SpellDebuff
from actions.spells.spell_heal import SpellHeal
from actions.spells.spell_offensive import SpellOffensive

__all__ = [
    "Spell",
    "SpellBuff",
    "SpellDebuff",
    "SpellHeal",
    "SpellOffensive",
]
