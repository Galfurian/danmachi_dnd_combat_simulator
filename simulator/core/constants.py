"""
Constants and enumerations for the simulator.

Defines global constants, enumerations for character types, action classes,
damage types, armor slots, and other core game elements used throughout the
simulator.
"""

from enum import Enum
from typing import Any

# Global verbose level for combat output:
# 0 - Minimal (e.g., only final results)
# 1 - Moderate (e.g., show dice rolls)
# 2 - Full detail (e.g., intermediate computations, effects applied, bonuses, etc.)
GLOBAL_VERBOSE_LEVEL = 0


class NiceEnum(Enum):
    """An enumeration that provides a nicer string representation."""

    def __str__(self) -> str:
        return self.name

    @property
    def display_name(self) -> str:
        return self.name.lower().capitalize()


class CharacterType(NiceEnum):
    """Defines the type of character in the game."""

    PLAYER = "PLAYER"
    ENEMY = "ENEMY"
    ALLY = "ALLY"

    @property
    def emoji(self) -> str:
        """Returns the emoji associated with this character type."""
        return {
            CharacterType.PLAYER: "👤",
            CharacterType.ENEMY: "👹",
            CharacterType.ALLY: "🤝",
        }.get(self, "❔")

    @property
    def color(self) -> str:
        """Returns the color string associated with this character type."""
        return {
            CharacterType.PLAYER: "bold blue",
            CharacterType.ENEMY: "bold red",
            CharacterType.ALLY: "bold green",
        }.get(self, "dim white")

    @property
    def colored_name(self) -> str:
        return self.colorize(self.display_name)

    def colorize(self, message: str) -> str:
        """Applies character type color formatting to a message."""
        return f"[{self.color}]{message}[/]"


class BonusType(NiceEnum):
    """Defines the types of bonuses that can be applied to characters."""

    HP = "HP"
    MIND = "MIND"
    AC = "AC"
    INITIATIVE = "INITIATIVE"
    ATTACK = "ATTACK"
    DAMAGE = "DAMAGE"
    CONCENTRATION = "CONCENTRATION"


class ActionClass(NiceEnum):
    """Defines the class of action that can be performed."""

    NONE = "NONE"
    STANDARD = "STANDARD"
    BONUS = "BONUS"
    FREE = "FREE"
    REACTION = "REACTION"

    @property
    def color(self) -> str:
        """Returns the color string associated with this action class."""
        return {
            ActionClass.STANDARD: "bold yellow",
            ActionClass.BONUS: "bold green",
            ActionClass.FREE: "bold cyan",
            ActionClass.REACTION: "bold red",
        }.get(self, "dim white")

    @property
    def colored_name(self) -> str:
        return self.colorize(self.display_name)

    def colorize(self, message: str) -> str:
        """Applies action class color formatting to a message."""
        return f"[{self.color}]{message}[/]"


class DamageType(NiceEnum):
    """Defines various types of damage that can be inflicted."""

    PIERCING = "PIERCING"
    SLASHING = "SLASHING"
    BLUDGEONING = "BLUDGEONING"
    FIRE = "FIRE"
    COLD = "COLD"
    LIGHTNING = "LIGHTNING"
    THUNDER = "THUNDER"
    POISON = "POISON"
    NECROTIC = "NECROTIC"
    RADIANT = "RADIANT"
    PSYCHIC = "PSYCHIC"
    FORCE = "FORCE"
    ACID = "ACID"

    @property
    def emoji(self) -> str:
        """Returns the emoji associated with this damage type."""
        return {
            DamageType.PIERCING: "🗡️",
            DamageType.SLASHING: "🪓",
            DamageType.BLUDGEONING: "🔨",
            DamageType.FIRE: "🔥",
            DamageType.COLD: "❄️",
            DamageType.LIGHTNING: "⚡",
            DamageType.THUNDER: "🌩️",
            DamageType.POISON: "☠️",
            DamageType.NECROTIC: "🖤",
            DamageType.RADIANT: "✨",
            DamageType.PSYCHIC: "💫",
            DamageType.FORCE: "🌀",
            DamageType.ACID: "🧪",
        }.get(self, "❔")

    @property
    def color(self) -> str:
        """Returns the color string associated with this damage type."""
        return {
            DamageType.PIERCING: "bold magenta",
            DamageType.SLASHING: "bold yellow",
            DamageType.BLUDGEONING: "bold red",
            DamageType.FIRE: "bold red",
            DamageType.COLD: "bold cyan",
            DamageType.LIGHTNING: "bold blue",
            DamageType.THUNDER: "bold purple",
            DamageType.POISON: "bold green",
            DamageType.NECROTIC: "dim white",
            DamageType.RADIANT: "bold white",
            DamageType.PSYCHIC: "magenta",
            DamageType.FORCE: "cyan",
            DamageType.ACID: "green",
        }.get(self, "dim white")

    @property
    def colored_name(self) -> str:
        return self.colorize(self.display_name)

    def colorize(self, message: str) -> str:
        """Applies damage type color formatting to a message."""
        return f"[{self.color}]{message}[/]"


class ActionCategory(NiceEnum):
    """Defines the primary purpose or effect category of an action or spell."""

    NONE = "NONE"
    OFFENSIVE = "OFFENSIVE"
    HEALING = "HEALING"
    BUFF = "BUFF"
    DEBUFF = "DEBUFF"
    UTILITY = "UTILITY"
    DEBUG = "DEBUG"

    @property
    def emoji(self) -> str:
        """Returns the emoji associated with this action category."""
        return {
            ActionCategory.OFFENSIVE: "⚔️",
            ActionCategory.HEALING: "💚",
            ActionCategory.BUFF: "💪",
            ActionCategory.DEBUFF: "😈",
            ActionCategory.UTILITY: "🔧",
            ActionCategory.DEBUG: "🐞",
        }.get(self, "❔")

    @property
    def color(self) -> str:
        """Returns the color string associated with this action category."""
        return {
            ActionCategory.OFFENSIVE: "bold red",
            ActionCategory.HEALING: "bold green",
            ActionCategory.BUFF: "bold yellow",
            ActionCategory.DEBUFF: "bold magenta",
            ActionCategory.UTILITY: "bold cyan",
            ActionCategory.DEBUG: "dim white",
        }.get(self, "dim white")

    @property
    def colored_name(self) -> str:
        return self.colorize(self.display_name)

    def colorize(self, message: str) -> str:
        """Applies action category color formatting to a message."""
        return f"[{self.color}]{message}[/]"


class ArmorSlot(NiceEnum):
    """Defines the slots where armor can be equipped."""

    HEAD = "HEAD"
    TORSO = "TORSO"
    SHIELD = "SHIELD"
    LEGS = "LEGS"
    CLOAK = "CLOAK"
    GLOVES = "GLOVES"
    RING = "RING"
    COMBAT_STYLE = "COMBAT_STYLE"


class ArmorType(NiceEnum):
    """Defines the type of armor that can be equipped."""

    HEAVY = "HEAVY"
    MEDIUM = "MEDIUM"
    LIGHT = "LIGHT"
    OTHER = "OTHER"

    @property
    def emoji(self) -> str:
        """Returns the emoji associated with this armor type."""
        return {
            ArmorType.LIGHT: "🧥",
            ArmorType.MEDIUM: "🥋",
            ArmorType.HEAVY: ":shield:",
            ArmorType.OTHER: "🎭",
        }.get(self, "❔")

    @property
    def color(self) -> str:
        """Returns the color string associated with this armor type."""
        return {
            ArmorType.HEAVY: "bold red",
            ArmorType.MEDIUM: "bold yellow",
            ArmorType.LIGHT: "bold green",
            ArmorType.OTHER: "dim white",
        }.get(self, "dim white")

    @property
    def colored_name(self) -> str:
        return self.colorize(self.display_name)

    def colorize(self, message: str) -> str:
        """Applies armor type color formatting to a message."""
        return f"[{self.color}]{message}[/]"


class IncapacitationType(NiceEnum):
    """Defines types of incapacitating effects."""

    PARALYZED = "PARALYZED"
    STUNNED = "STUNNED"
    SLEEP = "SLEEP"
    CHARMED = "CHARMED"
    FRIGHTENED = "FRIGHTENED"

    @property
    def emoji(self) -> str:
        """Returns the emoji associated with this incapacitation type."""
        return {
            IncapacitationType.PARALYZED: "😵‍💫",
            IncapacitationType.STUNNED: "💫",
            IncapacitationType.SLEEP: "💤",
            IncapacitationType.CHARMED: "😍",
            IncapacitationType.FRIGHTENED: "😱",
        }.get(self, "❔")

    @property
    def color(self) -> str:
        """Returns the color string associated with this incapacitation type."""
        return {
            IncapacitationType.PARALYZED: "bold red",
            IncapacitationType.STUNNED: "bold yellow",
            IncapacitationType.SLEEP: "cyan",
            IncapacitationType.CHARMED: "bold magenta",
            IncapacitationType.FRIGHTENED: "bold blue",
        }.get(self, "dim white")

    @property
    def colored_name(self) -> str:
        return self.colorize(self.display_name)

    def colorize(self, message: str) -> str:
        """Applies incapacitation type color formatting to a message."""
        return f"[{self.color}]{message}[/]"


class StatType(NiceEnum):
    """Defines the six stat types in D&D."""

    STRENGTH = "STRENGTH"
    DEXTERITY = "DEXTERITY"
    CONSTITUTION = "CONSTITUTION"
    INTELLIGENCE = "INTELLIGENCE"
    WISDOM = "WISDOM"
    CHARISMA = "CHARISMA"

    @property
    def short_name(self) -> str:
        """Returns the 3-letter abbreviation for the stat."""
        return {
            StatType.STRENGTH: "STR",
            StatType.DEXTERITY: "DEX",
            StatType.CONSTITUTION: "CON",
            StatType.INTELLIGENCE: "INT",
            StatType.WISDOM: "WIS",
            StatType.CHARISMA: "CHA",
        }.get(self, "UNK")


def is_oponent(char1: CharacterType, char2: CharacterType) -> bool:
    """Determines if char2 is an opponent of char1.

    Args:
        char1 (CharacterType): The first character type.
        char2 (CharacterType): The second character type.

    Returns:
        bool: True if char2 is an opponent of char1, False otherwise.

    """
    group1 = [CharacterType.PLAYER, CharacterType.ALLY]
    group2 = [CharacterType.ENEMY]
    if char1 == char2:
        return False
    if char1 in group1 and char2 in group1:
        return False
    if char1 in group2 and char2 in group2:
        return False
    return True


def adapt_keys_to_enum(enum_class: Any, data: dict[Any, Any]) -> dict[Any, Any]:
    """
    Converts dictionary keys to the specified enumeration type.

    Args:
        enum_class (Any):
            The enumeration class to convert keys to.
        data (dict[Any, Any]):
            The input dictionary with keys to convert.

    Returns:
        dict[Any, Any]:
            A new dictionary with keys converted to the specified enum type.
    """
    return {
        enum_class[key] if isinstance(key, str) else key: value
        for key, value in data.items()
    }
