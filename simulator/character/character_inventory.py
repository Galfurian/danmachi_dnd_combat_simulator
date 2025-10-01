"""
Character inventory management module for the simulator.

Handles equipping and unequipping weapons and armor for characters, including
validation of hand requirements, armor slots, and inventory constraints.
"""

from typing import Any

from core.constants import ArmorSlot
from core.logging import log_debug, log_warning
from items.armor import Armor
from items.weapon import NaturalWeapon, Weapon, WieldedWeapon


class CharacterInventory:
    """
    Manages character inventory including weapons, armor, and equipment
    validation.

    Attributes:
        owner (Any):
            The Character instance this inventory manager belongs to.
        wielded_weapons (list[WieldedWeapon]):
            List of currently wielded weapons.
        natural_weapons (list[NaturalWeapon]):
            List of natural weapons the character possesses.
        armors (list[Armor]):
            List of currently equipped armor pieces.

    """

    owner: Any
    wielded_weapons: list[WieldedWeapon]
    natural_weapons: list[NaturalWeapon]
    armors: list[Armor]

    def __init__(self, owner: Any) -> None:
        """
        Initialize the CharacterInventory with the owning character.

        Args:
            owner (Any):
                The Character instance this inventory manager belongs to.

        """
        self._owner = owner
        self.wielded_weapons = []
        self.natural_weapons = []
        self.armors = []

    def get_occupied_hands(self) -> int:
        """
        Return the number of hands currently occupied by equipped weapons and
        armor.

        Returns:
            int:
                The number of hands currently occupied.

        """
        used_hands = sum(
            item.get_required_hands()
            for item in self.wielded_weapons
            if item.requires_hands()
        )
        used_hands += sum(
            armor.armor_slot == ArmorSlot.SHIELD for armor in self.armors
        )
        return used_hands

    def get_free_hands(self) -> int:
        """
        Return the number of free hands available for equipping items.

        Returns:
            int:
                The number of free hands available.

        """
        from character.main import Character

        assert isinstance(self._owner, Character), "Owner must be a Character."

        return self._owner.total_hands - self.get_occupied_hands()

    def can_equip_weapon(self, weapon: Weapon) -> bool:
        """
        Check if the character can equip a specific weapon.

        Args:
            weapon (Weapon):
                The weapon to check.

        Returns:
            bool:
                True if the weapon can be equipped, False otherwise.

        """
        # If the weapon requires no hands, it can always be equipped.
        if not weapon.requires_hands():
            return True
        # Check if the character has enough free hands to equip the weapon.
        if weapon.get_required_hands() > self.get_free_hands():
            return False
        return True

    def add_weapon(self, weapon: Weapon) -> bool:
        """
        Add a weapon to the character's equipped weapons.

        Args:
            weapon (Weapon):
                The weapon to equip.

        Returns:
            bool:
                True if the weapon was equipped successfully, False otherwise.

        """
        from character.main import Character

        assert isinstance(self._owner, Character), "Owner must be a Character."

        if self.can_equip_weapon(weapon):
            # Add the weapon to the character's weapon list.
            if isinstance(weapon, NaturalWeapon):
                self.natural_weapons.append(weapon)
            elif isinstance(weapon, WieldedWeapon):
                self.wielded_weapons.append(weapon)
            else:
                raise ValueError(f"Unknown weapon type {type(weapon)}.")
            return True
        return False

    def remove_weapon(self, weapon: Weapon) -> bool:
        """
        Remove a weapon from the character's equipped weapons.

        Args:
            weapon (Weapon):
                The weapon to remove.

        Returns:
            bool:
                True if the weapon was removed successfully, False otherwise.

        """
        # Remove the weapon from the character's weapon list.
        if weapon in self.wielded_weapons and isinstance(weapon, WieldedWeapon):
            self.wielded_weapons.remove(weapon)
            return True
        # Remove the natural weapon from the character's natural weapon list.
        if weapon in self.natural_weapons and isinstance(weapon, NaturalWeapon):
            self.natural_weapons.remove(weapon)
            return True
        return False

    def can_equip_armor(self, armor: Armor) -> bool:
        """
        Check if the character can equip a specific armor.

        Args:
            armor (Armor):
                The armor to check.

        Returns:
            bool:
                True if the armor can be equipped, False otherwise.

        """
        # If the armor is a shield, it can be equipped if the character has a
        # free hand.
        if armor.armor_slot == ArmorSlot.SHIELD:
            if self.get_free_hands() <= 0:
                return False
            return True
        # Otherwise, check if the armor slot is already occupied.
        for equipped in self.armors:
            if equipped.armor_slot == armor.armor_slot:
                return False
        # If the armor slot is not occupied, we can equip it.
        return True

    def add_armor(self, armor: Armor) -> bool:
        """
        Add an armor to the character's equipped armor.

        Args:
            armor (Armor): The armor to equip.

        Returns:
            bool: True if the armor was equipped successfully, False otherwise.

        """
        from character.main import Character

        assert isinstance(self._owner, Character), "Owner must be a Character."

        if self.can_equip_armor(armor):
            log_debug(
                f"{self._owner.colored_name} is equipping {armor.colored_name}",
                context={"character": self._owner.name, "armor": armor.name},
            )
            # Add the armor to the character's armor list.
            self.armors.append(armor)
            # Apply armor effects to the character.
            armor.apply_effects(self._owner)
            return True
        return False

    def remove_armor(self, armor: Armor) -> bool:
        """
        Remove an armor from the character's equipped armor.

        Args:
            armor (Armor): The armor to remove.

        Returns:
            bool: True if the armor was removed successfully, False otherwise.

        """
        if armor in self.armors:
            # Remove the armor from the character's armor list.
            self.armors.remove(armor)
            return True
        log_warning(
            f"{self._owner.name} does not have {armor.name} equipped",
            {"character": self._owner.name, "armor": armor.name},
        )
        return False
