"""
Character management module for the simulator.

Defines the Character class and related functions for creating, loading, and
managing characters, including stats, equipment, actions, spells, and effects.
Handles character serialization from JSON data.
"""

from core.constants import CharacterType, DamageType
from core.dice_parser import VarInfo
from core.logging import log_debug
from effects.base_effect import EventResponse
from effects.event_system import (
    CombatEvent,
    TurnEndEvent,
    TurnStartEvent,
)
from effects.incapacitating_effect import IncapacitatingEffect

from .character_actions import CharacterActions
from .character_class import CharacterClass
from .character_display import CharacterDisplay
from .character_effects import CharacterEffects, ValidPassiveEffect
from .character_inventory import CharacterInventory
from .character_race import CharacterRace
from .character_stats import CharacterStats


class Character:
    """
    Represents a character in the game, including stats, equipment, actions,
    effects, and all related management modules. Provides methods for stat
    calculation, action and spell management, equipment handling, effect
    processing, and serialization.

    Attributes:
        char_type (CharacterType):
            The type of character (e.g., player, enemy, NPC).
        name (str):
            The name of the character.
        race (CharacterRace):
            The race of the character.
        levels (dict[CharacterClass, int]):
            The character's levels in different classes.
        spellcasting_ability (str | None):
            The ability score used for spellcasting, if applicable.
        total_hands (int):
            The total number of hands the character has for wielding weapons.
        immunities (set[DamageType]):
            The set of damage types the character is immune to.
        resistances (set[DamageType]):
            The set of damage types the character is resistant to.
        vulnerabilities (set[DamageType]):
            The set of damage types the character is vulnerable to.
        number_of_attacks (int):
            The number of attacks the character can make in a turn.
        passive_effects (list[ValidPassiveEffect]):
            List of passive effects that are always active on the character.

    """

    # === Static properties ===

    char_type: CharacterType
    name: str
    race: CharacterRace
    levels: dict[CharacterClass, int]
    spellcasting_ability: str | None
    total_hands: int
    immunities: set[DamageType]
    resistances: set[DamageType]
    vulnerabilities: set[DamageType]
    number_of_attacks: int
    passive_effects: list[ValidPassiveEffect]

    # === Management Modules ===

    effects: CharacterEffects
    stats: CharacterStats
    inventory: CharacterInventory
    actions: CharacterActions
    display: CharacterDisplay

    def __init__(
        self,
        char_type: CharacterType,
        name: str,
        race: CharacterRace,
        levels: dict[CharacterClass, int],
        stats: dict[str, int],
        spellcasting_ability: str | None,
        total_hands: int,
        immunities: set[DamageType],
        resistances: set[DamageType],
        vulnerabilities: set[DamageType],
        number_of_attacks: int,
        passive_effects: list[ValidPassiveEffect],
    ) -> None:
        # Initialize static properties.
        self.char_type = char_type
        self.name = name
        self.race = race
        self.levels = levels
        self.spellcasting_ability = spellcasting_ability
        self.total_hands = total_hands
        self.immunities = immunities
        self.resistances = resistances
        self.vulnerabilities = vulnerabilities
        self.number_of_attacks = number_of_attacks
        self.passive_effects = passive_effects

        # Initialize modules.
        self.effects = CharacterEffects(owner=self)
        self.stats = CharacterStats(owner=self, stats=stats)
        self.inventory = CharacterInventory(owner=self)
        self.actions = CharacterActions(owner=self)
        self.display = CharacterDisplay(owner=self)

    # ============================================================================
    # DELEGATED STAT PROPERTIES
    # ============================================================================
    # These properties delegate to the stats module for calculation

    @property
    def colored_name(self) -> str:
        """
        Returns the character's name with color coding based on character type.
        """
        return self.char_type.colorize(self.name)

    @property
    def HP_MAX(self) -> int:
        """Returns the maximum HP of the character."""
        return self.stats.HP_MAX

    @property
    def MIND_MAX(self) -> int:
        """Returns the maximum Mind of the character."""
        return self.stats.MIND_MAX

    @property
    def STR(self) -> int:
        """Returns the D&D strength modifier."""
        return self.stats.STR

    @property
    def DEX(self) -> int:
        """Returns the D&D dexterity modifier."""
        return self.stats.DEX

    @property
    def CON(self) -> int:
        """Returns the D&D constitution modifier."""
        return self.stats.CON

    @property
    def INT(self) -> int:
        """Returns the D&D intelligence modifier."""
        return self.stats.INT

    @property
    def WIS(self) -> int:
        """Returns the D&D wisdom modifier."""
        return self.stats.WIS

    @property
    def CHA(self) -> int:
        """Returns the D&D charisma modifier."""
        return self.stats.CHA

    @property
    def SPELLCASTING(self) -> int:
        """Returns the D&D spellcasting ability modifier."""
        return self.stats.SPELLCASTING

    @property
    def AC(self) -> int:
        """Calculates Armor Class (AC) using D&D 5e rules."""
        return self.stats.AC

    @property
    def INITIATIVE(self) -> int:
        """
        Calculates the character's initiative based on dexterity and any active
        effects.
        """
        return self.stats.INITIATIVE

    def adjust_mind(self, amount: int) -> int:
        """
        Adjusts the character's Mind by a specific amount, clamped between 0 and
        MIND_MAX.
        """
        return self.stats.adjust_mind(amount)

    def get_expression_variables(self) -> list[VarInfo]:
        """Returns a dictionary of the character's modifiers."""
        return self.stats.get_expression_variables()

    def is_incapacitated(self) -> bool:
        """Check if the character is incapacitated and cannot take actions."""
        for ae in self.effects.active_effects:
            if isinstance(ae.effect, IncapacitatingEffect):
                if ae.effect.prevents_actions():
                    return True
        return False

    def can_take_actions(self) -> bool:
        """Check if character can take any actions this turn."""
        return not self.is_incapacitated() and self.is_alive()

    def on_event(self, event: CombatEvent) -> list[EventResponse]:
        """
        Pass an event to the character's effects for processing.
        """
        return self.effects.on_event(event)

    def take_damage(self, amount: int, damage_type: DamageType) -> tuple[int, int, int]:
        """
        Applies damage to the character, factoring in resistances and vulnerabilities.

        Args:
            amount:
                The raw base damage
            damage_type:
                The type of damage being dealt

        Returns:
            tuple[int, int, int]:
                - The base damage before adjustments
                - The adjusted damage after resistances/vulnerabilities
                - The actual damage taken after applying to HP

        """
        base = amount
        adjusted = base
        if damage_type in self.resistances:
            adjusted = adjusted // 2
        elif damage_type in self.vulnerabilities:
            adjusted = adjusted * 2
        adjusted = max(adjusted, 0)

        # Apply the damage and get the actual damage taken.
        actual = abs(self.stats.adjust_hp(-adjusted))

        log_debug(
            f"{self.colored_name} takes {actual} {damage_type.value} damage "
            f"(base: {base}, adjusted: {adjusted}, remaining HP: {self.stats.hp})"
        )

        return base, adjusted, actual

    def heal(self, amount: int) -> int:
        """
        Increases the character's hp by the given amount, up to max_hp.

        Args:
            amount:
                The amount of healing to apply

        Returns:
            int:
                The actual amount healed

        """
        return self.stats.adjust_hp(amount)

    def use_mind(self, amount: int) -> bool:
        """
        Reduces the character's mind by the given amount, if they have enough
        mind points.

        Args:
            amount:
                The amount of mind points to use

        Returns:
            bool:
                True if the mind points were successfully used, False otherwise.

        """
        if self.stats.mind >= amount:
            self.stats.adjust_mind(-amount)
            return True
        return False

    def regain_mind(self, amount: int) -> int:
        """
        Increases the character's mind by the given amount, up to max_mind.

        Args:
            amount:
                The amount of mind points to regain

        Returns:
            int:
                The actual amount of mind points regained.

        """
        return self.stats.adjust_mind(amount)

    def is_alive(self) -> bool:
        """
        Checks if the character is alive (hp > 0).

        Returns:
            bool:
                True if the character is alive, False otherwise

        """
        return self.stats.hp > 0

    def is_dead(self) -> bool:
        """
        Checks if the character is dead (hp <= 0).

        Returns:
            bool:
                True if the character is dead, False otherwise

        """
        return self.stats.hp <= 0

    def get_spell_attack_bonus(self, spell_level: int = 1) -> int:
        """Calculates the spell attack bonus for the character.

        Args:
            spell_level: The level of the spell being cast

        Returns:
            int: The spell attack bonus for the character

        """
        return self.SPELLCASTING + spell_level

    def turn_start(self, turn_number: int) -> None:
        """
        Initializes the character at the start of their turn.
        """
        # Update all active effects.
        self.effects.on_event(TurnStartEvent(source=self, turn_number=turn_number))
        # Update action state.
        self.actions.turn_start()

    def turn_end(self, turn_number: int) -> None:
        """
        Updates the duration of all active effects, and cooldowns. Removes
        expired effects. This should be called at the end of a character's turn
        or a round.
        """
        # Update all active effects.
        self.effects.on_event(TurnEndEvent(source=self, turn_number=turn_number))
        # Update action cooldowns and reset turn flags.
        self.actions.turn_end()

    def __str__(self) -> str:
        """
        Returns a string representation of the character.

        Returns:
            str:
                The character's name.

        """
        return self.colored_name

    def __repr__(self) -> str:
        """
        Returns a detailed string representation of the character.

        Returns:
            str:
                The character's class name and name.

        """
        return f"{self.__class__.__name__}(name='{self.colored_name}', type={self.char_type})"

    def __hash__(self) -> int:
        """
        Hashes the character based on its name.

        Returns:
            int:
                The hash of the character's name.

        """
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        return self.name == getattr(other, "name", None)
