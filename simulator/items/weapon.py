from typing import Any

from actions.attacks import BaseAttack
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
    description: str = Field(
        description="A description of the weapon.",
    )
    attacks: list[BaseAttack] = Field(
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
