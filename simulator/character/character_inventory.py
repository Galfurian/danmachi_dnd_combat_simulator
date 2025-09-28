"""
Character Inventory Management Module - handles inventory-related functionality.
"""

from typing import Any

from catchery import log_warning
from core.constants import ArmorSlot
from items.armor import Armor
from items.weapon import Weapon, NaturalWeapon, WieldedWeapon


class CharacterInventory:
    """
    Manages character inventory including weapons, armor, and equipment
    validation.

    Attributes:
        owner (Any):
            The Character instance this inventory manager belongs to.
    """

    def __init__(self, owner: Any) -> None:
        """
        Initialize the CharacterInventory with the owning character.

        Args:
            owner (Any):
                The Character instance this inventory manager belongs to.
        """
        self.owner = owner

    def get_occupied_hands(self) -> int:
        """
        Return the number of hands currently occupied by equipped weapons and armor.

        Returns:
            int: The number of hands currently occupied.

        """
        used_hands = sum(
            item.get_required_hands()
            for item in self.owner.equipped_weapons
            if item.requires_hands()
        )
        used_hands += sum(
            armor.armor_slot == ArmorSlot.SHIELD for armor in self.owner.equipped_armor
        )
        return used_hands

    def get_free_hands(self) -> int:
        """
        Return the number of free hands available for equipping items.

        Returns:
            int: The number of free hands available.

        """
        return self.owner.total_hands - self.get_occupied_hands()

    def can_equip_weapon(self, weapon: Weapon) -> bool:
        """
        Check if the character can equip a specific weapon.

        Args:
            weapon (Weapon): The weapon to check.

        Returns:
            bool: True if the weapon can be equipped, False otherwise.

        """
        # If the weapon requires no hands, it can always be equipped.
        if not weapon.requires_hands():
            return True
        # Check if the character has enough free hands to equip the weapon.
        if weapon.get_required_hands() > self.get_free_hands():
            log_warning(
                f"{self.owner.name} does not have enough free hands to equip {weapon.name}.",
                {
                    "character": self.owner.name,
                    "weapon": weapon.name,
                    "hands_required": weapon.get_required_hands(),
                    "free_hands": self.get_free_hands(),
                },
            )
            return False
        return True

    def add_weapon(self, weapon: Weapon) -> bool:
        """
        Add a weapon to the character's equipped weapons.

        Args:
            weapon (Weapon): The weapon to equip.

        Returns:
            bool: True if the weapon was equipped successfully, False otherwise.

        """
        if self.can_equip_weapon(weapon):
            # Add the weapon to the character's weapon list.
            if isinstance(weapon, NaturalWeapon):
                self.owner.natural_weapons.append(weapon)
            elif isinstance(weapon, WieldedWeapon):
                self.owner.equipped_weapons.append(weapon)
            else:
                raise ValueError(f"Unknown weapon type {type(weapon)}.")
            return True
        log_warning(
            f"{self.owner.name} cannot equip {weapon.name}",
            {"character": self.owner.name, "weapon": weapon.name},
        )
        return False

    def remove_weapon(self, weapon: Weapon) -> bool:
        """
        Remove a weapon from the character's equipped weapons.

        Args:
            weapon (Weapon): The weapon to remove.

        Returns:
            bool: True if the weapon was removed successfully, False otherwise.

        """
        # Remove the weapon from the character's weapon list.
        if weapon in self.owner.equipped_weapons:
            self.owner.equipped_weapons.remove(weapon)
            return True
        # Remove the natural weapon from the character's natural weapon list.
        if weapon in self.owner.natural_weapons:
            self.owner.natural_weapons.remove(weapon)
            return True
        log_warning(
            f"{self.owner.name} does not have {weapon.name} equipped",
            {"character": self.owner.name, "weapon": weapon.name},
        )
        return False

    def can_equip_armor(self, armor: Armor) -> bool:
        """
        Check if the character can equip a specific armor.

        Args:
            armor (Armor): The armor to check.

        Returns:
            bool: True if the armor can be equipped, False otherwise.

        """
        # If the armor is a shield, it can be equipped if the character has a free hand.
        if armor.armor_slot == ArmorSlot.SHIELD:
            if self.get_free_hands() <= 0:
                log_warning(
                    f"{self.owner.name} does not have a free hand to equip {armor.name}",
                    {
                        "character": self.owner.name,
                        "armor": armor.name,
                        "free_hands": self.get_free_hands(),
                    },
                )
                return False
            return True
        # Otherwise, check if the armor slot is already occupied.
        for equipped in self.owner.equipped_armor:
            if equipped.armor_slot == armor.armor_slot:
                log_warning(
                    f"{self.owner.name} already has armor in slot {armor.armor_slot.name}. Cannot equip {armor.name}",
                    {
                        "character": self.owner.name,
                        "armor": armor.name,
                        "slot": armor.armor_slot.name,
                        "equipped": equipped.name,
                    },
                )
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
        if self.can_equip_armor(armor):
            # Add the armor to the character's armor list.
            self.owner.equipped_armor.append(armor)
            # Apply armor effects to the character.
            armor.apply_effects(self.owner)
            return True
        log_warning(
            f"{self.owner.name} cannot equip {armor.name} because the armor slot is already occupied",
            {
                "character": self.owner.name,
                "armor": armor.name,
                "slot": armor.armor_slot.name,
            },
        )
        return False

    def remove_armor(self, armor: Armor) -> bool:
        """
        Remove an armor from the character's equipped armor.

        Args:
            armor (Armor): The armor to remove.

        Returns:
            bool: True if the armor was removed successfully, False otherwise.

        """
        if armor in self.owner.equipped_armor:
            # Remove the armor from the character's armor list.
            self.owner.equipped_armor.remove(armor)
            return True
        log_warning(
            f"{self.owner.name} does not have {armor.name} equipped",
            {"character": self.owner.name, "armor": armor.name},
        )
        return False
