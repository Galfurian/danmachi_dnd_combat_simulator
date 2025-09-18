

from .base_attack import BaseAttack


class WeaponAttack(BaseAttack):
    """A weapon-based attack that can be equipped and unequipped.

    This class represents attacks made with weapons, such as swords, bows, or
    other equipment. It includes attributes for handling weapon-specific
    properties like the number of hands required to wield the weapon.
    """
