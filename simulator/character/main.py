"""
Character management module for the simulator.

Defines the Character class and related functions for creating, loading, and
managing characters, including stats, equipment, actions, spells, and effects.
Handles character serialization from JSON data.
"""

import json
from pathlib import Path
from typing import Any

from actions.attacks.natural_attack import NaturalAttack
from actions.attacks.weapon_attack import WeaponAttack
from actions.base_action import BaseAction
from actions.spells.base_spell import BaseSpell
from core.constants import ActionClass, BonusType, CharacterType, DamageType
from core.dice_parser import VarInfo
from core.logging import log_error
from core.utils import cprint
from effects.base_effect import Effect, EventResponse, deserialize_effect
from effects.event_system import DamageTakenEvent, HitEvent
from effects.incapacitating_effect import IncapacitatingEffect
from items.armor import Armor
from items.weapon import NaturalWeapon, Weapon, WieldedWeapon

from .character_actions import CharacterActions
from .character_class import CharacterClass
from .character_display import CharacterDisplay
from .character_effects import CharacterEffects, ValidPassiveEffect
from .character_inventory import CharacterInventory
from .character_race import CharacterRace
from .character_stats import CharacterStats


class Character:
    """
    Represents a character in the game, including stats, equipment, actions,
    effects, and all related management modules. Provides methods for stat
    calculation, action and spell management, equipment handling, effect
    processing, and serialization.
    """

    # === Static properties ===

    char_type: CharacterType
    name: str
    race: CharacterRace
    levels: dict[CharacterClass, int]
    spellcasting_ability: str | None
    total_hands: int
    resistances: set[DamageType]
    vulnerabilities: set[DamageType]
    number_of_attacks: int
    passive_effects: list[ValidPassiveEffect]

    # === Dynamic properties ===

    equipped_weapons: list["WieldedWeapon"]
    natural_weapons: list["NaturalWeapon"]
    equipped_armor: list[Armor]
    actions: dict[str, BaseAction]
    spells: dict[str, BaseSpell]

    # === Management Modules ===

    effects_module: CharacterEffects
    stats: CharacterStats
    inventory_module: CharacterInventory
    actions_module: CharacterActions
    display_module: CharacterDisplay

    def __init__(
        self,
        char_type: CharacterType,
        name: str,
        race: CharacterRace,
        levels: dict[CharacterClass, int],
        stats: dict[str, int],
        spellcasting_ability: str | None,
        total_hands: int,
        resistances: set[DamageType],
        vulnerabilities: set[DamageType],
        number_of_attacks: int,
        passive_effects: list[ValidPassiveEffect],
    ) -> None:
        # Initialize static properties.
        self.char_type = char_type
        self.name = name
        self.race = race
        self.levels = levels
        self.spellcasting_ability = spellcasting_ability
        self.total_hands = total_hands
        self.resistances = resistances
        self.vulnerabilities = vulnerabilities
        self.number_of_attacks = number_of_attacks
        self.passive_effects = passive_effects

        # Initialize dynamic properties.
        self.equipped_weapons = []
        self.natural_weapons = []
        self.equipped_armor = []
        self.actions = {}
        self.spells = {}

        # Initialize modules.
        self.effects_module = CharacterEffects(owner=self)
        self.stats = CharacterStats(owner=self, stats=stats)
        self.inventory_module = CharacterInventory(owner=self)
        self.actions_module = CharacterActions(owner=self)
        self.display_module = CharacterDisplay(owner=self)

    # ============================================================================
    # DELEGATED STAT PROPERTIES
    # ============================================================================
    # These properties delegate to the stats module for calculation

    @property
    def colored_name(self) -> str:
        """
        Returns the character's name with color coding based on character type.
        """
        return self.char_type.colorize(self.name)

    @property
    def HP_MAX(self) -> int:
        """Returns the maximum HP of the character."""
        return self.stats.HP_MAX

    @property
    def MIND_MAX(self) -> int:
        """Returns the maximum Mind of the character."""
        return self.stats.MIND_MAX

    @property
    def STR(self) -> int:
        """Returns the D&D strength modifier."""
        return self.stats.STR

    @property
    def DEX(self) -> int:
        """Returns the D&D dexterity modifier."""
        return self.stats.DEX

    @property
    def CON(self) -> int:
        """Returns the D&D constitution modifier."""
        return self.stats.CON

    @property
    def INT(self) -> int:
        """Returns the D&D intelligence modifier."""
        return self.stats.INT

    @property
    def WIS(self) -> int:
        """Returns the D&D wisdom modifier."""
        return self.stats.WIS

    @property
    def CHA(self) -> int:
        """Returns the D&D charisma modifier."""
        return self.stats.CHA

    @property
    def SPELLCASTING(self) -> int:
        """Returns the D&D spellcasting ability modifier."""
        return self.stats.SPELLCASTING

    @property
    def AC(self) -> int:
        """Calculates Armor Class (AC) using D&D 5e rules."""
        return self.stats.AC

    @property
    def INITIATIVE(self) -> int:
        """
        Calculates the character's initiative based on dexterity and any active
        effects.
        """
        return self.stats.INITIATIVE

    def adjust_mind(self, amount: int) -> int:
        """
        Adjusts the character's Mind by a specific amount, clamped between 0 and
        MIND_MAX.
        """
        return self.stats.adjust_mind(amount)

    def get_expression_variables(self) -> list[VarInfo]:
        """Returns a dictionary of the character's modifiers."""
        return self.stats.get_expression_variables()

    def add_passive_effect(self, effect: Effect) -> bool:
        """Add a passive effect that is always active (like boss phase triggers)."""
        return self.effects_module.add_passive_effect(effect)

    def remove_passive_effect(self, effect: Effect) -> bool:
        """Remove a passive effect."""
        return self.effects_module.remove_passive_effect(effect)

    def reset_available_actions(self) -> None:
        """Resets the classes of available actions for the character."""
        return self.actions_module.reset_available_actions()

    def use_action_class(self, action_class: ActionClass) -> None:
        """Marks an action class as used for the current turn."""
        return self.actions_module.use_action_class(action_class)

    def has_action_class(self, action_class: ActionClass) -> bool:
        """Checks if the character can use a specific action class this turn."""
        return self.actions_module.has_action_class(action_class)

    def is_incapacitated(self) -> bool:
        """Check if the character is incapacitated and cannot take actions."""
        for ae in self.effects_module.active_effects:
            if isinstance(ae.effect, IncapacitatingEffect):
                if ae.effect.prevents_actions():
                    return True
        return False

    def can_take_actions(self) -> bool:
        """Check if character can take any actions this turn."""
        return not self.is_incapacitated() and self.is_alive()

    def get_available_natural_weapon_attacks(self) -> list[NaturalAttack]:
        """Returns a list of natural weapon attacks available to the character.

        Returns:
            list[NaturalAttack]: A list of natural weapon attacks

        """
        return self.actions_module.get_available_natural_weapon_attacks()

    def get_available_weapon_attacks(self) -> list[WeaponAttack]:
        """Returns a list of weapon attacks that the character can use this turn."""
        return self.actions_module.get_available_weapon_attacks()

    def get_available_attacks(self) -> list[BaseAction]:
        """Returns a list of all attacks (weapon + natural) that the character can use this turn."""
        return self.actions_module.get_available_attacks()

    def get_available_actions(self) -> list[BaseAction]:
        """Returns a list of actions that the character can use this turn."""
        return self.actions_module.get_available_actions()

    def get_available_spells(self) -> list[BaseSpell]:
        """Returns a list of spells that the character can use this turn."""
        return self.actions_module.get_available_spells()

    def turn_done(self) -> bool:
        """Checks if the character has used both a standard and bonus action this turn.

        Returns:
            bool: True if both actions are used, False otherwise

        """
        return self.actions_module.turn_done()

    def take_damage(
        self,
        amount: int,
        damage_type: DamageType,
    ) -> tuple[int, int, int]:
        """
        Applies damage to the character, factoring in resistances and vulnerabilities.

        Args:
            amount:
                The raw base damage
            damage_type:
                The type of damage being dealt

        Returns:
            tuple[int, int, int]:
                - The base damage before adjustments
                - The adjusted damage after resistances/vulnerabilities
                - The actual damage taken after applying to HP

        """
        base = amount
        adjusted = base
        if damage_type in self.resistances:
            adjusted = adjusted // 2
        elif damage_type in self.vulnerabilities:
            adjusted = adjusted * 2
        adjusted = max(adjusted, 0)

        # Apply the damage and get the actual damage taken.
        actual = abs(self.stats.adjust_hp(-adjusted))

        # Handle effects that break on damage (like sleep effects), but only
        # if actual damage was taken.
        if actual > 0:
            responses = self.on_damage_taken(
                DamageTakenEvent(
                    actor=self,
                    damage_amount=actual,
                    damage_type=damage_type,
                )
            )
            for response in responses:
                cprint(f"    {response.message}")

        return base, adjusted, actual

    def heal(self, amount: int) -> int:
        """Increases the character's hp by the given amount, up to max_hp.

        Args:
            amount: The amount of healing to apply

        Returns:
            int: The actual amount healed

        """
        return self.stats.adjust_hp(amount)

    def use_mind(self, amount: int) -> bool:
        """
        Reduces the character's mind by the given amount, if they have enough
        mind points.

        Args:
            amount:
                The amount of mind points to use

        Returns:
            bool:
                True if the mind points were successfully used, False otherwise.

        """
        if self.stats.mind >= amount:
            self.stats.adjust_mind(-amount)
            return True
        return False

    def regain_mind(self, amount: int) -> int:
        """
        Increases the character's mind by the given amount, up to max_mind.

        Args:
            amount:
                The amount of mind points to regain

        Returns:
            int:
                The actual amount of mind points regained.

        """
        return self.stats.adjust_mind(amount)

    def is_alive(self) -> bool:
        """
        Checks if the character is alive (hp > 0).

        Returns:
            bool:
                True if the character is alive, False otherwise

        """
        return self.stats.hp > 0

    def is_dead(self) -> bool:
        """
        Checks if the character is dead (hp <= 0).

        Returns:
            bool:
                True if the character is dead, False otherwise

        """
        return self.stats.hp <= 0

    def get_spell_attack_bonus(self, spell_level: int = 1) -> int:
        """Calculates the spell attack bonus for the character.

        Args:
            spell_level: The level of the spell being cast

        Returns:
            int: The spell attack bonus for the character

        """
        return self.SPELLCASTING + spell_level

    def learn_action(self, action: Any) -> None:
        """Adds an Action object to the character's known actions.

        Args:
            action (Any): The action to learn.

        """
        self.actions_module.learn_action(action)

    def unlearn_action(self, action: Any) -> None:
        """Removes an Action object from the character's known actions.

        Args:
            action (Any): The action to unlearn.

        """
        self.actions_module.unlearn_action(action)

    def learn_spell(self, spell: Any) -> None:
        """Adds a BaseSpell object to the character's known spells.

        Args:
            spell (Any): The spell to learn.

        """
        self.actions_module.learn_spell(spell)

    def unlearn_spell(self, spell: Any) -> None:
        """Removes a BaseSpell object from the character's known spells.

        Args:
            spell (Any): The spell to unlearn.

        """
        self.actions_module.unlearn_spell(spell)

    def get_occupied_hands(self) -> int:
        """Returns the number of hands currently occupied by equipped weapons and armor."""
        return self.inventory_module.get_occupied_hands()

    def get_free_hands(self) -> int:
        """Returns the number of free hands available for equipping items."""
        return self.inventory_module.get_free_hands()

    def can_equip_weapon(self, weapon: Weapon) -> bool:
        """Checks if the character can equip a specific weapon.

        Args:
            weapon (Weapon): The weapon to check.

        Returns:
            bool: True if the weapon can be equipped, False otherwise.

        """
        return self.inventory_module.can_equip_weapon(weapon)

    def add_weapon(self, weapon: Weapon) -> bool:
        """Adds a weapon to the character's equipped weapons.

        Args:
            weapon (Weapon): The weapon to equip.

        Returns:
            bool: True if the weapon was equipped successfully, False otherwise.

        """
        return self.inventory_module.add_weapon(weapon)

    def remove_weapon(self, weapon: Weapon) -> bool:
        """Removes a weapon from the character's equipped weapons.

        Args:
            weapon (Weapon): The weapon to remove.

        Returns:
            bool: True if the weapon was removed successfully, False otherwise.

        """
        return self.inventory_module.remove_weapon(weapon)

    def can_equip_armor(self, armor: Armor) -> bool:
        """Checks if the character can equip a specific armor.

        Args:
            armor (Armor): The armor to check.

        Returns:
            bool: True if the armor can be equipped, False otherwise.

        """
        return self.inventory_module.can_equip_armor(armor)

    def add_armor(self, armor: Armor) -> bool:
        """Adds an armor to the character's equipped armor.

        Args:
            armor (Armor): The armor to equip.

        Returns:
            bool: True if the armor was equipped successfully, False otherwise.

        """
        return self.inventory_module.add_armor(armor)

    def remove_armor(self, armor: Armor) -> bool:
        """Removes an armor from the character's equipped armor.

        Args:
            armor (Armor): The armor to remove.

        Returns:
            bool: True if the armor was removed successfully, False otherwise.

        """
        return self.inventory_module.remove_armor(armor)

    def turn_update(self) -> None:
        """
        Updates the duration of all active effects, and cooldowns. Removes
        expired effects. This should be called at the end of a character's turn
        or a round.
        """
        # Update all active effects.
        self.effects_module.turn_update()
        # Update action cooldowns and reset turn flags.
        self.actions_module.turn_update()

    def add_cooldown(self, action: BaseAction) -> None:
        """Adds a cooldown to an action.

        Args:
            action_name (BaseAction): The action to add a cooldown to.

        """
        self.actions_module.add_cooldown(action)

    def is_on_cooldown(self, action: BaseAction) -> bool:
        """Checks if an action is currently on cooldown.

        Args:
            action (BaseAction): The action to check.

        Returns:
            bool: True if the action is on cooldown, False otherwise.

        """
        return self.actions_module.is_on_cooldown(action)

    def initialize_uses(self, action: BaseAction) -> None:
        """Initializes the uses of an action to its maximum uses.

        Args:
            action (BaseAction): The action to initialize uses for.

        """
        self.actions_module.initialize_uses(action)

    def get_remaining_uses(self, action: BaseAction) -> int:
        """Returns the remaining uses of an action.

        Args:
            action (BaseAction): The action to check.

        Returns:
            int: The remaining uses of the action. Returns -1 for unlimited use actions.

        """
        return self.actions_module.get_remaining_uses(action)

    def decrement_uses(self, action: BaseAction) -> None:
        """Decrements the uses of an action by 1.

        Args:
            action (BaseAction): The action to decrement uses for.

        """
        self.actions_module.decrement_uses(action)

    def can_add_effect(
        self,
        source: Any,
        effect: Effect,
        variables: list[VarInfo] = [],
    ) -> bool:
        """
        Checks if an effect can be added to the character.

        Args:
            source (Any):
                The source of the effect (e.g., another character, an item).
            effect (Effect):
                The effect to check.
            variables (list[VarInfo], optional):
                Additional variables for effect calculations.

        Returns:
            bool:
                True if the effect can be added, False otherwise.

        """
        return self.effects_module.can_add_effect(source, effect, variables)

    def add_effect(
        self,
        source: Any,
        effect: Effect,
        variables: list[VarInfo] = [],
    ) -> bool:
        """
        Adds an effect to the character.

        Args:
            source (Any):
                The source of the effect (e.g., another character, an item).
            effect (Effect):
                The effect to add.
            variables (list[VarInfo], optional):
                Additional variables for effect calculations.

        Returns:
            bool:
                True if the effect was added successfully, False otherwise.

        """
        return self.effects_module.add_effect(source, effect, variables)

    def get_modifier(self, bonus_type: BonusType) -> Any:
        """
        Gets the total modifier for a specific bonus type from all active
        effects.

        Args:
            bonus_type (BonusType):
                The type of bonus to calculate.

        Returns:
            Any:
                The total modifier for the specified bonus type.

        """
        return self.effects_module.get_modifier(bonus_type)

    def on_hit(self, event: HitEvent) -> list[EventResponse]:
        """
        Handles the event when the character hits with an attack or spell,
        triggering any effects.

        Args:
            event (CombatEvent):
                The combat event representing the hit.

        Returns:
            list[EventResponse]:
                Responses from effects that were broken or triggered.

        """
        return self.effects_module.on_hit(event)

    def on_damage_taken(self, event: DamageTakenEvent) -> list[EventResponse]:
        """
        Handles the event when the character takes damage, triggering any
        effects.

        Args:
            event (DamageTakenEvent):
                The damage taken event.

        Returns:
            list[EventResponse]:
                Responses from effects that were broken or triggered.

        """
        return self.effects_module.on_damage_taken(event)

    def __hash__(self) -> int:
        """
        Hashes the character based on its name.

        Returns:
            int:
                The hash of the character's name.

        """
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        return self.name == getattr(other, "name", None)


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
        spellcasting_ability=data.get("spellcasting_ability"),
        total_hands=data.get("total_hands", 2),
        resistances={DamageType(dt) for dt in data.get("resistances", [])},
        vulnerabilities={DamageType(dt) for dt in data.get("vulnerabilities", [])},
        number_of_attacks=data.get("number_of_attacks", 1),
        passive_effects=passive_effects,
    )

    # Add default race spells.
    for spell_name in character.race.default_spells:
        spell = repo.get_spell(spell_name)
        if spell:
            character.learn_spell(spell)

    # Get spells from each class level
    for character_class, class_level in character.levels.items():
        # Get all spells up to the current class level
        spell_names = character_class.get_all_spells_up_to_level(class_level)
        # Get all actions up to the current class level
        action_names = character_class.get_all_actions_up_to_level(class_level)
        for spell_name in spell_names:
            spell = repo.get_spell(spell_name)
            if spell:
                character.learn_spell(spell)
        for action_name in action_names:
            action = repo.get_action(action_name)
            if action:
                character.learn_action(action)
            else:
                spell = repo.get_spell(action_name)
                if spell:
                    character.learn_spell(spell)

    # Replace equipped weapons with actual instances.
    for weapon_name in data.get("equipped_weapons", []):
        weapon = repo.get_weapon(weapon_name)
        if not weapon:
            raise ValueError(f"Weapon '{weapon_name}' not found in repository.")
        if not isinstance(weapon, WieldedWeapon):
            raise ValueError(f"Weapon '{weapon_name}' is not a WieldedWeapon.")
        character.inventory_module.add_weapon(weapon)

    # Replace natural weapons with actual instances.
    for weapon_name in data.get("natural_weapons", []):
        weapon = repo.get_weapon(weapon_name)
        if not weapon:
            raise ValueError(f"Natural weapon '{weapon_name}' not found in repository.")
        if not isinstance(weapon, NaturalWeapon):
            raise ValueError(f"Weapon '{weapon_name}' is not a NaturalWeapon.")
        character.inventory_module.add_weapon(weapon)

    # Replace equipped armor with actual instances.
    for armor_name in data.get("equipped_armor", []):
        armor = repo.get_armor(armor_name)
        if not armor:
            raise ValueError(f"Armor '{armor_name}' not found in repository.")
        character.inventory_module.add_armor(armor)

    # Replace actions with actual instances.
    for action_name in data.get("actions", []):
        action = repo.get_action(action_name)
        if action:
            character.learn_action(action)
        else:
            spell = repo.get_spell(action_name)
            if not spell:
                raise ValueError(
                    f"Action or spell '{action_name}' not found in repository."
                )
            character.learn_spell(spell)
    # Replace spells with actual instances.
    for spell_name in data.get("spells", []):
        spell = repo.get_spell(spell_name)
        if not spell:
            raise ValueError(f"Spell '{spell_name}' not found in repository.")
        character.learn_spell(spell)

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
