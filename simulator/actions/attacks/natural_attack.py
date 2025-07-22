from typing import Any

from .base_attack import BaseAttack
from combat.damage import DamageComponent
from core.constants import ActionType
from effects.effect import Effect


class NaturalAttack(BaseAttack):
    """A natural/innate attack that is part of a creature's biology."""

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
            name: Natural weapon name (e.g., "Bite", "Claw", "Tail Slap")
            type: Action type (usually ACTION, sometimes BONUS_ACTION)
            description: Flavor text describing the natural weapon
            cooldown: Turns between uses (0 for most natural attacks)
            maximum_uses: Max uses per encounter (-1 for unlimited)
            attack_roll: Attack roll expression with variables
            damage: List of damage components for the natural weapon
            effect: Optional effect like poison or disease
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
