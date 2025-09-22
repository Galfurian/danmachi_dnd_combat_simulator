from enum import Enum
from typing import Any

from actions.attacks import BaseAttack
from actions.attacks.natural_attack import NaturalAttack
from actions.attacks.weapon_attack import WeaponAttack
from core.constants import WeaponType
from pydantic import BaseModel, Field, model_validator


class Weapon(BaseModel):
    """
    Represents a weapon that can be wielded by characters in combat.

    Weapons contain one or more attacks that can be performed, specify how many
    hands are required to wield them, and automatically prefix attack names
    with the weapon name for identification.
    """

    name: str = Field(
        description="The name of the weapon.",
    )
    weapon_type: WeaponType = Field(
        description="The type of the weapon.",
    )
    description: str = Field(
        description="A description of the weapon.",
    )
    attacks: list[WeaponAttack | NaturalAttack] = Field(
        description="List of attacks this weapon can perform.",
    )
    hands_required: int = Field(
        default=0,
        description="Number of hands required to wield this weapon.",
    )

    @model_validator(mode="after")
    def validate_fields(self) -> "Weapon":
        if self.hands_required < 0:
            raise ValueError("hands_required cannot be negative.")
        # Validate that the attacks are of the correct type.
        for attack in self.attacks:
            if self.weapon_type == WeaponType.NATURAL:
                if not all(isinstance(a, NaturalAttack) for a in self.attacks):
                    print(self)
                    raise ValueError("All attacks must be of type NaturalAttack.")
            else:
                if not all(isinstance(a, WeaponAttack) for a in self.attacks):
                    print(self)
                    raise ValueError("All attacks must be of type WeaponAttack.")
        # Rename the attacks to match the weapon name.
        for attack in self.attacks:
            attack.name = f"{self.name} - {attack.name}"
        return self

    # ===========================================================================
    # GENERIC METHODS
    # ===========================================================================

    def requires_hands(self) -> int:
        """Get the number of hands required to perform this attack.

        Returns:
            int: Number of hands required.

        """
        return self.hands_required > 0

    def get_required_hands(self) -> int:
        """Get the number of hands required to perform this attack.

        Returns:
            int: Number of hands required.

        """
        return self.hands_required


class NaturalWeapon(Weapon):
    weapon_type: WeaponType = Field(
        default=WeaponType.NATURAL,
        description="The type of the weapon.",
    )


class WieldedWeapon(Weapon):
    weapon_type: WeaponType = Field(
        default=WeaponType.WIELDED,
        description="The type of the weapon.",
    )


def deserialize_weapon(data: dict[str, Any]) -> Weapon | None:
    """
    Deserialize a weapon from a dictionary.

    Args:
        data (dict): The dictionary containing weapon data.

    Returns:
        Weapon | None: The deserialized weapon or None if deserialization fails.
    """

    weapon_type = data.get("weapon_type", None)
    if weapon_type == "NATURAL":
        return NaturalWeapon(**data)
    if weapon_type == "WIELDED":
        return WieldedWeapon(**data)
    return None
