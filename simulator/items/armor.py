# armor.py

from typing import Any

from core.constants import ArmorSlot, ArmorType
from effects.base_effect import Effect


class Armor:
    """
    Represents a piece of armor that can be equipped by characters.
    
    Armor provides Armor Class (AC) bonuses and may have special effects.
    Different armor types (light, medium, heavy) interact differently with
    Dexterity modifiers, and armor can be equipped in different slots.
    """

    def __init__(
        self,
        name: str,
        description: str,
        ac: int,
        armor_slot: ArmorSlot,
        armor_type: ArmorType,
        max_dex_bonus: int = 0,
        effect: Effect | None = None,
    ):
        self.name = name
        self.description = description
        self.ac = ac
        self.armor_slot: ArmorSlot = armor_slot
        self.armor_type: ArmorType = armor_type
        self.max_dex_bonus = max_dex_bonus
        self.effect: Effect | None = effect

        self.validate()

    def validate(self) -> None:
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

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the armor to a dictionary representation.
        
        Returns:
            dict[str, Any]: Dictionary containing the armor's properties.

        """
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
        """
        Create an Armor instance from a dictionary representation.
        
        Args:
            data (dict[str, Any]): Dictionary containing armor properties.
            
        Returns:
            Armor: A new Armor instance created from the dictionary data.
            
        Raises:
            AssertionError: If the data is None.
            KeyError: If required keys are missing from the data.

        """
        assert data is not None, "Data must not be None."
        return Armor(
            name=data["name"],
            description=data.get("description", ""),
            ac=data["ac"],
            armor_slot=ArmorSlot[data["armor_slot"]],
            armor_type=ArmorType[data["armor_type"]],
        )
