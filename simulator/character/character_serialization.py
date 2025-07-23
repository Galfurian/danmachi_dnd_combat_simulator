"""
Character Serialization Module

This module handles character serialization and deserialization functionality.
Extracted from the main Character class to improve modularity.
"""

import json
from pathlib import Path
from typing import Any, TYPE_CHECKING

from core.utils import log_warning
from core.constants import CharacterType, DamageType
from character.character_class import CharacterClass
from effects.effect import Effect

if TYPE_CHECKING:
    from .main import Character


class CharacterSerialization:
    """
    Handles serialization and deserialization functionality for Character objects.
    """

    def __init__(self, character: "Character") -> None:
        """
        Initialize the serialization module with a reference to the character.

        Args:
            character (Character): The character instance to serialize/deserialize.
        """
        self._character = character

    def to_dict(self) -> dict[str, Any]:
        """
        Converts the character to a dictionary representation.

        Returns:
            dict[str, Any]: The dictionary representation of the character.
        """
        data: dict[str, Any] = {}
        data["type"] = self._character.type.name
        data["name"] = self._character.name
        data["race"] = self._character.race.name
        data["levels"] = {cls.name: lvl for cls, lvl in self._character.levels.items()}
        data["stats"] = {
            "strength": self._character.stats["strength"],
            "dexterity": self._character.stats["dexterity"],
            "constitution": self._character.stats["constitution"],
            "intelligence": self._character.stats["intelligence"],
            "wisdom": self._character.stats["wisdom"],
            "charisma": self._character.stats["charisma"],
        }
        data["spellcasting_ability"] = self._character.spellcasting_ability
        data["total_hands"] = self._character.total_hands
        data["equipped_weapons"] = [
            weapon.name for weapon in self._character.equipped_weapons
        ]
        data["equipped_armor"] = [
            armor.name for armor in self._character.equipped_armor
        ]
        data["actions"] = list(self._character.actions.keys())
        data["spells"] = list(self._character.spells.keys())
        data["resistances"] = [res.name for res in self._character.resistances]
        data["vulnerabilities"] = [
            vuln.name for vuln in self._character.vulnerabilities
        ]
        data["number_of_attacks"] = self._character.number_of_attacks
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Character | None":
        """
        Create a Character instance from a dictionary representation.

        Args:
            data (dict[str, Any]): The dictionary representation of the character.

        Returns:
            Character | None: The Character instance if successful, None otherwise.
        """
        # Import here to avoid circular imports
        from .main import Character
        from core.content import ContentRepository

        # Get the content repositories (assume singleton is already initialized).
        repo = ContentRepository()
        # Get the type.
        char_type = CharacterType[data["type"].upper()]
        # Get the name.
        name = data["name"]
        # Get the race.
        race = repo.get_character_race(data["race"])
        assert race, f"Invalid race '{data['race']}' for character {name}."
        # Get the levels.
        levels: dict[CharacterClass, int] = {}
        for cls_name, cls_level in data["levels"].items():
            # Get the class from the class registry.
            cls = repo.get_character_class(cls_name)
            assert cls is not None, f"Invalid class '{cls_name}' for character {name}."
            assert (
                cls_level > 0
            ), f"Invalid class level '{cls_level}' for character {name}."
            # Add the class and its level to the levels dictionary.
            levels[cls] = cls_level
        # Get the stats.
        stats = data["stats"]
        # Get the spellcasting ability if present.
        spellcasting_ability = data.get("spellcasting_ability", None)
        # Get the total hands.
        total_hands = data.get("total_hands", 2)
        # Get the resistances.
        resistances = set()
        for res in data.get("resistances", []):
            resistances.add(DamageType[res.upper()])
        # Get the vulnerabilities.
        vulnerabilities = set()
        for vuln in data.get("vulnerabilities", []):
            vulnerabilities.add(DamageType[vuln.upper()])
        # Get the number of attacks.
        number_of_attacks = data.get("number_of_attacks", 1)

        # Create the character instance.
        char = Character(
            char_type,
            name,
            race,
            levels,
            stats,
            spellcasting_ability,
            total_hands,
            resistances,
            vulnerabilities,
            number_of_attacks,
        )

        # Get the list of equipped weapons.
        for weapon_name in data.get("equipped_weapons", []):
            weapon = repo.get_weapon(weapon_name)
            if weapon is None:
                log_warning(
                    f"Invalid weapon '{weapon_name}' for character {data['name']}",
                    {
                        "character": data["name"],
                        "weapon_name": weapon_name,
                        "context": "character_loading",
                    },
                )
                continue
            char.add_weapon(weapon)

        # Get the list of natural weapons.
        for weapon_name in data.get("natural_weapons", []):
            weapon = repo.get_weapon(weapon_name)
            if weapon is None:
                log_warning(
                    f"Invalid natural weapon '{weapon_name}' for character {data['name']}",
                    {
                        "character": data["name"],
                        "weapon_name": weapon_name,
                        "weapon_type": "natural",
                        "context": "character_loading",
                    },
                )
                continue
            char.natural_weapons.append(weapon)

        # Get the list of equipped armor.
        for armor_name in data.get("equipped_armor", []):
            armor = repo.get_armor(armor_name)
            if armor is None:
                log_warning(
                    f"Invalid armor '{armor_name}' for character {data['name']}",
                    {
                        "character": data["name"],
                        "armor_name": armor_name,
                        "context": "character_loading",
                    },
                )
                continue
            char.add_armor(armor)

        # Load the actions.
        for action_name in data.get("actions", []):
            action = repo.get_action(action_name)
            if action is None:
                log_warning(
                    f"Invalid action '{action_name}' for character {data['name']}",
                    {
                        "character": data["name"],
                        "action_name": action_name,
                        "context": "character_loading",
                    },
                )
                continue
            char.learn_action(action)

        # Load the spells.
        for spell_data in data.get("spells", []):
            spell = repo.get_spell(spell_data)
            if spell is None:
                log_warning(
                    f"Invalid spell '{spell_data}' for character {data['name']}",
                    {
                        "character": data["name"],
                        "spell_data": str(spell_data),
                        "context": "character_loading",
                    },
                )
                continue
            char.learn_spell(spell)

        # Load passive effects (like boss phase triggers).
        for effect_data in data.get("passive_effects", []):
            try:
                effect = Effect.from_dict(effect_data)
                if effect is not None:
                    char.add_passive_effect(effect)
            except Exception as e:
                log_warning(
                    f"Invalid passive effect for character {data['name']}: {e}",
                    {
                        "character": data["name"],
                        "effect_data": str(effect_data),
                        "error": str(e),
                        "context": "character_loading",
                    },
                )
                continue

        return char


def load_character(file_path: Path) -> "Character | None":
    """
    Loads a character from a JSON file.

    Args:
        file_path (Path): The path to the JSON file containing character data.

    Returns:
        Character | None: A Character instance if the file is valid, None otherwise.
    """
    try:
        with open(file_path, "r") as f:
            character_data = json.load(f)
            return CharacterSerialization.from_dict(character_data)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log_warning(
            f"Failed to load character from {file_path}: {e}",
            {
                "file_path": str(file_path),
                "error": str(e),
                "context": "character_file_loading",
            },
        )
        return None


def load_characters(file_path: Path) -> dict[str, "Character"]:
    """
    Loads characters from a JSON file.

    Args:
        file_path (Path): The path to the JSON file containing character data.

    Returns:
        dict[str, Character]: A dictionary mapping character names to Character instances.
    """
    from .main import Character

    characters: dict[str, Character] = {}
    with open(file_path, "r") as f:
        character_data = json.load(f)
        for entry in character_data:
            character = CharacterSerialization.from_dict(entry)
            if character is not None:
                characters[character.name] = character
    return characters
