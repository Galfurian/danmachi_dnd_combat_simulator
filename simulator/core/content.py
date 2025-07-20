import copy
import json
from pathlib import Path
from typing import Any, Optional

from actions.base_action import BaseAction
from actions.attacks import (
    BaseAttack,
    NaturalAttack,
    WeaponAttack,
    from_dict_attack,
)
from actions.spells import (
    Spell,
    SpellAttack,
    SpellBuff,
    SpellDebuff,
    SpellHeal,
    from_dict_spell,
)
from core.utils import Singleton, cprint, crule
from entities.character_class import CharacterClass
from entities.character_race import CharacterRace
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

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir:
            self.reload(data_dir)

    def reload(self, root: Path) -> None:
        """(Re)load all JSON/YAML assets from disk—handy for hot-reloading."""

        crule("Reloading Database", style="bold green")

        cprint(f"Loading content from: [bold blue]{root}[/bold blue]")

        def load_json_file(filename: str, loader_func, description: str):
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
            self.spells = load_json_file("spells.json", self._load_spells, "spells")
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
    ) -> Any | None:
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

    def get_spell_attack(self, name: str) -> SpellAttack | None:
        """Get a spell attack by name, or None if not found."""
        return self._get_from_collection("spells", name, SpellAttack)

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
    def _load_character_classes(data) -> dict[str, CharacterClass]:
        classes = {}
        for class_data in data:
            character_class = CharacterClass.from_dict(class_data)
            if character_class.name in classes:
                raise ValueError(f"Duplicate class name: {character_class.name}")
            classes[character_class.name] = character_class
        return classes

    @staticmethod
    def _load_character_races(data) -> dict[str, CharacterRace]:
        races = {}
        for race_data in data:
            character_race = CharacterRace.from_dict(race_data)
            if character_race.name in races:
                raise ValueError(f"Duplicate race name: {character_race.name}")
            races[character_race.name] = character_race
        return races

    @staticmethod
    def _load_armors(data) -> dict[str, Armor]:
        armors = {}
        for armor_data in data:
            armor = Armor.from_dict(armor_data)
            if armor.name in armors:
                raise ValueError(f"Duplicate armor name: {armor.name}")
            armors[armor.name] = armor
        return armors

    @staticmethod
    def _load_weapons(data) -> dict[str, Weapon]:
        """Load weapons from the given data."""
        weapons: dict[str, Weapon] = {}
        for weapon_data in data:
            weapon = Weapon.from_dict(weapon_data)
            if weapon.name in weapons:
                raise ValueError(f"Duplicate weapon name: {weapon.name}")
            weapons[weapon.name] = weapon
        return weapons

    def _load_actions(self, data) -> dict[str, BaseAction]:
        """Load actions from the given data."""
        actions: dict[str, BaseAction] = {}
        for action_data in data:
            action = from_dict_attack(action_data)
            if not action:
                action = from_dict_spell(action_data)
                if not action:
                    from actions.abilities import from_dict_ability

                    action = from_dict_ability(action_data)
                    if not action:
                        raise ValueError(f"Invalid action data: {action_data}")
            actions[action.name] = action
        return actions

    def _load_spells(self, data) -> dict[str, BaseAction]:
        """Load spells from the given data."""
        spells: dict[str, BaseAction] = {}
        for spell_data in data:
            spell = from_dict_spell(spell_data)
            if not spell:
                raise ValueError(f"Invalid spell data: {spell_data}")
            if spell.name in spells:
                raise ValueError(f"Duplicate spell name: {spell.name}")
            spells[spell.name] = spell
        return spells

    @staticmethod
    def _load_base_attacks(data) -> dict[str, BaseAttack]:
        attacks: dict[str, BaseAttack] = {}
        # Load base attacks.
        for attack_data in data:
            base_attack = from_dict_attack(attack_data)
            if base_attack is None:
                continue  # Skip invalid attacks
            if base_attack.name in attacks:
                raise ValueError(f"Duplicate attack name: {base_attack.name}")
            attacks[base_attack.name] = base_attack
        return attacks
