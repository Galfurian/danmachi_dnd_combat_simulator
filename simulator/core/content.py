from pathlib import Path
from rich.console import Console
from rich.rule import Rule

from actions.base_action import *
from actions.attack_action import *
from actions.spell_action import *
from effects.effect import *
from entities.character_class import *
from entities.character_race import *
from core.utils import *

import copy
import json

console = Console()


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
    attacks: dict[str, BaseAttack]
    armors: dict[str, Armor]
    # Action-related attributes.
    spells: dict[str, BaseAction]
    actions: dict[str, BaseAction]

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir:
            self.reload(data_dir)

    def reload(self, root: Path) -> None:
        """(Re)load all JSON/YAML assets from disk—handy for hot-reloading."""

        console.print(Rule("Reloading Database", style="bold green"))

        console.print(
            f"Loading content from: [bold blue]{root}[/bold blue]", style="bold yellow"
        )

        console.print("Loading character classes...", style="bold yellow")

        # Load the character classes.
        with open(root / "character_classes.json", "r") as f:
            data = json.load(f)
            if not isinstance(data, list):
                raise ValueError(
                    f"Expected a list in {root / 'character_classes.json'}"
                )
            self.classes = self._load_character_classes(data)

        console.print("Loading character races...", style="bold yellow")

        # Load the character races.
        with open(root / "character_races.json", "r") as f:
            data = json.load(f)
            if not isinstance(data, list):
                raise ValueError(f"Expected a list in {root / 'character_races.json'}")
            self.races = self._load_character_races(data)

        console.print("Loading attacks...", style="bold yellow")

        # Load the attacks.
        with open(root / "attacks.json", "r") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError(f"Expected a dict in {root / 'attacks.json'}")
            if "attacks" not in data:
                raise ValueError(f"No 'attacks' key found in {root / 'attacks.json'}")
            if "variants" not in data:
                raise ValueError(f"No 'variants' key found in {root / 'attacks.json'}")
            # First, load the base attacks.
            self.attacks = self._load_base_attacks(data["attacks"])
            # Then, load the attack variants.
            attack_variants = self._load_attack_variants(data["variants"], self.attacks)
            # Add the variants to the attacks dictionary.
            self.attacks.update(attack_variants)

        console.print("Loading armors...", style="bold yellow")

        # Load the armors.
        with open(root / "armors.json", "r") as f:
            data = json.load(f)
            if not isinstance(data, list):
                raise ValueError(f"Expected a list in {root / 'armors.json'}")
            self.armors = self._load_armors(data)

        console.print("Loading spells...", style="bold yellow")

        # Load the spells and actions.
        with open(root / "spells.json", "r") as f:
            data = json.load(f)
            if not isinstance(data, list):
                raise ValueError(f"Expected a list in {root / 'spells.json'}")
            self.spells = self._load_spells(data)

        console.print("Loading actions...", style="bold yellow")

        with open(root / "actions.json", "r") as f:
            data = json.load(f)
            if not isinstance(data, list):
                raise ValueError(f"Expected a list in {root / 'actions.json'}")
            self.actions = self._load_actions(data)

        console.print("Content loaded successfully!\n", style="bold green")

    def get_character_class(self, name: str) -> CharacterClass | None:
        """Get a character class by name, or None if not found.

        Args:
            name (str): The name of the character class.

        Returns:
            CharacterClass | None: The character class instance or None.
        """
        entry = self.classes.get(name)
        if entry and isinstance(entry, CharacterClass):
            return entry
        return None

    def get_character_race(self, name: str) -> CharacterRace | None:
        """Get a character race by name, or None if not found.

        Args:
            name (str): The name of the character race.

        Returns:
            CharacterRace | None: The character race instance or None.
        """
        entry = self.races.get(name)
        if entry and isinstance(entry, CharacterRace):
            return entry
        return None

    def get_armor(self, name: str) -> Armor | None:
        """Get an armor effect by name, or None if not found.

        Args:
            name (str): The name of the armor effect.

        Returns:
            Effect | None: The armor effect instance or None.
        """
        entry = self.armors.get(name)
        if entry and isinstance(entry, Armor):
            return entry
        return None

    def get_action(self, name: str) -> BaseAction | None:
        """Get an action by name, or None if not found.

        Args:
            name (str): The name of the action.

        Returns:
            BaseAction | None: The action instance or None.
        """
        entry = self.actions.get(name)
        if entry and isinstance(entry, BaseAction):
            return entry
        return None

    def get_base_attack(self, name: str) -> BaseAttack | None:
        """Get a base attack by name, or None if not found.

        Args:
            name (str): The name of the base attack.

        Returns:
            BaseAttack | None: The base attack instance or None.
        """
        entry = self.attacks.get(name)
        if entry and isinstance(entry, BaseAttack):
            return entry
        return None

    def get_spell(self, name: str) -> BaseAction | None:
        """Get a spell by name, or None if not found.

        Args:
            name (str): The name of the spell.

        Returns:
            BaseAction | None: The spell instance or None.
        """
        entry = self.spells.get(name)
        if entry and isinstance(entry, BaseAction):
            return entry
        return None

    def get_spell_attack(self, name: str) -> SpellAttack | None:
        """Get a spell attack by name, or None if not found.

        Args:
            name (str): The name of the spell attack.

        Returns:
            SpellAttack | None: The spell attack instance or None.
        """
        entry = self.spells.get(name)
        if entry and isinstance(entry, SpellAttack):
            return entry
        return None

    def get_spell_heal(self, name: str) -> SpellHeal | None:
        """Get a spell heal by name, or None if not found.

        Args:
            name (str): The name of the spell heal.

        Returns:
            SpellHeal | None: The spell heal instance or None.
        """
        entry = self.spells.get(name)
        if entry and isinstance(entry, SpellHeal):
            return entry
        return None

    def get_spell_buff(self, name: str) -> SpellBuff | None:
        """Get a spell buff by name, or None if not found.

        Args:
            name (str): The name of the spell buff.

        Returns:
            SpellBuff | None: The spell buff instance or None.
        """
        entry = self.spells.get(name)
        if entry and isinstance(entry, SpellBuff):
            return entry
        return None

    def get_spell_debuff(self, name: str) -> SpellDebuff | None:
        """Get a spell debuff by name, or None if not found.

        Args:
            name (str): The name of the spell debuff.

        Returns:
            SpellDebuff | None: The spell debuff instance or None.
        """
        entry = self.spells.get(name)
        if entry and isinstance(entry, SpellDebuff):
            return entry
        return None

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

    def _load_actions(self, data) -> dict[str, BaseAction]:
        """Load actions from the given data."""
        actions: dict[str, BaseAction] = {}
        for action_data in data:
            action = from_dict_attack(action_data, self.attacks)
            if not action:
                action = from_dict_spell(action_data)
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
            base_attack = BaseAttack.from_dict(attack_data)
            if base_attack.name in attacks:
                raise ValueError(f"Duplicate attack name: {base_attack.name}")
            attacks[base_attack.name] = base_attack
        return attacks

    @staticmethod
    def _load_attack_variants(
        data, base_attacks: dict[str, BaseAttack]
    ) -> dict[str, BaseAttack]:
        variants: dict[str, BaseAttack] = {}
        for variant_data in data:
            base_attack = base_attacks.get(variant_data["base"])
            if not base_attack:
                raise ValueError(
                    f"Base attack '{variant_data['base']}' not found in attacks."
                )
            # Generate the variant.
            variant = copy.deepcopy(base_attack)
            # Set the variant name and apply deltas.
            variant.name = variant_data["name"]
            if mod := variant_data.get("attack_roll_mod"):
                variant.attack_roll += (
                    f"{mod:+}" if not mod.startswith(("+", "-")) else mod
                )
            if mod := variant_data.get("damage_roll_mod"):
                for comp in variant.damage:
                    comp.damage_roll += (
                        f"{mod:+}" if not mod.startswith(("+", "-")) else mod
                    )
            # blanket overrides / additions
            for k, v in variant_data.get("delta", {}).items():
                if k not in ("attack_roll_mod", "damage_roll_mod"):
                    setattr(variant, k, v)
            if variant.name in base_attacks:
                raise ValueError(f"Duplicate attack variant name: {variant.name}")
            variants[variant.name] = variant
        return variants
