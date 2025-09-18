# armor.py

from typing import Any

from core.constants import ArmorSlot, ArmorType
from effects.base_effect import Effect
from pydantic import BaseModel, Field, model_validator


class Armor(BaseModel):
    """
    Represents a piece of armor that can be equipped by characters.

    Armor provides Armor Class (AC) bonuses and may have special effects.
    Different armor types (light, medium, heavy) interact differently with
    Dexterity modifiers, and armor can be equipped in different slots.
    """

    name: str = Field(
        description="The name of the armor piece.",
    )
    description: str = Field(
        description="A brief description of the armor piece.",
    )
    ac: int = Field(
        description="The base Armor Class (AC) bonus provided by this armor piece.",
        ge=0,
    )
    armor_slot: ArmorSlot = Field(
        description="The slot where this armor piece is equipped (e.g., torso, shield).",
    )
    armor_type: ArmorType = Field(
        description="The type of armor (light, medium, heavy).",
    )
    max_dex_bonus: int = Field(
        default=0,
        description=(
            "The maximum Dexterity modifier that can be applied to the AC bonus. "
            "Relevant for medium armor."
        ),
        ge=0,
    )
    effect: Effect | None = Field(
        default=None,
        description="An optional special effect granted by this armor piece.",
    )

    @model_validator(mode="after")
    def validate_fields(self) -> "Armor":
        """
        Validate the armor's properties.

        Raises:
            AssertionError: If any armor property is invalid.

        """
        assert self.name and isinstance(self.name, str), "Armor name must not be empty."
        assert self.ac >= 0, "Armor AC bonus must be a non-negative integer."
        assert isinstance(
            self.armor_slot, ArmorSlot
        ), "Armor slot must be an instance of ArmorSlot."
        assert isinstance(
            self.armor_type, ArmorType
        ), "Armor type must be an instance of ArmorType."
        assert (
            self.max_dex_bonus >= 0
        ), "Max Dexterity bonus must be a non-negative integer."
        return self

    def get_ac(self, dex_mod: int = 0) -> int:
        """
        Returns the total AC of the armor, considering the Dexterity modifier.

        Args:
            dex_mod (int): The character's Dexterity modifier. Defaults to 0.

        Returns:
            int: The total AC bonus provided by this armor piece.

        """
        if self.armor_slot == ArmorSlot.TORSO:
            if self.armor_type == ArmorType.LIGHT:
                return self.ac + dex_mod
            if self.armor_type == ArmorType.MEDIUM:
                return self.ac + min(dex_mod, self.max_dex_bonus)
            if self.armor_type == ArmorType.HEAVY:
                return self.ac
            return self.ac
        if self.armor_slot == ArmorSlot.SHIELD:
            return self.ac
        return 0
