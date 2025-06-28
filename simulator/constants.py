from enum import Enum, auto


class BonusType(Enum):
    HP_MAX = auto()
    MIND_MAX = auto()
    AC = auto()
    ATTACK_BONUS = auto()
    DAMAGE_BONUS = auto()
    # Add other bonus types as needed


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
    ICE = auto()
    ACID = auto()
    POISON = auto()
    NECROTIC = auto()
    RADIANT = auto()
    LIGHTNING = auto()
    THUNDER = auto()
    FORCE = auto()
    PSYCHIC = auto()
    # Add more damage types as needed


class ActionCategory(Enum):
    """
    Defines the primary purpose or effect category of an action or spell.
    """

    OFFENSIVE = auto()  # Deals damage, applies debuffs
    HEALING = auto()  # Restores HP
    BUFF = auto()  # Applies beneficial effects to allies
    DEBUFF = auto()  # Applies detrimental effects to enemies
    UTILITY = auto()  # Miscellaneous effects (e.g., movement, disarm traps)
    DEBUG = auto()  # Actions used for testing/debugging purposes
    # Add more categories as needed (e.g., Summon, Transform, Environmental)
