# armor.py

from typing import Optional

from core.constants import *
from effects.effect import *


class Armor:
    def __init__(
        self,
        name: str,
        description: str,
        ac: int,
        armor_slot: ArmorSlot,
        armor_type: ArmorType,
        max_dex_bonus: int = 0,
        effect: Optional[Effect] = None,
    ):
        self.name = name
        self.description = description
        self.ac = ac
        self.armor_slot: ArmorSlot = armor_slot
        self.armor_type: ArmorType = armor_type
        self.max_dex_bonus = max_dex_bonus
        self.effect: Optional[Effect] = effect

        self.validate()

    def validate(self) -> None:
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

    def get_ac(self, dex_mod: int = 0) -> int:
        """
        Returns the total AC of the armor, considering the Dexterity modifier.
        """
        if self.armor_slot == ArmorSlot.TORSO:
            if self.armor_type == ArmorType.LIGHT:
                return self.ac + dex_mod
            if self.armor_type == ArmorType.MEDIUM:
                return self.ac + min(dex_mod, self.max_dex_bonus)
            if self.armor_type == ArmorType.HEAVY:
                return self.ac
            return self.ac
        elif self.armor_slot == ArmorSlot.SHIELD:
            return self.ac
        return 0

    def to_dict(self) -> dict[str, Any]:
        data = {
            "name": self.name,
            "description": self.description,
            "ac": self.ac,
            "armor_slot": self.armor_slot.name,
            "armor_type": self.armor_type.name,
        }
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Armor":
        assert data is not None, "Data must not be None."
        return Armor(
            name=data["name"],
            description=data.get("description", ""),
            ac=data["ac"],
            armor_slot=ArmorSlot[data["armor_slot"]],
            armor_type=ArmorType[data["armor_type"]],
        )
