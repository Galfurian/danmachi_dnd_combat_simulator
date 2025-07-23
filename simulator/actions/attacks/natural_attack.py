from typing import Any

from .base_attack import BaseAttack
from combat.damage import DamageComponent
from core.constants import ActionType
from effects.base_effect import Effect


class NaturalAttack(BaseAttack):
    """A natural or innate attack that is part of a creature's biology.

    Examples include bites, claws, tail slaps, or other attacks that do not
    require weapons and are intrinsic to the creature's anatomy.
    """

    def __init__(
        self,
        name: str,
        type: ActionType,
        description: str,
        cooldown: int,
        maximum_uses: int,
        attack_roll: str,
        damage: list[DamageComponent],
        effect: Effect | None = None,
    ):
        """Initialize a new NaturalAttack.
        
        Args:
            name (str): Natural weapon name (e.g., "Bite", "Claw", "Tail Slap").
            type (ActionType): Action type (usually ACTION, sometimes BONUS_ACTION).
            description (str): Flavor text describing the natural weapon.
            cooldown (int): Turns between uses (0 for most natural attacks).
            maximum_uses (int): Max uses per encounter (-1 for unlimited).
            attack_roll (str): Attack roll expression with variables.
            damage (list[DamageComponent]): List of damage components for the natural weapon.
            effect (Effect | None): Optional effect like poison or disease.
        """
        super().__init__(
            name,
            type,
            description,
            cooldown,
            maximum_uses,
            0,  # Natural attacks don't require hands
            attack_roll,
            damage,
            effect,
        )
