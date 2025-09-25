from typing import Any, Literal

from actions.attacks.natural_attack import NaturalAttack
from actions.attacks.weapon_attack import WeaponAttack
from pydantic import BaseModel, Field


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

    def model_post_init(self, _) -> None:
        """
        Automatically prefix attack names with the weapon name for clarity.

        Returns:
            Weapon:
                The weapon instance with renamed attacks.
        """
        # for attack in self.attacks:
        #    attack.name = f"{self.name} - {attack.name}"
        pass

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

    weapon_type: Literal["NaturalWeapon"] = "NaturalWeapon"

    def model_post_init(self, _) -> None:
        if self.hands_required != 0:
            raise ValueError("Natural weapons cannot require hands.")

        if not all(isinstance(a, NaturalAttack) for a in self.attacks):
            print(self)
            raise ValueError("All attacks must be of type NaturalAttack.")


class WieldedWeapon(Weapon):

    weapon_type: Literal["WieldedWeapon"] = "WieldedWeapon"

    def model_post_init(self, _) -> None:
        if self.hands_required <= 0:
            raise ValueError("Wielded weapons must require at least one hand.")

        if not all(isinstance(a, WeaponAttack) for a in self.attacks):
            print(self)
            raise ValueError("All attacks must be of type WeaponAttack.")


def deserialize_weapon(data: dict[str, Any]) -> Weapon:
    """
    Deserialize a weapon from a dictionary.

    Args:
        data (dict[str, Any]):
            The dictionary containing weapon data.

    Raises:
        ValueError:
            If the weapon type is unknown or if required fields are missing.

    Returns:
        Weapon:
            The deserialized weapon instance.
    """

    weapon_type = data.get("weapon_type")
    if weapon_type == "NaturalWeapon":
        return NaturalWeapon(**data)
    if weapon_type == "WieldedWeapon":
        return WieldedWeapon(**data)

    raise ValueError(f"Unknown weapon type: {weapon_type}")
