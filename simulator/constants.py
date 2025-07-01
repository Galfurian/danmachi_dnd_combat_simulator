from enum import Enum, auto

from typing import Any


class CharacterType(Enum):
    """Defines the type of character in the game."""

    PLAYER = auto()
    ENEMY = auto()
    ALLY = auto()


class BonusType(Enum):
    """Defines the types of bonuses that can be applied to characters."""

    HP = auto()
    MIND = auto()
    AC = auto()
    ATTACK = auto()
    INITIATIVE = auto()
    DAMAGE = auto()


class ActionType(Enum):
    """Defines the type of action that can be performed."""

    STANDARD = auto()
    BONUS = auto()
    FREE = auto()


class DamageType(Enum):
    """Defines various types of damage that can be inflicted."""

    PIERCING = auto()
    SLASHING = auto()
    BLUDGEONING = auto()
    FIRE = auto()
    COLD = auto()
    LIGHTNING = auto()
    POISON = auto()
    NECROTIC = auto()
    RADIANT = auto()
    PSYCHIC = auto()
    FORCE = auto()
    ACID = auto()


class ActionCategory(Enum):
    """Defines the primary purpose or effect category of an action or spell."""

    OFFENSIVE = auto()
    HEALING = auto()
    BUFF = auto()
    DEBUFF = auto()
    UTILITY = auto()
    DEBUG = auto()


class ArmorSlot(Enum):
    """Defines the slots where armor can be equipped."""

    HEAD = auto()
    TORSO = auto()
    SHIELD = auto()
    LEGS = auto()
    CLOAK = auto()
    GLOVES = auto()
    RING = auto()
    COMBAT_STYLE = auto()


class ArmorType(Enum):
    """Defines the type of armor that can be equipped."""

    HEAVY = auto()
    MEDIUM = auto()
    LIGHT = auto()


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


def get_character_type_color(character_type: CharacterType) -> str:
    """Returns a color string based on the character type.

    Args:
        character_type (CharacterType): The character type.

    Returns:
        str: The color string associated with the character type.
    """
    color_map = {
        CharacterType.PLAYER: "bold blue",
        CharacterType.ENEMY: "bold red",
        CharacterType.ALLY: "bold green",
    }
    return color_map.get(character_type, "dim white")


def get_character_type_emoji(character_type: CharacterType) -> str:
    """Returns an emoji representation based on the character type.

    Args:
        character_type (CharacterType): The character type.

    Returns:
        str: The emoji associated with the character type.
    """
    emoji_map = {
        CharacterType.PLAYER: "👤",
        CharacterType.ENEMY: "💀",
        CharacterType.ALLY: "🤝",
    }
    return emoji_map.get(character_type, "❔")


def get_damage_emoji(damage_type: DamageType) -> str:
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
        DamageType.POISON: "☠️",
        DamageType.NECROTIC: "💀",
        DamageType.RADIANT: "✨",
        DamageType.PSYCHIC: "💫",
        DamageType.FORCE: "🌀",
        DamageType.ACID: "🧪",
    }
    return emoji_map.get(damage_type, "❔")


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
    }
    return color_map.get(action_type, "dim white")


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


def get_action_category_emoji(category: ActionCategory) -> str:
    """Returns an emoji representation based on the action category.

    Args:
        category (ActionCategory): The action category.

    Returns:
        str: The emoji associated with the action category.
    """
    emoji_map = {
        ActionCategory.OFFENSIVE: "⚔️",
        ActionCategory.HEALING: "✳️",
        ActionCategory.BUFF: "🛡️",
        ActionCategory.DEBUFF: "💀",
        ActionCategory.UTILITY: "🔧",
        ActionCategory.DEBUG: "🐞",
    }
    return emoji_map.get(category, "❔")


def get_armor_emoji(armor_type: ArmorType) -> str:
    """Returns an emoji representation based on the armor type.

    Args:
        armor_type (ArmorType): The armor type.

    Returns:
        str: The emoji associated with the armor type.
    """
    emoji_map = {
        ArmorType.LIGHT: "🧥",
        ArmorType.MEDIUM: "🥋",
        ArmorType.HEAVY: "🛡️",
    }
    return emoji_map.get(armor_type, "❔")


def get_effect_color(effect: Any) -> str:
    """Returns a color string based on the effect type.

    Args:
        effect (Any): The effect instance.

    Returns:
        str: The color string associated with the effect type.
    """
    color_map = {
        "Buff": "bold green",
        "Debuff": "bold red",
        "DoT": "magenta",
        "HoT": "cyan",
        "Armor": "yellow",
    }
    return color_map.get(type(effect).__name__, "dim white")
