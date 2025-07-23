from typing import Any

from .base_attack import BaseAttack
from combat.damage import DamageComponent
from core.constants import ActionType
from effects.effect import Effect


class WeaponAttack(BaseAttack):
    """A weapon-based attack that can be equipped and unequipped.

    This class represents attacks made with weapons, such as swords, bows, or
    other equipment. It includes attributes for handling weapon-specific
    properties like the number of hands required to wield the weapon.
    """

    def __init__(
        self,
        name: str,
        type: ActionType,
        description: str,
        cooldown: int,
        maximum_uses: int,
        hands_required: int,
        attack_roll: str,
        damage: list[DamageComponent],
        effect: Effect | None = None,
    ):
        """Initialize a new WeaponAttack.
        
        Args:
            name (str): Weapon name (e.g., "Longsword", "Shortbow").
            type (ActionType): Action type (usually ACTION or BONUS_ACTION).
            description (str): Flavor text describing the weapon.
            cooldown (int): Turns between uses (0 for most weapons).
            maximum_uses (int): Max uses per encounter (-1 for unlimited).
            hands_required (int): Number of hands needed to wield (1 or 2).
            attack_roll (str): Attack roll expression with variables.
            damage (list[DamageComponent]): List of damage components for the weapon.
            effect (Effect | None): Optional effect applied on successful hit.
        """
        super().__init__(
            name,
            type,
            description,
            cooldown,
            maximum_uses,
            hands_required,
            attack_roll,
            damage,
            effect,
        )
