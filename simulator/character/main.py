from pathlib import Path
from typing import Any

from actions.attacks import NaturalAttack, WeaponAttack
from actions.base_action import BaseAction
from actions.spells import Spell
from core.constants import (
    ActionType,
    CharacterType,
    DamageType,
)
from effects.base_effect import Effect
from effects.incapacitating_effect import IncapacitatingEffect
from items.armor import Armor
from items.weapon import Weapon

from character.character_actions import CharacterActions
from character.character_class import CharacterClass
from character.character_concentration import CharacterConcentration
from character.character_display import CharacterDisplay
from character.character_effects import CharacterEffects
from character.character_inventory import CharacterInventory
from character.character_race import CharacterRace
from character.character_serialization import CharacterSerialization
from character.character_stats import CharacterStats


class Character:
    """
    Represents a character in the game, including stats, equipment, actions, effects, and all related management modules.
    Provides methods for stat calculation, action and spell management, equipment handling, effect processing, and serialization.
    """

    def __init__(
        self,
        char_type: CharacterType,
        name: str,
        race: CharacterRace,
        levels: dict[CharacterClass, int],
        stats: dict[str, int],
        spellcasting_ability: str | None = None,
        total_hands: int = 2,
        resistances: set[DamageType] = set(),
        vulnerabilities: set[DamageType] = set(),
        number_of_attacks: int = 1,
    ):
        """
        Initialize a Character instance with all core properties and modules.

        Args:
            char_type (CharacterType): The type of character (player, NPC, etc.).
            name (str): The character's name.
            race (CharacterRace): The character's race.
            levels (dict[CharacterClass, int]): The character's class levels.
            stats (dict[str, int]): The character's base stats.
            spellcasting_ability (Optional[str], optional): The spellcasting ability, if any. Defaults to None.
            total_hands (int, optional): The number of hands the character has. Defaults to 2.
            resistances (set[DamageType], optional): Damage types the character resists. Defaults to set().
            vulnerabilities (set[DamageType], optional): Damage types the character is vulnerable to. Defaults to set().
            number_of_attacks (int, optional): Number of attacks per turn. Defaults to 1.

        """
        # Determines if the character is a player or an NPC.
        self.char_type: CharacterType = char_type
        # Name of the character.
        self.name: str = name
        # The character race.
        self.race: CharacterRace = race
        # The character's class levels.
        self.levels: dict[CharacterClass, int] = levels
        # Stats.
        self.stats: dict[str, int] = stats
        # Spellcasting Ability.
        self.spellcasting_ability: str | None = spellcasting_ability
        # List of available attacks.
        self.total_hands: int = total_hands
        # Resistances and vulnerabilities to damage types.
        self.resistances: set[DamageType] = resistances
        self.vulnerabilities: set[DamageType] = vulnerabilities
        # Number of attacks.
        self.number_of_attacks: int = number_of_attacks

        # === Dynamic Properties ===

        # List of equipped weapons.
        self.equipped_weapons: list[Weapon] = list()
        # List of natural weapons, if any.
        self.natural_weapons: list[Weapon] = []
        # List of equipped armor.
        self.equipped_armor: list[Armor] = list()
        # List of actions.
        self.actions: dict[str, BaseAction] = dict()
        # List of spells
        self.spells: dict[str, Spell] = dict()

        # Manages active effects on the character.
        self.effects_module: CharacterEffects = CharacterEffects(self)

        # Initialize stats module for calculated properties
        self.stats_module = CharacterStats(self)
        # Initialize inventory module for equipment management
        self.inventory_module = CharacterInventory(self)
        # Initialize actions module for turn and action management
        self.actions_module = CharacterActions(self)
        # Initialize serialization module for save/load functionality
        self.serialization_module = CharacterSerialization(self)
        # Initialize display module for UI and formatting
        self.display_module = CharacterDisplay(self)
        # Initialize concentration module for spell concentration management
        self.concentration_module = CharacterConcentration(self)

        # Keep track of abilitiies cooldown.
        self.cooldowns: dict[str, int] = {}
        # Keep track of the uses of abilities.
        self.uses: dict[str, int] = {}
        # Maximum HP and Mind.
        self.hp: int = self.stats_module.HP_MAX
        self.mind: int = self.stats_module.MIND_MAX

    # ============================================================================
    # DELEGATED STAT PROPERTIES
    # ============================================================================
    # These properties delegate to the stats module for calculation

    @property
    def HP_MAX(self) -> int:
        """Returns the maximum HP of the character."""
        return self.stats_module.HP_MAX

    @property
    def MIND_MAX(self) -> int:
        """Returns the maximum Mind of the character."""
        return self.stats_module.MIND_MAX

    @property
    def STR(self) -> int:
        """Returns the D&D strength modifier."""
        return self.stats_module.STR

    @property
    def DEX(self) -> int:
        """Returns the D&D dexterity modifier."""
        return self.stats_module.DEX

    @property
    def CON(self) -> int:
        """Returns the D&D constitution modifier."""
        return self.stats_module.CON

    @property
    def INT(self) -> int:
        """Returns the D&D intelligence modifier."""
        return self.stats_module.INT

    @property
    def WIS(self) -> int:
        """Returns the D&D wisdom modifier."""
        return self.stats_module.WIS

    @property
    def CHA(self) -> int:
        """Returns the D&D charisma modifier."""
        return self.stats_module.CHA

    @property
    def SPELLCASTING(self) -> int:
        """Returns the D&D spellcasting ability modifier."""
        return self.stats_module.SPELLCASTING

    @property
    def AC(self) -> int:
        """Calculates Armor Class (AC) using D&D 5e rules."""
        return self.stats_module.AC

    @property
    def INITIATIVE(self) -> int:
        """Calculates the character's initiative based on dexterity and any active effects."""
        return self.stats_module.INITIATIVE

    def get_expression_variables(self) -> dict[str, int]:
        """Returns a dictionary of the character's modifiers."""
        return self.stats_module.get_expression_variables()

    @property
    def CONCENTRATION_LIMIT(self) -> int:
        """Calculate the maximum number of concentration effects this character can maintain."""
        return self.stats_module.CONCENTRATION_LIMIT

    @property
    def passive_effects(self) -> list[Effect]:
        """Get the list of passive effects from the effect manager."""
        return self.effects_module.passive_effects

    def add_passive_effect(self, effect: Effect) -> bool:
        """Add a passive effect that is always active (like boss phase triggers)."""
        return self.effects_module.add_passive_effect(effect)

    def remove_passive_effect(self, effect: Effect) -> bool:
        """Remove a passive effect."""
        return self.effects_module.remove_passive_effect(effect)

    def reset_turn_flags(self) -> None:
        """Resets the turn flags for the character."""
        return self.actions_module.reset_turn_flags()

    def use_action_type(self, action_type: ActionType) -> None:
        """Marks an action type as used for the current turn."""
        return self.actions_module.use_action_type(action_type)

    def has_action_type(self, action_type: ActionType) -> bool:
        """Checks if the character can use a specific action type this turn."""
        return self.actions_module.has_action_type(action_type)

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

    def get_available_natural_weapon_attacks(self) -> list["NaturalAttack"]:
        """Returns a list of natural weapon attacks available to the character.

        Returns:
            list[NaturalAttack]: A list of natural weapon attacks

        """
        return self.actions_module.get_available_natural_weapon_attacks()

    def get_available_weapon_attacks(self) -> list["WeaponAttack"]:
        """Returns a list of weapon attacks that the character can use this turn."""
        return self.actions_module.get_available_weapon_attacks()

    def get_available_attacks(self) -> list[BaseAction]:
        """Returns a list of all attacks (weapon + natural) that the character can use this turn."""
        return self.actions_module.get_available_attacks()

    def get_available_actions(self) -> list[BaseAction]:
        """Returns a list of actions that the character can use this turn."""
        return self.actions_module.get_available_actions()

    def get_available_spells(self) -> list[Spell]:
        """Returns a list of spells that the character can use this turn."""
        return self.actions_module.get_available_spells()

    def turn_done(self) -> bool:
        """Checks if the character has used both a standard and bonus action this turn.

        Returns:
            bool: True if both actions are used, False otherwise

        """
        return self.actions_module.turn_done()

    def check_passive_triggers(self) -> list[str]:
        """Checks all passive effects for trigger conditions and activates them.

        Returns:
            list[str]: Messages for effects that were triggered this check

        """
        return self.effects_module.check_passive_triggers()

    def take_damage(self, amount: int, damage_type: DamageType) -> tuple[int, int, int]:
        """Applies damage to the character, factoring in resistances and vulnerabilities.

        Args:
            amount: The raw base damage
            damage_type: The type of damage being dealt

        Returns:
            Tuple[int, int, int]: (base_damage, adjusted_damage, damage_taken)

        """
        base = amount
        adjusted = base
        if damage_type in self.resistances:
            adjusted = adjusted // 2
        elif damage_type in self.vulnerabilities:
            adjusted = adjusted * 2
        adjusted = max(adjusted, 0)
        actual = min(adjusted, self.hp)
        self.hp = max(self.hp - adjusted, 0)

        # Handle effects that break on damage (like sleep effects)
        if actual > 0:  # Only if damage was actually taken
            wake_up_messages = self.effects_module.handle_damage_taken(actual)
            if wake_up_messages:
                from core.utils import cprint

                for msg in wake_up_messages:
                    cprint(f"    {msg}")

        # Check for passive triggers after taking damage (e.g., OnLowHealthTrigger)
        if self.passive_effects and self.is_alive():
            activation_messages = self.check_passive_triggers()
            if activation_messages:
                from core.utils import cprint

                for msg in activation_messages:
                    cprint(f"    {msg}")

        return base, adjusted, actual

    def heal(self, amount: int) -> int:
        """Increases the character's hp by the given amount, up to max_hp.

        Args:
            amount: The amount of healing to apply

        Returns:
            int: The actual amount healed

        """
        # Compute the actual amount we can heal.
        amount = max(0, min(amount, self.HP_MAX - self.hp))
        # Ensure we don't exceed the maximum hp.
        self.hp += amount
        # Return the actual amount healed.
        return amount

    def use_mind(self, amount: int) -> bool:
        """Reduces the character's mind by the given amount, if they have enough mind points.

        Args:
            amount: The amount of mind points to use

        Returns:
            bool: True if the mind points were successfully used, False otherwise

        """
        if self.mind >= amount:
            self.mind -= amount
            return True
        return False

    def is_alive(self) -> bool:
        """Checks if the character is alive (hp > 0).

        Returns:
            bool: True if the character is alive, False otherwise

        """
        return self.hp > 0

    def get_spell_attack_bonus(self, spell_level: int = 1) -> int:
        """Calculates the spell attack bonus for the character.

        Args:
            spell_level: The level of the spell being cast

        Returns:
            int: The spell attack bonus for the character

        """
        return self.SPELLCASTING + spell_level

    def learn_action(self, action: Any):
        """Adds an Action object to the character's known actions.

        Args:
            action (Any): The action to learn.

        """
        return self.actions_module.learn_action(action)

    def unlearn_action(self, action: Any):
        """Removes an Action object from the character's known actions.

        Args:
            action (Any): The action to unlearn.

        """
        return self.actions_module.unlearn_action(action)

    def learn_spell(self, spell: Any):
        """Adds a Spell object to the character's known spells.

        Args:
            spell (Any): The spell to learn.

        """
        return self.actions_module.learn_spell(spell)

    def unlearn_spell(self, spell: Any):
        """Removes a Spell object from the character's known spells.

        Args:
            spell (Any): The spell to unlearn.

        """
        return self.actions_module.unlearn_spell(spell)

    def assign_class_and_race_spells(self):
        """
        Automatically assigns spells based on character class levels and race.
        This should be called after character creation or level changes.
        """
        from core.content import ContentRepository

        repo = ContentRepository()

        # Get spells from race (default spells and level-based)
        if self.race:
            # Add default race spells
            for spell_name in self.race.default_spells:
                spell = repo.get_spell(spell_name)
                if spell:
                    self.learn_spell(spell)

            # Add race spells based on character level
            total_level = sum(self.levels.values())
            for level_str, spell_names in self.race.available_spells.items():
                required_level = int(level_str)
                if total_level >= required_level:
                    for spell_name in spell_names:
                        spell = repo.get_spell(spell_name)
                        if spell:
                            self.learn_spell(spell)

        # Get spells from each class level
        for character_class, class_level in self.levels.items():
            # Get all spells up to the current class level
            spell_names = character_class.get_all_spells_up_to_level(class_level)
            # Get all actions up to the current class level
            action_names = character_class.get_all_actions_up_to_level(class_level)
            for spell_name in spell_names:
                spell = repo.get_spell(spell_name)
                if spell:
                    self.learn_spell(spell)
            for action_name in action_names:
                action = repo.get_action(action_name)
                if action:
                    self.learn_action(action)
                else:
                    spell = repo.get_spell(action_name)
                    if spell:
                        self.learn_spell(spell)

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

    def turn_update(self):
        """Updates the duration of all active effects, and cooldowns. Removes
        expired effects. This should be called at the end of a character's turn
        or a round.
        """
        return self.actions_module.turn_update()

    def add_cooldown(self, action: BaseAction):
        """Adds a cooldown to an action.

        Args:
            action_name (BaseAction): The action to add a cooldown to.

        """
        return self.actions_module.add_cooldown(action)

    def is_on_cooldown(self, action: BaseAction) -> bool:
        """Checks if an action is currently on cooldown.

        Args:
            action (BaseAction): The action to check.

        Returns:
            bool: True if the action is on cooldown, False otherwise.

        """
        return self.actions_module.is_on_cooldown(action)

    def initialize_uses(self, action: BaseAction):
        """Initializes the uses of an action to its maximum uses.

        Args:
            action (BaseAction): The action to initialize uses for.

        """
        return self.actions_module.initialize_uses(action)

    def get_remaining_uses(self, action: BaseAction) -> int:
        """Returns the remaining uses of an action.

        Args:
            action (BaseAction): The action to check.

        Returns:
            int: The remaining uses of the action. Returns -1 for unlimited use actions.

        """
        return self.actions_module.get_remaining_uses(action)

    def decrement_uses(self, action: BaseAction):
        """Decrements the uses of an action by 1.

        Args:
            action (BaseAction): The action to decrement uses for.

        """
        return self.actions_module.decrement_uses(action)

    def get_status_line(
        self,
        show_all_effects: bool = False,
        show_numbers: bool = False,
        show_bars: bool = False,
        show_ac: bool = True,
    ) -> str:
        """Get a formatted status line for the character with health, mana, effects, etc."""
        return self.display_module.get_status_line(
            show_all_effects, show_numbers, show_bars, show_ac
        )

    def get_detailed_effects(self) -> str:
        """Get a detailed multi-line view of all active effects."""
        return self.display_module.get_detailed_effects()

    def to_dict(self) -> dict[str, Any]:
        """Converts the character to a dictionary representation."""
        return self.serialization_module.to_dict()

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Character | None":
        """Create a Character instance from a dictionary representation."""
        return CharacterSerialization.from_dict(data)


def load_character(file_path: Path) -> Character | None:
    """
    Loads a character from a JSON file.

    Args:
        file_path (str): The path to the JSON file containing character data.

    Returns:
        Character | None: A Character instance if the file is valid, None otherwise.

    """
    from .character_serialization import load_character as load_char_impl

    return load_char_impl(file_path)


def load_characters(file_path: Path) -> dict[str, Character]:
    """Loads characters from a JSON file.

    Args:
        file_path (Path): The path to the JSON file containing character data.

    Returns:
        dict[str, Character]: A dictionary mapping character names to Character instances.

    """
    from .character_serialization import load_characters as load_chars_impl

    return load_chars_impl(file_path)
