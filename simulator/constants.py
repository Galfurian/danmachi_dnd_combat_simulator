from enum import Enum, auto


class BonusType(Enum):
    HP = auto()
    MIND = auto()
    AC = auto()
    ATTACK = auto()
    DAMAGE = auto()
    INITIATIVE = auto()


class ActionType(Enum):
    """
    Defines the type of action that can be performed.
    """

    STANDARD = auto()
    BONUS = auto()
    FREE = auto()


class DamageType(Enum):
    """
    Defines various types of damage that can be inflicted.
    """

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
    """
    Defines the primary purpose or effect category of an action or spell.
    """

    OFFENSIVE = auto()
    HEALING = auto()
    BUFF = auto()
    DEBUFF = auto()
    UTILITY = auto()
    DEBUG = auto()


class ArmorSlot(Enum):
    HEAD = auto()
    TORSO = auto()
    SHIELD = auto()
    LEGS = auto()
    CLOAK = auto()
    GLOVES = auto()
    RING = auto()
    COMBAT_STYLE = auto()


class ArmorType(Enum):
    HEAVY = auto()
    MEDIUM = auto()
    LIGHT = auto()


def get_damage_emoji(damage_type: DamageType) -> str:
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


def get_action_category_emoji(category: ActionCategory) -> str:
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
    emoji_map = {
        ArmorType.LIGHT: "🧥",
        ArmorType.MEDIUM: "🥋",
        ArmorType.HEAVY: "🛡️",
    }
    return emoji_map.get(armor_type, "❔")
