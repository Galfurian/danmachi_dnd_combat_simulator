from typing import Any
from pathlib import Path
import json


class CharacterClass:
    def __init__(self, name: str, hp_mult: int, mind_mult: int):
        self.name: str = name
        self.hp_mult: int = hp_mult
        self.mind_mult: int = mind_mult

    def to_dict(self) -> dict[str, Any]:
        """Converts the CharacterClass instance to a dictionary.

        Returns:
            dict[str, Any]: The dictionary representation of the CharacterClass instance.
        """
        return {
            "name": self.name,
            "hp_mult": self.hp_mult,
            "mind_mult": self.mind_mult,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "CharacterClass":
        """Creates a CharacterClass instance from a dictionary.

        Args:
            data (dict): _description_

        Returns:
            _type_: _description_
        """
        return CharacterClass(
            name=data["name"],
            hp_mult=data.get("hp_mult", 0),
            mind_mult=data.get("mind_mult", 0),
        )
