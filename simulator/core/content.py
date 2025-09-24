import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from actions.base_action import BaseAction
from actions.spells import (
    SpellBuff,
    SpellDebuff,
    SpellHeal,
    SpellOffensive,
)
from actions.spells.base_spell import Spell
from catchery import log_warning
from character.character_class import CharacterClass
from character.character_race import CharacterRace
from items.armor import Armor
from items.weapon import Weapon

from core.utils import Singleton, cprint


class ContentRepository(metaclass=Singleton):
    """
    One-stop registry for every game-asset that needs fast by-name access.
    """

    # Character-related attributes.
    classes: dict[str, CharacterClass]
    races: dict[str, CharacterRace]
    # Item-related attributes.
    weapons: dict[str, Weapon]
    armors: dict[str, Armor]
    # Action-related attributes.
    spells: dict[str, Spell]
    actions: dict[str, BaseAction]

    def __init__(self, data_dir: Path | None = None) -> None:
        """
        Initialize the ContentRepository.

        Args:
            data_dir (Path | None):
                The directory containing data files to load.

        """
        if data_dir:
            self.reload(data_dir)
            self.loaded = True
        elif not hasattr(self, "loaded"):
            raise ValueError(
                "ContentRepository must be initialized with a valid data_dir on first use."
            )

    def reload(self, root: Path) -> None:
        """
        (Re)load all JSON/YAML assets from disk—handy for hot-reloading.

        Args:
            root (Path):
                The directory containing data files to load.
        """
        # Load all content using the helper
        self.classes = _load_json_file(
            root / "character_classes.json",
            self._load_character_classes,
            "character classes",
        )
        self.races = _load_json_file(
            root / "character_races.json",
            self._load_character_races,
            "character races",
        )

        # Load weapons (special case - two files)
        self.weapons = _load_json_file(
            root / "weapons_natural.json",
            self._load_weapons,
            "natural weapons",
        )
        self.weapons.update(
            _load_json_file(
                root / "weapons_wielded.json",
                self._load_weapons,
                "wielded weapons",
            )
        )

        self.armors = _load_json_file(
            root / "armors.json",
            self._load_armors,
            "armors",
        )
        self.spells = _load_json_file(
            root / "spells.json",
            self._load_actions,
            "spells",
        )
        self.actions = _load_json_file(
            root / "abilities.json",
            self._load_actions,
            "actions",
        )

    def _get_from_collection(
        self,
        collection_name: str,
        item_name: str,
        expected_type: type | None = None,
    ) -> Any | None:
        """
        Generic helper to get an item from any collection with optional type checking.

        Args:
            collection_name (str):
                Name of the collection attribute (e.g., 'weapons', 'spells')
            item_name (str):
                Name of the item to retrieve
            expected_type (type, optional):
                Expected type for isinstance check

        Returns:
            Any | None:
                The item if found and type matches, None otherwise

        """
        collection = getattr(self, collection_name, None)
        # Check if collection exists.
        if not collection:
            log_warning(
                f"Collection '{collection_name}' not found in ContentRepository.",
                {
                    "collection_name": collection_name,
                    "item_name": item_name,
                    "expected_type": expected_type,
                },
            )
            return None
        # Get the entry.
        entry = collection.get(item_name)
        # Check type if specified.
        if entry and expected_type and not isinstance(entry, expected_type):
            log_warning(
                f"Item '{item_name}' in collection '{collection_name}' "
                f"is not of expected type '{expected_type.__name__}'.",
                {
                    "collection_name": collection_name,
                    "item_name": item_name,
                    "expected_type": expected_type,
                    "actual_type": type(entry).__name__,
                },
            )
            return None
        return entry

    def get_character_class(self, name: str) -> CharacterClass | None:
        """Get a character class by name, or None if not found."""
        return self._get_from_collection("classes", name, CharacterClass)

    def get_character_race(self, name: str) -> CharacterRace | None:
        """Get a character race by name, or None if not found."""
        return self._get_from_collection("races", name, CharacterRace)

    def get_weapon(self, name: str) -> Weapon | None:
        """Get a weapon by name, or None if not found."""
        return self._get_from_collection("weapons", name, Weapon)

    def get_armor(self, name: str) -> Armor | None:
        """Get an armor by name, or None if not found."""
        return self._get_from_collection("armors", name, Armor)

    def get_action(self, name: str) -> BaseAction | None:
        """Get an action by name, or None if not found."""
        return self._get_from_collection("actions", name, BaseAction)

    def get_spell(self, name: str) -> BaseAction | None:
        """Get a spell by name, or None if not found."""
        return self._get_from_collection("spells", name, BaseAction)

    def get_spell_attack(self, name: str) -> SpellOffensive | None:
        """Get a spell attack by name, or None if not found."""
        return self._get_from_collection("spells", name, SpellOffensive)

    def get_spell_heal(self, name: str) -> SpellHeal | None:
        """Get a spell heal by name, or None if not found."""
        return self._get_from_collection("spells", name, SpellHeal)

    def get_spell_buff(self, name: str) -> SpellBuff | None:
        """Get a spell buff by name, or None if not found."""
        return self._get_from_collection("spells", name, SpellBuff)

    def get_spell_debuff(self, name: str) -> SpellDebuff | None:
        """Get a spell debuff by name, or None if not found."""
        return self._get_from_collection("spells", name, SpellDebuff)

    @staticmethod
    def _load_character_classes(data: list[dict]) -> dict[str, CharacterClass]:
        """
        Load character classes from JSON data.

        Args:
            data (list[dict]): List of character class data dictionaries.

        Returns:
            dict[str, CharacterClass]: Dictionary mapping class names to CharacterClass objects.

        Raises:
            ValueError: If duplicate class names are found.

        """
        classes = {}
        for class_data in data:
            character_class = CharacterClass(**class_data)
            if character_class.name in classes:
                raise ValueError(f"Duplicate class name: {character_class.name}")
            classes[character_class.name] = character_class
        return classes

    @staticmethod
    def _load_character_races(data: list[dict]) -> dict[str, CharacterRace]:
        """
        Load character races from JSON data.

        Args:
            data (list[dict]): List of character race data dictionaries.

        Returns:
            dict[str, CharacterRace]: Dictionary mapping race names to CharacterRace objects.

        Raises:
            ValueError: If duplicate race names are found.

        """
        races = {}
        for race_data in data:
            character_race = CharacterRace(**race_data)
            if character_race.name in races:
                raise ValueError(f"Duplicate race name: {character_race.name}")
            races[character_race.name] = character_race
        return races

    @staticmethod
    def _load_armors(data: list[dict]) -> dict[str, Armor]:
        """
        Load armors from JSON data.

        Args:
            data (list[dict]): List of armor data dictionaries.

        Returns:
            dict[str, Armor]: Dictionary mapping armor names to Armor objects.

        Raises:
            ValueError: If duplicate armor names are found.

        """
        armors = {}
        for armor_data in data:
            armors[armor_data["name"]] = Armor(**armor_data)
        return armors

    @staticmethod
    def _load_weapons(data: list[dict]) -> dict[str, Weapon]:
        """
        Load weapons from JSON data.

        Args:
            data (list[dict]): List of weapon data dictionaries.

        Returns:
            dict[str, Weapon]: Dictionary mapping weapon names to Weapon objects.

        Raises:
            ValueError: If duplicate weapon names are found.

        """
        from items.weapon import deserialize_weapon

        weapons: dict[str, Weapon] = {}
        for weapon_data in data:
            weapon = deserialize_weapon(weapon_data)
            if weapon.name in weapons:
                raise ValueError(f"Duplicate weapon name: {weapon.name}")
            weapons[weapon.name] = weapon
        return weapons

    def _load_actions(self, data: list[dict]) -> dict[str, BaseAction]:
        """
        Load actions from JSON data.

        Args:
            data (list[dict]): List of action data dictionaries.

        Returns:
            dict[str, BaseAction]: Dictionary mapping action names to BaseAction objects.

        Raises:
            ValueError: If invalid action data is encountered.

        """
        from actions.abilities.base_ability import deserialize_ability
        from actions.attacks.base_attack import deserialize_attack
        from actions.spells.base_spell import deserialize_spell

        actions: dict[str, BaseAction] = {}
        for action_data in data:
            ability = deserialize_ability(action_data)
            if ability:
                actions[ability.name] = ability
                continue
            attack = deserialize_attack(action_data)
            if attack:
                actions[attack.name] = attack
                continue
            spell = deserialize_spell(action_data)
            if spell:
                actions[spell.name] = spell
                continue
            raise ValueError(f"Invalid action data: {action_data}")

        return actions


def _load_json_file(
    filepath: Path,
    loader_func: Callable[[list[dict]], dict[str, Any]],
    description: str,
) -> dict[str, Any]:
    """Helper to load and validate JSON files"""
    try:
        cprint(
            f"  Loading {description} using {loader_func.__name__}...",
            style="bold green",
        )
        # Validate file path
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        if not filepath.is_file():
            raise ValueError(f"Not a file: {filepath}")
        # Load and validate JSON
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        if not data:
            raise ValueError(f"Empty data list in {filepath}")
        if not isinstance(data, list):
            raise ValueError(f"Expected list in {filepath}, got {type(data).__name__}")
        return loader_func(data)
    except (json.JSONDecodeError, FileNotFoundError, ValueError) as e:
        raise ValueError(f"File {filepath} raised an error: {e}")
