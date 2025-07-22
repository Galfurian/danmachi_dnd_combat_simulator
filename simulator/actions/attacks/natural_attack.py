from typing import Any

from .base_attack import BaseAttack
from combat.damage import DamageComponent
from core.constants import ActionType
from effects.effect import Effect


class NaturalAttack(BaseAttack):
    """
    A natural/innate attack that is part of a creature's biology.

    NaturalAttacks represent attacks using natural weapons like claws, fangs,
    horns, or tail strikes. These attacks are inherent to the creature and
    cannot be disarmed or unequipped.

    Key Characteristics:
        - Always available (cannot be disarmed)
        - Never requires hands (hands_required always 0)
        - Represents biological weapons (claws, bite, sting, etc.)
        - Often tied to creature race or species
        - May have unique biological effects (poison, disease, etc.)

    Usage Context:
        - Monster and creature attacks
        - Racial natural weapons (tiefling claws, dragonborn breath)
        - Supernatural creature abilities
        - Unarmed combat variants
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
        """
        Initialize a new NaturalAttack.

        Note that hands_required is automatically set to 0 since natural
        attacks never require hands to use.

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

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "NaturalAttack":
        """
        Creates a NaturalAttack instance from a dictionary.

        Reconstructs a complete NaturalAttack from its dictionary representation,
        typically loaded from creature/monster configuration files.

        Args:
            data: Dictionary with natural weapon specification

        Returns:
            NaturalAttack: Fully initialized natural attack instance
        """
        return NaturalAttack(
            name=data["name"],
            type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            attack_roll=data["attack_roll"],
            damage=[DamageComponent.from_dict(comp) for comp in data["damage"]],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
        )
