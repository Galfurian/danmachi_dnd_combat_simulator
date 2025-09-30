"""
Character stats module for the simulator.

Handles all stat calculations and derived properties for a Character, including
ability modifiers, HP, AC, initiative, and utility stat expressions.
"""

from typing import Any

from core.constants import BonusType
from core.dice_parser import VarInfo
from core.utils import get_stat_modifier


class CharacterStats:
    """
    Handles all stat calculations and derived properties for a Character,
    including ability modifiers, HP, AC, initiative, and utility stat
    expressions.

    Attributes:
        owner (Any):
            The Character instance that owns this CharacterStats.
        stats (dict[str, int]):
            A dictionary of the character's base stats (e.g., strength,
            dexterity).
        hp (int):
            The current hit points (HP) of the character.
        mind (int):
            The current Mind points of the character.

    """

    def __init__(self, owner: Any, stats: dict[str, int]) -> None:
        """
        Initializes the CharacterStats with a reference to its owner.

        Args:
            owner (Any):
                The Character instance that owns this CharacterStats.

        """
        self.owner: Any = owner
        self.statistics: dict[str, int] = stats
        self.hp: int = self.HP_MAX
        self.mind: int = self.MIND_MAX

    # ============================================================================
    # ABILITY SCORE MODIFIERS (D&D 5e Standard)
    # ============================================================================

    @property
    def STR(self) -> int:
        """
        Returns the D&D strength modifier.

        Returns:
            int: The strength modifier value.

        """
        return get_stat_modifier(self.statistics["strength"])

    @property
    def DEX(self) -> int:
        """
        Returns the D&D dexterity modifier.

        Returns:
            int: The dexterity modifier value.

        """
        return get_stat_modifier(self.statistics["dexterity"])

    @property
    def CON(self) -> int:
        """
        Returns the D&D constitution modifier.

        Returns:
            int: The constitution modifier value.

        """
        return get_stat_modifier(self.statistics["constitution"])

    @property
    def INT(self) -> int:
        """
        Returns the D&D intelligence modifier.

        Returns:
            int: The intelligence modifier value.

        """
        return get_stat_modifier(self.statistics["intelligence"])

    @property
    def WIS(self) -> int:
        """
        Returns the D&D wisdom modifier.

        Returns:
            int: The wisdom modifier value.

        """
        return get_stat_modifier(self.statistics["wisdom"])

    @property
    def CHA(self) -> int:
        """
        Returns the D&D charisma modifier.

        Returns:
            int: The charisma modifier value.

        """
        return get_stat_modifier(self.statistics["charisma"])

    @property
    def SPELLCASTING(self) -> int:
        """
        Returns the D&D spellcasting ability modifier.

        Returns:
            int: The spellcasting ability modifier value.

        """
        if (
            self.owner.spellcasting_ability
            and self.owner.spellcasting_ability in self.statistics
        ):
            return get_stat_modifier(self.statistics[self.owner.spellcasting_ability])
        return 0

    # ============================================================================
    # DERIVED STATS (HP, MIND, AC, etc.)
    # ============================================================================

    @property
    def HP_MAX(self) -> int:
        """
        Returns the maximum HP of the character.

        Returns:
            int: The maximum HP value.

        """
        hp_max: int = 0
        # Add the class levels' HP multipliers to the max HP.
        for cls, lvl in self.owner.levels.items():
            hp_max += lvl * (cls.hp_mult + self.CON)
        # Sum all the HP modifiers from effects.
        modifiers = self.owner.effects.get_modifier(BonusType.HP)
        if isinstance(modifiers, list):
            hp_max += sum(int(mod) for mod in modifiers)
        return hp_max

    @property
    def MIND_MAX(self) -> int:
        """
        Returns the maximum Mind of the character.

        Returns:
            int: The maximum Mind value.

        """
        mind_max: int = 0
        # Add the class levels' Mind multipliers to the max Mind.
        for cls, lvl in self.owner.levels.items():
            mind_max += lvl * (cls.mind_mult + self.SPELLCASTING)
        # Sum all the Mind modifiers from effects.
        modifiers = self.owner.effects.get_modifier(BonusType.MIND)
        if isinstance(modifiers, list):
            mind_max += sum(int(mod) for mod in modifiers)
        return mind_max

    @property
    def AC(self) -> int:
        """
        Calculates Armor Class (AC) using D&D 5e rules.

        Returns:
            int: The total AC value.

        """
        # Base AC is 10 + DEX modifier.
        base_ac = 10 + self.DEX

        # If there is equipped armor, replace base AC.
        if self.owner.inventory.armors:
            base_ac = sum(
                armor.get_ac(self.DEX) for armor in self.owner.inventory.armors
            )

        # Sum all AC modifiers from active effects.
        modifiers = self.owner.effects.get_modifier(BonusType.AC)
        effect_ac = 0
        if isinstance(modifiers, list):
            effect_ac += sum(int(mod) for mod in modifiers)

        # Determine final AC.
        race_bonus = self.owner.race.natural_ac if self.owner.race else 0
        return base_ac + race_bonus + effect_ac

    @property
    def INITIATIVE(self) -> int:
        """
        Calculates the character's initiative based on dexterity and any active effects.

        Returns:
            int: The total initiative value.

        """
        # Base initiative is DEX modifier.
        initiative = self.DEX
        # Sum all initiative modifiers from active effects.
        modifiers = self.owner.effects.get_modifier(BonusType.INITIATIVE)
        if isinstance(modifiers, list):
            initiative += sum(int(mod) for mod in modifiers)
        return initiative

    @property
    def CONCENTRATION_LIMIT(self) -> int:
        """
        Calculate the maximum number of concentration effects this character can maintain.

        Returns:
            int: Maximum concentration effects.

        """
        base_limit = max(1, 1 + (self.SPELLCASTING // 2))

        # Sum all concentration modifiers from active effects.
        modifiers = self.owner.effects.get_modifier(BonusType.CONCENTRATION)
        bonus_value = 0
        if isinstance(modifiers, list):
            bonus_value = sum(int(mod) for mod in modifiers)

        # Handle different return types from get_modifier
        return max(1, base_limit + bonus_value)

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def adjust_hp(self, amount: int) -> int:
        """
        Adjusts the character's current HP by the specified amount.

        Args:
            amount (int):
                The amount to adjust HP by (positive or negative).

        Returns:
            int:
                The actual amount adjusted (may be less than requested if at max
                or min).

        """
        new_hp = max(0, min(self.hp + amount, self.HP_MAX))
        actual_adjustment = new_hp - self.hp
        self.hp = new_hp
        return actual_adjustment

    def adjust_mind(self, amount: int) -> int:
        """
        Adjusts the character's current Mind by the specified amount.

        Args:
            amount (int):
                The amount to adjust Mind by (positive or negative).

        Returns:
            int:
                The actual amount adjusted (may be less than requested if at max
                or min).

        """
        new_mind = max(0, min(self.mind + amount, self.MIND_MAX))
        actual_adjustment = new_mind - self.mind
        self.mind = new_mind
        return actual_adjustment

    def get_expression_variables(self) -> list[VarInfo]:
        """
        Returns a list of the character's modifiers for use in expressions.

        Returns:
            List[VarInfo]:
                A list containing the character's modifiers.

        """
        return [
            VarInfo(name="SPELLCASTING", value=self.SPELLCASTING),
            VarInfo(name="STR", value=self.STR),
            VarInfo(name="DEX", value=self.DEX),
            VarInfo(name="CON", value=self.CON),
            VarInfo(name="INT", value=self.INT),
            VarInfo(name="WIS", value=self.WIS),
            VarInfo(name="CHA", value=self.CHA),
        ]
