"""
Character serialization and deserialization functions.

This module provides functions to serialize and deserialize Character instances
to and from dictionaries and JSON files.
"""

import json
from pathlib import Path
from typing import Any

from character.character_class import CharacterClass
from character.character_effects import ValidPassiveEffect
from character.main import Character
from core.constants import CharacterType, DamageType
from core.logging import log_error


def character_from_dict(data: dict[str, Any]) -> Character:
    """
    Creates a Character instance from a dictionary of data.

    Args:
        data (dict[str, Any]):
            The dictionary containing character data.

    Returns:
        Character:
            The created Character instance.

    """
    from core.content import ContentRepository
    from effects.base_effect import deserialize_effect
    from items.weapon import NaturalWeapon, WieldedWeapon

    # Get the repository instance.
    repo = ContentRepository()

    # Get the race.
    race_name: str = data.get("race", "")
    race = repo.get_character_race(race_name)
    if not race:
        raise ValueError(f"Character race '{race_name}' not found.")

    # Get the levels.
    levels: dict[CharacterClass, int] = {}
    for class_name, level in data.get("levels", {}).items():
        character_class = repo.get_character_class(class_name)
        if not character_class:
            raise ValueError(f"Character class '{class_name}' not found.")
        levels[character_class] = level

    # Load the passive effects.
    passive_effects: list[ValidPassiveEffect] = []
    for effect_data in data.get("passive_effects", []):
        effect = deserialize_effect(effect_data)
        if not effect:
            raise ValueError(f"Failed to deserialize effect: {effect_data}")
        if not isinstance(effect, ValidPassiveEffect):
            raise ValueError(f"Effect is not a valid passive effect: {effect_data}")
        passive_effects.append(effect)

    character = Character(
        name=data["name"],
        char_type=CharacterType(data["char_type"]),
        race=race,
        levels=levels,
        stats=data["stats"],
        spellcasting_ability=data.get("spellcasting_ability", None),
        total_hands=data.get("total_hands", 2),
        immunities={DamageType(dt) for dt in data.get("immunities", [])},
        resistances={DamageType(dt) for dt in data.get("resistances", [])},
        vulnerabilities={DamageType(dt) for dt in data.get("vulnerabilities", [])},
        number_of_attacks=data.get("number_of_attacks", 1),
        passive_effects=passive_effects,
    )

    # Add default race spells.
    for spell_name in character.race.default_spells:
        spell = repo.get_spell(spell_name)
        if spell:
            character.actions.learn(spell)

    # Get spells from each class level
    for character_class, class_level in character.levels.items():
        # Get all spells up to the current class level
        spell_names = character_class.get_all_spells_up_to_level(class_level)
        # Get all actions up to the current class level
        action_names = character_class.get_all_actions_up_to_level(class_level)
        for spell_name in spell_names:
            spell = repo.get_spell(spell_name)
            if spell:
                character.actions.learn(spell)
        for action_name in action_names:
            action = repo.get_action(action_name)
            if action:
                character.actions.learn(action)
            else:
                spell = repo.get_spell(action_name)
                if spell:
                    character.actions.learn(spell)

    # Replace actions with actual instances.
    for action_name in data.get("actions", []):
        action = repo.get_action(action_name)
        if action:
            character.actions.learn(action)
        else:
            spell = repo.get_spell(action_name)
            if not spell:
                raise ValueError(
                    f"Action or spell '{action_name}' not found in repository."
                )
            character.actions.learn(spell)
    # Replace spells with actual instances.
    for spell_name in data.get("spells", []):
        spell = repo.get_spell(spell_name)
        if not spell:
            raise ValueError(f"Spell '{spell_name}' not found in repository.")
        character.actions.learn(spell)

    # Replace equipped weapons with actual instances.
    for weapon_name in data.get("wielded_weapons", []):
        weapon = repo.get_weapon(weapon_name)
        if not weapon:
            raise ValueError(f"Weapon '{weapon_name}' not found in repository.")
        if not isinstance(weapon, WieldedWeapon):
            raise ValueError(f"Weapon '{weapon_name}' is not a WieldedWeapon.")
        character.inventory.add_weapon(weapon)

    # Replace natural weapons with actual instances.
    for weapon_name in data.get("natural_weapons", []):
        weapon = repo.get_weapon(weapon_name)
        if not weapon:
            raise ValueError(f"Natural weapon '{weapon_name}' not found in repository.")
        if not isinstance(weapon, NaturalWeapon):
            raise ValueError(f"Weapon '{weapon_name}' is not a NaturalWeapon.")
        character.inventory.add_weapon(weapon)

    # Replace equipped armor with actual instances.
    for armor_name in data.get("armors", []):
        armor = repo.get_armor(armor_name)
        if not armor:
            raise ValueError(f"Armor '{armor_name}' not found in repository.")
        character.inventory.add_armor(armor)

    return character


def load_character(file_path: Path) -> Character | None:
    """
    Loads a character from a JSON file.

    Args:
        file_path (str): The path to the JSON file containing character data.

    Returns:
        Character | None: A Character instance if the file is valid, None otherwise.

    """
    try:
        with open(file_path) as f:
            return character_from_dict(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log_error(
            f"Failed to load character from {file_path}: {e}",
            {
                "file_path": str(file_path),
                "error": str(e),
                "context": "character_file_loading",
            },
        )
        return None


def load_characters(file_path: Path) -> dict[str, Character]:
    """
    Loads characters from a JSON file.

    Args:
        file_path (Path):
            The path to the JSON file containing character data.

    Returns:
        dict[str, Character]: A dictionary mapping character names to Character instances.

    """
    characters: dict[str, Character] = {}
    try:
        with open(file_path) as f:
            character_list = json.load(f)
            if isinstance(character_list, list):
                for character_data in character_list:
                    character = character_from_dict(character_data)
                    if character is not None:
                        characters[character.name] = character
            else:
                log_error(
                    f"Character data in {file_path} is not a list.",
                    {
                        "file_path": str(file_path),
                        "error": "Invalid format",
                        "context": "character_file_loading",
                    },
                )
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log_error(
            f"Failed to load character from {file_path}: {e}",
            {
                "file_path": str(file_path),
                "error": str(e),
                "context": "character_file_loading",
            },
        )
    return characters
