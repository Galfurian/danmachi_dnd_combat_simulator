from typing import Any


class CharacterRace:
    """
    Represents a character's race, including natural AC, default and available actions and spells.
    """

    def __init__(
        self,
        name: str,
        natural_ac: int = 0,
        default_actions: list[str] | None = None,
        default_spells: list[str] | None = None,
        available_actions: dict[int, list[str]] | None = None,
        available_spells: dict[int, list[str]] | None = None,
    ) -> None:
        """
        Initialize a CharacterRace instance.

        Args:
            name (str): The name of the race.
            natural_ac (int, optional): The natural armor class. Defaults to 0.
            default_actions (list[str] | None, optional): Default actions for the race. Defaults to None.
            default_spells (list[str] | None, optional): Default spells for the race. Defaults to None.
            available_actions (dict[int, list[str]] | None, optional): Actions available by level. Defaults to None.
            available_spells (dict[int, list[str]] | None, optional): Spells available by level. Defaults to None.
        """
        self.name = name
        self.natural_ac = natural_ac
        self.default_actions = default_actions or []
        self.default_spells = default_spells or []
        self.available_actions = available_actions or {}
        self.available_spells = available_spells or {}

    def to_dict(self) -> dict[str, Any]:
        """
        Converts the CharacterRace instance to a dictionary.

        Returns:
            dict[str, Any]: The dictionary representation of the CharacterRace instance.
        """
        return {
            "name": self.name,
            "natural_ac": self.natural_ac,
            "default_actions": self.default_actions,
            "default_spells": self.default_spells,
            "available_actions": self.available_actions,
            "available_spells": self.available_spells,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "CharacterRace":
        """
        Creates a CharacterRace instance from a dictionary.

        Args:
            data (dict[str, Any]): The dictionary representation of the CharacterRace.

        Returns:
            CharacterRace: The CharacterRace instance.
        """
        return CharacterRace(
            name=data["name"],
            natural_ac=data.get("natural_ac", 0),
            default_actions=data.get("default_actions", []),
            default_spells=data.get("default_spells", []),
            available_actions=data.get("available_actions", {}),
            available_spells=data.get("available_spells", {}),
        )
