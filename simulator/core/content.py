import copy
import json
from pathlib import Path
from typing import Any, Optional, Callable

from actions.base_action import BaseAction
from actions.spells import (
    SpellAttack,
    SpellBuff,
    SpellDebuff,
    SpellHeal,
)
from core.utils import Singleton, cprint, crule
from character.character_class import CharacterClass
from character.character_race import CharacterRace
from items.armor import Armor
from items.weapon import Weapon
from core.error_handling import log_critical, log_error


class ContentRepository(metaclass=Singleton):
    """
    One-stop registry for every game-asset that needs fast by-name access.
    Usage:
        repo = ContentRepository()
        magic_missile = repo.spells["Magic Missile"]
        longsword = repo.attacks["Longsword"]
    """

    # Character-related attributes.
    classes: dict[str, CharacterClass]
    races: dict[str, CharacterRace]
    # Item-related attributes.
    weapons: dict[str, Weapon]
    armors: dict[str, Armor]
    # Action-related attributes.
    spells: dict[str, BaseAction]
    actions: dict[str, BaseAction]

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        """
        Initialize the ContentRepository.
        
        Args:
            data_dir (Optional[Path]): The directory containing data files to load.
        """
        if data_dir:
            self.reload(data_dir)

    def reload(self, root: Path) -> None:
        """(Re)load all JSON/YAML assets from disk—handy for hot-reloading."""

        cprint(f"Loading content from: [bold blue]{root}[/bold blue]")

        def load_json_file(filename: str, loader_func: Callable, description: str) -> dict:
            """Helper to load and validate JSON files"""
            try:
                cprint(f"Loading {description}...")

                # Validate file path
                file_path = root / filename
                if not file_path.exists():
                    log_error(
                        f"Data file not found: {filename}",
                        {"filename": filename, "path": str(file_path)},
                    )
                    raise FileNotFoundError(f"File not found: {file_path}")

                if not file_path.is_file():
                    log_error(
                        f"Path is not a file: {filename}",
                        {"filename": filename, "path": str(file_path)},
                    )
                    raise ValueError(f"Not a file: {file_path}")

                # Load and validate JSON
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if not isinstance(data, list):
                    log_error(
                        f"Expected a list in {filename}, got {type(data).__name__}",
                        {"filename": filename, "data_type": type(data).__name__},
                    )
                    raise ValueError(
                        f"Expected a list in {file_path}, got {type(data).__name__}"
                    )

                if not data:
                    log_error(f"Empty data list in {filename}", {"filename": filename})
                return loader_func(data)

            except json.JSONDecodeError as e:
                log_error(
                    f"Invalid JSON in {filename}: {str(e)}",
                    {"filename": filename, "error": str(e)},
                    e,
                )
                raise ValueError(f"Invalid JSON in {filename}: {e}")

            except Exception as e:
                log_error(
                    f"Error loading {filename}: {str(e)}",
                    {"filename": filename, "description": description},
                    e,
                )
                raise

        try:
            # Load all content using the helper
            self.classes = load_json_file(
                "character_classes.json",
                self._load_character_classes,
                "character classes",
            )
            self.races = load_json_file(
                "character_races.json", self._load_character_races, "character races"
            )

            # Load weapons (special case - two files)
            self.weapons = load_json_file(
                "weapons_natural.json", self._load_weapons, "natural weapons"
            )
            self.weapons.update(
                load_json_file(
                    "weapons_wielded.json", self._load_weapons, "wielded weapons"
                )
            )

            self.armors = load_json_file("armors.json", self._load_armors, "armors")
            self.spells = load_json_file("spells.json", self._load_actions, "spells")
            self.actions = load_json_file("actions.json", self._load_actions, "actions")

            cprint("Content loaded successfully!\n")

        except Exception as e:
            log_critical(
                f"Critical error during content loading: {str(e)}",
                {"root_path": str(root), "error": str(e)},
            )
            raise

    def _get_from_collection(
        self, collection_name: str, item_name: str, expected_type: Optional[type] = None
    ) -> Optional[Any]:
        """Generic helper to get an item from any collection with optional type checking.

        Args:
            collection_name (str): Name of the collection attribute (e.g., 'weapons', 'spells')
            item_name (str): Name of the item to retrieve
            expected_type (type, optional): Expected type for isinstance check

        Returns:
            Any | None: The item if found and type matches, None otherwise
        """
        collection = getattr(self, collection_name, None)
        if not collection:
            return None

        entry = collection.get(item_name)
        if entry and (expected_type is None or isinstance(entry, expected_type)):
            return entry
        return None

    def get_character_class(self, name: str) -> Optional[CharacterClass]:
        """Get a character class by name, or None if not found."""
        return self._get_from_collection("classes", name, CharacterClass)

    def get_character_race(self, name: str) -> Optional[CharacterRace]:
        """Get a character race by name, or None if not found."""
        return self._get_from_collection("races", name, CharacterRace)

    def get_weapon(self, name: str) -> Optional[Weapon]:
        """Get a weapon by name, or None if not found."""
        return self._get_from_collection("weapons", name, Weapon)

    def get_armor(self, name: str) -> Optional[Armor]:
        """Get an armor by name, or None if not found."""
        return self._get_from_collection("armors", name, Armor)

    def get_action(self, name: str) -> Optional[BaseAction]:
        """Get an action by name, or None if not found."""
        return self._get_from_collection("actions", name, BaseAction)

    def get_spell(self, name: str) -> Optional[BaseAction]:
        """Get a spell by name, or None if not found."""
        return self._get_from_collection("spells", name, BaseAction)

    def get_spell_attack(self, name: str) -> Optional[SpellAttack]:
        """Get a spell attack by name, or None if not found."""
        return self._get_from_collection("spells", name, SpellAttack)

    def get_spell_heal(self, name: str) -> Optional[SpellHeal]:
        """Get a spell heal by name, or None if not found."""
        return self._get_from_collection("spells", name, SpellHeal)

    def get_spell_buff(self, name: str) -> Optional[SpellBuff]:
        """Get a spell buff by name, or None if not found."""
        return self._get_from_collection("spells", name, SpellBuff)

    def get_spell_debuff(self, name: str) -> Optional[SpellDebuff]:
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
            character_class = CharacterClass.from_dict(class_data)
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
            character_race = CharacterRace.from_dict(race_data)
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
            armor = Armor.from_dict(armor_data)
            if armor.name in armors:
                raise ValueError(f"Duplicate armor name: {armor.name}")
            armors[armor.name] = armor
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
        weapons: dict[str, Weapon] = {}
        for weapon_data in data:
            weapon = Weapon.from_dict(weapon_data)
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
        from actions.abilities.ability_serializer import AbilityDeserializer
        from actions.attacks.attack_serializer import AttackDeserializer
        from actions.spells.spell_serializer import SpellDeserializer

        actions: dict[str, BaseAction] = {}
        for action_data in data:
            action = AttackDeserializer.deserialize(action_data)
            if not action:
                action = SpellDeserializer.deserialize(action_data)
                if not action:
                    action = AbilityDeserializer.deserialize(action_data)
                    if not action:
                        raise ValueError(f"Invalid action data: {action_data}")
            actions[action.name] = action
        return actions
