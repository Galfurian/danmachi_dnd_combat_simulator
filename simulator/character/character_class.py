from typing import Any


class CharacterClass:
    """
    Represents a character class with its properties and available actions per level.
    """

    def __init__(
        self,
        name: str,
        hp_mult: int,
        mind_mult: int,
        actions_by_level: dict[str, list[str]] = {},
        spells_by_level: dict[str, list[str]] = {},
    ) -> None:
        """
        Initialize a CharacterClass instance.

        Args:
            name (str): The name of the class.
            hp_mult (int): The HP multiplier for this class.
            mind_mult (int): The Mind multiplier for this class.
            actions_by_level (dict[str, list[str]], optional): Actions available at each level. Defaults to {}.
            spells_by_level (dict[str, list[str]], optional): Spells learned at each level. Defaults to {}.

        """
        self.name: str = name
        self.hp_mult: int = hp_mult
        self.mind_mult: int = mind_mult
        self.actions_by_level: dict[str, list[str]] = actions_by_level
        self.spells_by_level: dict[str, list[str]] = spells_by_level

    def get_actions_at_level(self, level: int) -> list[str]:
        """
        Returns the actions available at a specific level.

        Args:
            level (int): The level for which to retrieve actions.

        Returns:
            list[str]: A list of action names available at the specified level.

        """
        # Return the actions directly from actions_by_level
        return self.actions_by_level.get(str(level), [])

    def get_all_actions_up_to_level(self, level: int) -> list[str]:
        """
        Get all actions that should be known up to and including a specific level.

        Args:
            level (int): The maximum level to check for actions.

        Returns:
            list[str]: A list of all action names available up to the specified level.

        """
        all_actions = []
        for lvl in range(1, level + 1):
            all_actions.extend(self.get_actions_at_level(lvl))
        return all_actions

    def get_spells_at_level(self, level: int) -> list[str]:
        """
        Get the spells that should be learned at a specific level for this class.

        Args:
            level (int): The level to check for spells.

        Returns:
            list[str]: A list of spell names available at the specified level.

        """
        return self.spells_by_level.get(str(level), [])

    def get_all_spells_up_to_level(self, level: int) -> list[str]:
        """
        Get all spells that should be known up to and including a specific level.

        Args:
            level (int): The maximum level to check for spells.

        Returns:
            list[str]: A list of all spell names available up to the specified level.

        """
        all_spells = []
        for lvl in range(1, level + 1):
            all_spells.extend(self.get_spells_at_level(lvl))
        return all_spells

    def to_dict(self) -> dict[str, Any]:
        """
        Converts the CharacterClass instance to a dictionary.

        Returns:
            dict[str, Any]: The dictionary representation of the CharacterClass instance.

        """
        return {
            "name": self.name,
            "hp_mult": self.hp_mult,
            "mind_mult": self.mind_mult,
            "actions_by_level": self.actions_by_level,
            "spells_by_level": self.spells_by_level,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "CharacterClass":
        """
        Creates a CharacterClass instance from a dictionary.

        Args:
            data (dict[str, Any]): The dictionary containing character class data with keys 'name', 'hp_mult', 'mind_mult', and 'levels'.

        Returns:
            CharacterClass: An instance of CharacterClass created from the provided dictionary data.

        """
        return CharacterClass(
            name=data["name"],
            hp_mult=data.get("hp_mult", 0),
            mind_mult=data.get("mind_mult", 0),
            actions_by_level=data.get("actions_by_level", {}),
            spells_by_level=data.get("spells_by_level", {}),
        )
