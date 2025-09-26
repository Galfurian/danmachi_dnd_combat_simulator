
from pydantic import BaseModel, Field


class CharacterClass(BaseModel):
    """
    Represents a character class with its properties and available actions per
    level.
    """

    name: str = Field(
        description="The name of the character class.",
    )
    hp_mult: int = Field(
        description="The HP multiplier for this class.",
    )
    mind_mult: int = Field(
        description="The Mind multiplier for this class.",
    )
    actions_by_level: dict[str, list[str]] = Field(
        default_factory=dict,
        description="A dictionary mapping levels to lists of action names available at that level.",
    )
    spells_by_level: dict[str, list[str]] = Field(
        default_factory=dict,
        description="A dictionary mapping levels to lists of spell names available at that level.",
    )

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

    def __hash__(self) -> int:
        """
        Hash the character class based on its name.

        Returns:
            int:
                The hash value of the character class.

        """
        return hash(self.name)
