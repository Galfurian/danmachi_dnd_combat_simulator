from typing import Any

from .base_attack import BaseAttack
from combat.damage import DamageComponent
from core.constants import ActionType
from effects.effect import Effect


class WeaponAttack(BaseAttack):
    """
    A weapon-based attack that can be equipped and unequipped.

    WeaponAttacks represent attacks made with physical weapons that characters
    can wield, equip, and unequip. They inherit all functionality from BaseAttack
    but are specifically designed for weapon-based combat systems.

    Key Characteristics:
        - Requires specific hands to wield (tracked via hands_required)
        - Can be equipped/unequipped from character inventories
        - Represents manufactured weapons (swords, axes, bows, etc.)
        - May have weapon-specific properties and restrictions

    Usage Context:
        - Player character weapons
        - Lootable/tradeable weapons
        - Equipment-based combat systems
        - Weapon proficiency systems

    Example:
        ```python
        longsword = WeaponAttack(
            name="Longsword",
            type=ActionType.ACTION,
            description="A versatile martial weapon",
            cooldown=0,
            maximum_uses=-1,
            hands_required=1,
            attack_roll="1d20 + {STR} + {PROF}",
            damage=[DamageComponent("slashing", "1d8 + {STR}")],
            effect=None
        )
        ```
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
        """
        Initialize a new WeaponAttack.

        Args:
            name: Weapon name (e.g., "Longsword", "Shortbow")
            type: Action type (usually ACTION or BONUS_ACTION)
            description: Flavor text describing the weapon
            cooldown: Turns between uses (0 for most weapons)
            maximum_uses: Max uses per encounter (-1 for unlimited)
            hands_required: Number of hands needed to wield (1 or 2)
            attack_roll: Attack roll expression with variables
            damage: List of damage components for the weapon
            effect: Optional effect applied on successful hit

        Example:
            ```python
            greatsword = WeaponAttack(
                name="Greatsword",
                type=ActionType.ACTION,
                description="A heavy two-handed sword",
                cooldown=0,
                maximum_uses=-1,
                hands_required=2,
                attack_roll="1d20 + {STR} + {PROF}",
                damage=[DamageComponent("slashing", "2d6 + {STR}")],
                effect=None
            )
            ```
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

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "WeaponAttack":
        """
        Creates a WeaponAttack instance from a dictionary.

        Reconstructs a complete WeaponAttack from its dictionary representation,
        typically loaded from JSON weapon configuration files.

        Args:
            data: Dictionary with weapon specification

        Returns:
            WeaponAttack: Fully initialized weapon attack instance

        Example:
            ```python
            weapon_data = load_weapon_from_json("longsword.json")
            longsword = WeaponAttack.from_dict(weapon_data)
            ```
        """
        return WeaponAttack(
            name=data["name"],
            type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            hands_required=data.get("hands_required", 0),
            attack_roll=data["attack_roll"],
            damage=[DamageComponent.from_dict(comp) for comp in data["damage"]],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
        )
