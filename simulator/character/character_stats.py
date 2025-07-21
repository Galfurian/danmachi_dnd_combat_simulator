"""
Character statistics and calculated properties module.

This module handles all stat-related calculations for Character objects,
including ability modifiers, derived stats like HP/AC, and expression variables.
"""

from typing import Dict, Any, TYPE_CHECKING
from core.constants import BonusType
from core.utils import get_stat_modifier

if TYPE_CHECKING:
    from character.character_class import CharacterClass
    from character.character_race import CharacterRace
    from effects.effect_manager import EffectManager
    from items.armor import Armor


class CharacterStats:
    """Handles all stat calculations and derived properties for a Character."""
    
    def __init__(self, character_ref):
        """Initialize with reference to parent Character object."""
        self._character = character_ref
    
    # ============================================================================
    # ABILITY SCORE MODIFIERS (D&D 5e Standard)
    # ============================================================================
    
    @property
    def STR(self) -> int:
        """Returns the D&D strength modifier."""
        return get_stat_modifier(self._character.stats["strength"])

    @property 
    def DEX(self) -> int:
        """Returns the D&D dexterity modifier."""
        return get_stat_modifier(self._character.stats["dexterity"])

    @property
    def CON(self) -> int:
        """Returns the D&D constitution modifier."""
        return get_stat_modifier(self._character.stats["constitution"])

    @property
    def INT(self) -> int:
        """Returns the D&D intelligence modifier."""
        return get_stat_modifier(self._character.stats["intelligence"])

    @property
    def WIS(self) -> int:
        """Returns the D&D wisdom modifier."""
        return get_stat_modifier(self._character.stats["wisdom"])

    @property
    def CHA(self) -> int:
        """Returns the D&D charisma modifier."""
        return get_stat_modifier(self._character.stats["charisma"])

    @property
    def SPELLCASTING(self) -> int:
        """Returns the D&D spellcasting ability modifier."""
        if (self._character.spellcasting_ability and 
            self._character.spellcasting_ability in self._character.stats):
            return get_stat_modifier(self._character.stats[self._character.spellcasting_ability])
        return 0

    # ============================================================================
    # DERIVED STATS (HP, MIND, AC, etc.)
    # ============================================================================

    @property
    def HP_MAX(self) -> int:
        """Returns the maximum HP of the character."""
        hp_max: int = 0
        # Add the class levels' HP multipliers to the max HP.
        for cls, lvl in self._character.levels.items():
            hp_max += lvl * (cls.hp_mult + self.CON)
        # Add the effect modifiers to the max HP.
        hp_max += self._character.effect_manager.get_modifier(BonusType.HP)
        return hp_max

    @property
    def MIND_MAX(self) -> int:
        """Returns the maximum Mind of the character."""
        mind_max: int = 0
        # Add the class levels' Mind multipliers to the max Mind.
        for cls, lvl in self._character.levels.items():
            mind_max += lvl * (cls.mind_mult + self.SPELLCASTING)
        # Add the effect modifiers to the max Mind.
        mind_max += self._character.effect_manager.get_modifier(BonusType.MIND)
        return mind_max

    @property
    def AC(self) -> int:
        """
        Calculates Armor Class (AC) using D&D 5e rules:
        - If wearing body armor, AC = armor.base + DEX modifier (if allowed by type)
        - Shields stack with body armor or base AC
        - If no armor is worn, AC = 10 + DEX + race bonus
        """
        # Base AC is 10 + DEX modifier.
        base_ac = 10 + self.DEX

        # If there is equipped armor, replace base AC.
        if self._character.equipped_armor:
            base_ac = sum(armor.get_ac(self.DEX) for armor in self._character.equipped_armor)

        # Add effect bonuses to AC.
        effect_ac = self._character.effect_manager.get_modifier(BonusType.AC)

        # Determine final AC.
        race_bonus = self._character.race.natural_ac if self._character.race else 0
        return base_ac + race_bonus + effect_ac

    @property
    def INITIATIVE(self) -> int:
        """Calculates the character's initiative based on dexterity and any active effects.

        Returns:
            int: The total initiative value.
        """
        # Base initiative is DEX modifier.
        initiative = self.DEX
        # Add any initiative bonuses from active effects.
        initiative += self._character.effect_manager.get_modifier(BonusType.INITIATIVE)
        return initiative

    @property
    def CONCENTRATION_LIMIT(self) -> int:
        """Calculate the maximum number of concentration effects this character can maintain.

        Returns:
            int: Maximum concentration effects
        """
        base_limit = max(1, 1 + (self.SPELLCASTING // 2))
        concentration_bonus = self._character.effect_manager.get_modifier(BonusType.CONCENTRATION)

        # Handle different return types from get_modifier
        if isinstance(concentration_bonus, list):
            # Sum up all concentration bonuses if it's a list
            bonus_value = sum(
                bonus for bonus in concentration_bonus if isinstance(bonus, int)
            )
        elif isinstance(concentration_bonus, int):
            bonus_value = concentration_bonus
        else:
            bonus_value = 0

        return max(1, base_limit + bonus_value)

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def get_expression_variables(self) -> Dict[str, int]:
        """Returns a dictionary of the character's modifiers for use in expressions.

        Returns:
            Dict[str, int]: A dictionary containing the character's modifiers.
        """
        return {
            "SPELLCASTING": self.SPELLCASTING,
            "STR": self.STR,
            "DEX": self.DEX,
            "CON": self.CON,
            "INT": self.INT,
            "WIS": self.WIS,
            "CHA": self.CHA,
        }
