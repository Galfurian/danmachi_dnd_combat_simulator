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
    def color(self) -> str:
        """Returns the color string associated with this character type."""
        color_map = {
            CharacterType.PLAYER: "bold blue",
            CharacterType.ENEMY: "bold red",
            CharacterType.ALLY: "bold green",
        }
        return color_map.get(self, "dim white")


class BonusType(NiceEnum):
    """Defines the types of bonuses that can be applied to characters."""

    HP = "HP"
    MIND = "MIND"
    AC = "AC"
    INITIATIVE = "INITIATIVE"
    ATTACK = "ATTACK"
    DAMAGE = "DAMAGE"
    CONCENTRATION = "CONCENTRATION"


class ActionType(NiceEnum):
    """Defines the type of action that can be performed."""

    NONE = "NONE"
    STANDARD = "STANDARD"
    BONUS = "BONUS"
    FREE = "FREE"
    REACTION = "REACTION"


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


class ActionCategory(str, Enum):
    """Defines the primary purpose or effect category of an action or spell."""

    OFFENSIVE = "OFFENSIVE"
    HEALING = "HEALING"
    BUFF = "BUFF"
    DEBUFF = "DEBUFF"
    UTILITY = "UTILITY"
    DEBUG = "DEBUG"


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


def apply_character_type_color(character_type: CharacterType, message: str) -> str:
    """
    Applies character type color formatting to a message.

    Args:
        character_type (CharacterType): The character type to get color for.
        message (str): The message to format with color.

    Returns:
        str: The message wrapped in color formatting tags.
    """
    return f"[{character_type.color}]{message}[/]"


def get_damage_type_color(damage_type: DamageType) -> str:
    """Returns a color string based on the damage type.

    Args:
        damage_type (DamageType): The damage type.

    Returns:
        str: The color string associated with the damage type.
    """
    color_map = {
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
    }
    return color_map.get(damage_type, "dim white")


def apply_damage_type_color(damage_type: DamageType, message: str) -> str:
    """
    Applies damage type color formatting to a message.

    Args:
        damage_type (DamageType): The damage type to get color for.
        message (str): The message to format with color.

    Returns:
        str: The message wrapped in color formatting tags.
    """
    return f"[{get_damage_type_color(damage_type)}]{message}[/]"


def get_action_type_color(action_type: ActionType) -> str:
    """Returns a color string based on the action type.

    Args:
        action_type (ActionType): The action type.

    Returns:
        str: The color string associated with the action type.
    """
    color_map = {
        ActionType.STANDARD: "bold yellow",
        ActionType.BONUS: "bold green",
        ActionType.FREE: "bold cyan",
        ActionType.REACTION: "bold red",
    }
    return color_map.get(action_type, "dim white")


def apply_action_type_color(action_type: ActionType, message: str) -> str:
    """
    Applies action type color formatting to a message.

    Args:
        action_type (ActionType): The action type to get color for.
        message (str): The message to format with color.

    Returns:
        str: The message wrapped in color formatting tags.
    """
    return f"[{get_action_type_color(action_type)}]{message}[/]"


def get_action_category_color(category: ActionCategory) -> str:
    """Returns a color string based on the action category.

    Args:
        category (ActionCategory): The action category.

    Returns:
        str: The color string associated with the action category.
    """
    color_map = {
        ActionCategory.OFFENSIVE: "bold red",
        ActionCategory.HEALING: "bold green",
        ActionCategory.BUFF: "bold yellow",
        ActionCategory.DEBUFF: "bold magenta",
        ActionCategory.UTILITY: "bold cyan",
        ActionCategory.DEBUG: "dim white",
    }
    return color_map.get(category, "dim white")


def apply_action_category_color(category: ActionCategory, message: str) -> str:
    """
    Applies action category color formatting to a message.

    Args:
        category (ActionCategory): The action category to get color for.
        message (str): The message to format with color.

    Returns:
        str: The message wrapped in color formatting tags.
    """
    return f"[{get_action_category_color(category)}]{message}[/]"


def get_effect_color(effect: Any) -> str:
    """Returns a color string based on the effect type.

    Args:
        effect (Any): The effect instance.

    Returns:
        str: The color string associated with the effect type.
    """
    color_map = {
        "BuffEffect": "bold cyan",
        "DebuffEffect": "bold red",
        "DamageOverTimeEffect": "bold magenta",
        "HealingOverTimeEffect": "bold green",
        "ModifierEffect": "bold yellow",
        "TriggerEffect": "bold white",
        "IncapacitatingEffect": "bold red",
    }
    return color_map.get(type(effect).__name__, "dim white")


def apply_effect_color(effect: Any, message: str) -> str:
    """
    Applies effect type color formatting to a message.

    Args:
        effect (Any): The effect instance to get color for.
        message (str): The message to format with color.

    Returns:
        str: The message wrapped in color formatting tags.
    """
    return f"[{get_effect_color(effect)}]{message}[/]"


def get_character_type_emoji(character_type: CharacterType) -> str:
    """Returns an emoji representation based on the character type.

    Args:
        character_type (CharacterType): The character type.

    Returns:
        str: The emoji associated with the character type.
    """
    emoji_map = {
        CharacterType.PLAYER: "👤",
        CharacterType.ENEMY: "👹",
        CharacterType.ALLY: "🤝",
    }
    return emoji_map.get(character_type, "❔")


def get_damage_type_emoji(damage_type: DamageType) -> str:
    """Returns an emoji representation based on the damage type.

    Args:
        damage_type (DamageType): The damage type.

    Returns:
        str: The emoji associated with the damage type.
    """
    emoji_map = {
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
    }
    return emoji_map.get(damage_type, "❔")


def get_action_category_emoji(category: ActionCategory) -> str:
    """Returns an emoji representation based on the action category.

    Args:
        category (ActionCategory): The action category.

    Returns:
        str: The emoji associated with the action category.
    """
    emoji_map = {
        ActionCategory.OFFENSIVE: "⚔️",
        ActionCategory.HEALING: "💚",
        ActionCategory.BUFF: "💪",
        ActionCategory.DEBUFF: "😈",
        ActionCategory.UTILITY: "🔧",
        ActionCategory.DEBUG: "🐞",
    }
    return emoji_map.get(category, "❔")


def get_armor_type_emoji(armor_type: ArmorType) -> str:
    """Returns an emoji representation based on the armor type.

    Args:
        armor_type (ArmorType): The armor type.

    Returns:
        str: The emoji associated with the armor type.
    """
    emoji_map = {
        ArmorType.LIGHT: "🧥",
        ArmorType.MEDIUM: "🥋",
        ArmorType.HEAVY: ":shield:",
        ArmorType.OTHER: "🎭",
    }
    return emoji_map.get(armor_type, "❔")


def get_effect_emoji(effect: Any) -> str:
    """Returns an emoji representation based on the effect type.

    Args:
        effect (Any): The effect instance.

    Returns:
        str: The emoji associated with the effect type.
    """
    emoji_map = {
        "BuffEffect": "💫",
        "DebuffEffect": "☠️",
        "DamageOverTimeEffect": "❣️",
        "HealingOverTimeEffect": "💚",
        "ModifierEffect": "🛡️",
        "TriggerEffect": "⚡",
        "IncapacitatingEffect": "😵‍💫",
    }
    return emoji_map.get(type(effect).__name__, "❔")
