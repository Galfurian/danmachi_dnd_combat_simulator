import json
from pathlib import Path
from typing import Any, TypeAlias, Union

from actions.attacks import NaturalAttack, WeaponAttack
from actions.base_action import BaseAction
from actions.spells import Spell
from catchery import log_error
from core.constants import ActionClass, BonusType, CharacterType, DamageType
from core.utils import VarInfo, cprint
from effects.base_effect import Effect
from effects.damage_over_time_effect import DamageOverTimeEffect
from effects.incapacitating_effect import IncapacitatingEffect
from effects.modifier_effect import ModifierEffect
from effects.trigger_effect import TriggerData, TriggerEffect
from items.armor import Armor
from items.weapon import NaturalWeapon, Weapon, WieldedWeapon

from character.character_actions import CharacterActions
from character.character_class import CharacterClass
from character.character_display import CharacterDisplay
from character.character_effects import CharacterEffects
from character.character_inventory import CharacterInventory
from character.character_race import CharacterRace
from character.character_stats import CharacterStats
from pydantic import BaseModel, Field, PrivateAttr, model_validator

ValidPassiveEffect: TypeAlias = Union[
    DamageOverTimeEffect,
    ModifierEffect,
    IncapacitatingEffect,
    TriggerEffect,
]


class Character(BaseModel):
    """
    Represents a character in the game, including stats, equipment, actions,
    effects, and all related management modules. Provides methods for stat
    calculation, action and spell management, equipment handling, effect
    processing, and serialization.
    """

    # === Static properties ===

    char_type: CharacterType = Field(
        description="The type of character (player, NPC, etc.)",
    )
    name: str = Field(
        description="The character's name",
    )
    race: CharacterRace = Field(
        description="The character's race",
    )
    levels: dict[CharacterClass, int] = Field(
        description="The character's class levels",
    )
    stats: dict[str, int] = Field(
        description="The character's base stats",
    )
    spellcasting_ability: str | None = Field(
        default=None,
        description="The spellcasting ability, if any",
    )
    total_hands: int = Field(
        default=2,
        description="The number of hands the character has",
    )
    resistances: set[DamageType] = Field(
        default_factory=set,
        description="Damage types the character resists",
    )
    vulnerabilities: set[DamageType] = Field(
        default_factory=set,
        description="Damage types the character is vulnerable to",
    )
    number_of_attacks: int = Field(
        default=1,
        description="Number of attacks per turn",
    )
    passive_effects: list[ValidPassiveEffect] = Field(
        default_factory=list,
        description="List of passive effects always active on the character",
    )

    # === Dynamic properties ===
    equipped_weapons: list[WieldedWeapon] = Field(
        default_factory=list,
        description="List of currently equipped weapons",
    )
    natural_weapons: list[NaturalWeapon] = Field(
        default_factory=list,
        description="List of natural weapons, if any",
    )
    equipped_armor: list[Armor] = Field(
        default_factory=list,
        description="List of currently equipped armor",
    )
    actions: dict[str, BaseAction] = Field(
        default_factory=dict,
        description="Dictionary of known actions",
    )
    spells: dict[str, Spell] = Field(
        default_factory=dict,
        description="Dictionary of known spells",
    )

    # === Management modules ===

    _effects_module: CharacterEffects = PrivateAttr()
    _stats_module: CharacterStats = PrivateAttr()
    _inventory_module: CharacterInventory = PrivateAttr()
    _actions_module: CharacterActions = PrivateAttr()
    _display_module: CharacterDisplay = PrivateAttr()

    @model_validator(mode="before")
    def replace_with_real(cls, data: dict[str, Any]) -> dict[str, Any]:
        """
        Replaces weapons, armor, actions, and spells with actual instances from
        the content repository during initialization.

        Args:
            data (dict[str, Any]):
                The input data to validate and possibly modify.

        Returns:
            dict[str, Any]:
                The modified data with real instances.
        """
        from core.content import ContentRepository

        # Import here to avoid circular imports.
        repo: ContentRepository = ContentRepository()

        # Replace the race with actual instance.
        data["race"] = repo.get_character_race(data["race"])

        # Replace character classes with actual instances.
        real_levels: dict[CharacterClass, int] = {}
        for class_name, level in data.get("levels", {}).items():
            character_class = repo.get_character_class(class_name)
            if character_class:
                real_levels[character_class] = level
        data["levels"] = real_levels

        # Replace equipped weapons with actual instances.
        real_weapons = []
        for weapon_name in data.get("equipped_weapons", []):
            weapon = repo.get_weapon(weapon_name)
            if not weapon:
                raise ValueError(f"Weapon '{weapon_name}' not found in repository.")
            if not isinstance(weapon, WieldedWeapon):
                raise ValueError(f"Weapon '{weapon_name}' is not a WieldedWeapon.")
            real_weapons.append(weapon)
        data["equipped_weapons"] = real_weapons

        # Replace natural weapons with actual instances.
        real_natural_weapons = []
        for weapon_name in data.get("natural_weapons", []):
            weapon = repo.get_weapon(weapon_name)
            if not weapon:
                raise ValueError(
                    f"Natural weapon '{weapon_name}' not found in repository."
                )
            if not isinstance(weapon, NaturalWeapon):
                raise ValueError(f"Weapon '{weapon_name}' is not a NaturalWeapon.")
            real_natural_weapons.append(weapon)
        data["natural_weapons"] = real_natural_weapons

        # Replace equipped armor with actual instances.
        real_armor = []
        for armor_name in data.get("equipped_armor", []):
            armor = repo.get_armor(armor_name)
            if armor:
                real_armor.append(armor)
        data["equipped_armor"] = real_armor

        # Replace actions with actual instances.
        real_actions = {}
        for action_name in data.get("actions", []):
            action = repo.get_action(action_name)
            if action:
                real_actions[action_name] = action
        data["actions"] = real_actions

        # Replace spells with actual instances.
        real_spells = {}
        for spell_name in data.get("spells", []):
            spell = repo.get_spell(spell_name)
            if spell:
                real_spells[spell_name] = spell
        data["spells"] = real_spells

        return data

    @model_validator(mode="after")
    def setup_character(self) -> "Character":
        """
        Post-initialization to set up dynamic properties and modules.
        """
        from core.content import ContentRepository

        # Import here to avoid circular imports.
        repo: ContentRepository = ContentRepository()

        self._effects_module: CharacterEffects = CharacterEffects(owner=self)
        self._stats_module = CharacterStats(owner=self)
        self._inventory_module = CharacterInventory(owner=self)
        self._actions_module = CharacterActions(owner=self)
        self._display_module = CharacterDisplay(owner=self)

        self._stats_module.adjust_hp(self.HP_MAX)
        self._stats_module.adjust_mind(self.MIND_MAX)

        # Add default race spells.
        for spell_name in self.race.default_spells:
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

        return self

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
    def hp(self) -> int:
        """Returns the current HP of the character."""
        return self._stats_module.HP_CURRENT

    @property
    def mind(self) -> int:
        """Returns the current Mind of the character."""
        return self._stats_module.MIND_CURRENT

    @property
    def HP_MAX(self) -> int:
        """Returns the maximum HP of the character."""
        return self._stats_module.HP_MAX

    @property
    def MIND_MAX(self) -> int:
        """Returns the maximum Mind of the character."""
        return self._stats_module.MIND_MAX

    @property
    def STR(self) -> int:
        """Returns the D&D strength modifier."""
        return self._stats_module.STR

    @property
    def DEX(self) -> int:
        """Returns the D&D dexterity modifier."""
        return self._stats_module.DEX

    @property
    def CON(self) -> int:
        """Returns the D&D constitution modifier."""
        return self._stats_module.CON

    @property
    def INT(self) -> int:
        """Returns the D&D intelligence modifier."""
        return self._stats_module.INT

    @property
    def WIS(self) -> int:
        """Returns the D&D wisdom modifier."""
        return self._stats_module.WIS

    @property
    def CHA(self) -> int:
        """Returns the D&D charisma modifier."""
        return self._stats_module.CHA

    @property
    def SPELLCASTING(self) -> int:
        """Returns the D&D spellcasting ability modifier."""
        return self._stats_module.SPELLCASTING

    @property
    def AC(self) -> int:
        """Calculates Armor Class (AC) using D&D 5e rules."""
        return self._stats_module.AC

    @property
    def INITIATIVE(self) -> int:
        """
        Calculates the character's initiative based on dexterity and any active
        effects.
        """
        return self._stats_module.INITIATIVE

    def adjust_mind(self, amount: int) -> int:
        """
        Adjusts the character's Mind by a specific amount, clamped between 0 and
        MIND_MAX.
        """
        return self._stats_module.adjust_mind(amount)

    def get_expression_variables(self) -> list[VarInfo]:
        """Returns a dictionary of the character's modifiers."""
        return self._stats_module.get_expression_variables()

    def add_passive_effect(self, effect: Effect) -> bool:
        """Add a passive effect that is always active (like boss phase triggers)."""
        return self._effects_module.add_passive_effect(effect)

    def remove_passive_effect(self, effect: Effect) -> bool:
        """Remove a passive effect."""
        return self._effects_module.remove_passive_effect(effect)

    def reset_available_actions(self) -> None:
        """Resets the classes of available actions for the character."""
        return self._actions_module.reset_available_actions()

    def use_action_class(self, action_class: ActionClass) -> None:
        """Marks an action class as used for the current turn."""
        return self._actions_module.use_action_class(action_class)

    def has_action_class(self, action_class: ActionClass) -> bool:
        """Checks if the character can use a specific action class this turn."""
        return self._actions_module.has_action_class(action_class)

    def is_incapacitated(self) -> bool:
        """Check if the character is incapacitated and cannot take actions."""
        for ae in self._effects_module.active_effects:
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
        return self._actions_module.get_available_natural_weapon_attacks()

    def get_available_weapon_attacks(self) -> list["WeaponAttack"]:
        """Returns a list of weapon attacks that the character can use this turn."""
        return self._actions_module.get_available_weapon_attacks()

    def get_available_attacks(self) -> list[BaseAction]:
        """Returns a list of all attacks (weapon + natural) that the character can use this turn."""
        return self._actions_module.get_available_attacks()

    def get_available_actions(self) -> list[BaseAction]:
        """Returns a list of actions that the character can use this turn."""
        return self._actions_module.get_available_actions()

    def get_available_spells(self) -> list[Spell]:
        """Returns a list of spells that the character can use this turn."""
        return self._actions_module.get_available_spells()

    def turn_done(self) -> bool:
        """Checks if the character has used both a standard and bonus action this turn.

        Returns:
            bool: True if both actions are used, False otherwise

        """
        return self._actions_module.turn_done()

    def check_passive_triggers(self) -> list[str]:
        """Checks all passive effects for trigger conditions and activates them.

        Returns:
            list[str]: Messages for effects that were triggered this check

        """
        return self._effects_module.check_passive_triggers()

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

        # Apply the damage and get the actual damage taken.
        actual = self._stats_module.adjust_hp(amount)

        # Handle effects that break on damage (like sleep effects), but only
        # if actual damage was taken.
        if actual > 0:
            wake_up_messages = self._effects_module.handle_damage_taken(actual)
            if wake_up_messages:
                for msg in wake_up_messages:
                    cprint(f"    {msg}")
        # Check for passive triggers after taking damage (e.g., OnLowHealthTrigger)
        if self.passive_effects and self.is_alive():
            activation_messages = self.check_passive_triggers()
            if activation_messages:
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
        return self._stats_module.adjust_hp(amount)

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
        if self.mind >= amount:
            self._stats_module.adjust_mind(-amount)
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
        return self._stats_module.adjust_mind(amount)

    def is_alive(self) -> bool:
        """
        Checks if the character is alive (hp > 0).

        Returns:
            bool:
                True if the character is alive, False otherwise

        """
        return self.hp > 0

    def is_dead(self) -> bool:
        """
        Checks if the character is dead (hp <= 0).

        Returns:
            bool:
                True if the character is dead, False otherwise

        """
        return self.hp <= 0

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
        self._actions_module.learn_action(action)

    def unlearn_action(self, action: Any) -> None:
        """Removes an Action object from the character's known actions.

        Args:
            action (Any): The action to unlearn.

        """
        self._actions_module.unlearn_action(action)

    def learn_spell(self, spell: Any) -> None:
        """Adds a Spell object to the character's known spells.

        Args:
            spell (Any): The spell to learn.

        """
        self._actions_module.learn_spell(spell)

    def unlearn_spell(self, spell: Any) -> None:
        """Removes a Spell object from the character's known spells.

        Args:
            spell (Any): The spell to unlearn.

        """
        self._actions_module.unlearn_spell(spell)

    def get_occupied_hands(self) -> int:
        """Returns the number of hands currently occupied by equipped weapons and armor."""
        return self._inventory_module.get_occupied_hands()

    def get_free_hands(self) -> int:
        """Returns the number of free hands available for equipping items."""
        return self._inventory_module.get_free_hands()

    def can_equip_weapon(self, weapon: Weapon) -> bool:
        """Checks if the character can equip a specific weapon.

        Args:
            weapon (Weapon): The weapon to check.

        Returns:
            bool: True if the weapon can be equipped, False otherwise.

        """
        return self._inventory_module.can_equip_weapon(weapon)

    def add_weapon(self, weapon: Weapon) -> bool:
        """Adds a weapon to the character's equipped weapons.

        Args:
            weapon (Weapon): The weapon to equip.

        Returns:
            bool: True if the weapon was equipped successfully, False otherwise.

        """
        return self._inventory_module.add_weapon(weapon)

    def remove_weapon(self, weapon: Weapon) -> bool:
        """Removes a weapon from the character's equipped weapons.

        Args:
            weapon (Weapon): The weapon to remove.

        Returns:
            bool: True if the weapon was removed successfully, False otherwise.

        """
        return self._inventory_module.remove_weapon(weapon)

    def can_equip_armor(self, armor: Armor) -> bool:
        """Checks if the character can equip a specific armor.

        Args:
            armor (Armor): The armor to check.

        Returns:
            bool: True if the armor can be equipped, False otherwise.

        """
        return self._inventory_module.can_equip_armor(armor)

    def add_armor(self, armor: Armor) -> bool:
        """Adds an armor to the character's equipped armor.

        Args:
            armor (Armor): The armor to equip.

        Returns:
            bool: True if the armor was equipped successfully, False otherwise.

        """
        return self._inventory_module.add_armor(armor)

    def remove_armor(self, armor: Armor) -> bool:
        """Removes an armor from the character's equipped armor.

        Args:
            armor (Armor): The armor to remove.

        Returns:
            bool: True if the armor was removed successfully, False otherwise.

        """
        return self._inventory_module.remove_armor(armor)

    def turn_update(self) -> None:
        """
        Updates the duration of all active effects, and cooldowns. Removes
        expired effects. This should be called at the end of a character's turn
        or a round.
        """
        # Update all active effects.
        self._effects_module.turn_update()
        # Update action cooldowns and reset turn flags.
        self._actions_module.turn_update()

    def add_cooldown(self, action: BaseAction):
        """Adds a cooldown to an action.

        Args:
            action_name (BaseAction): The action to add a cooldown to.

        """
        return self._actions_module.add_cooldown(action)

    def is_on_cooldown(self, action: BaseAction) -> bool:
        """Checks if an action is currently on cooldown.

        Args:
            action (BaseAction): The action to check.

        Returns:
            bool: True if the action is on cooldown, False otherwise.

        """
        return self._actions_module.is_on_cooldown(action)

    def initialize_uses(self, action: BaseAction):
        """Initializes the uses of an action to its maximum uses.

        Args:
            action (BaseAction): The action to initialize uses for.

        """
        return self._actions_module.initialize_uses(action)

    def get_remaining_uses(self, action: BaseAction) -> int:
        """Returns the remaining uses of an action.

        Args:
            action (BaseAction): The action to check.

        Returns:
            int: The remaining uses of the action. Returns -1 for unlimited use actions.

        """
        return self._actions_module.get_remaining_uses(action)

    def decrement_uses(self, action: BaseAction):
        """Decrements the uses of an action by 1.

        Args:
            action (BaseAction): The action to decrement uses for.

        """
        return self._actions_module.decrement_uses(action)

    def get_status_line(
        self,
        show_all_effects: bool = False,
        show_numbers: bool = False,
        show_bars: bool = False,
        show_ac: bool = True,
    ) -> str:
        """Get a formatted status line for the character with health, mana, effects, etc."""
        return self._display_module.get_status_line(
            show_all_effects, show_numbers, show_bars, show_ac
        )

    def get_detailed_effects(self) -> str:
        """Get a detailed multi-line view of all active effects."""
        return self._display_module.get_detailed_effects()

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
        return self._effects_module.can_add_effect(source, effect, variables)

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
        return self._effects_module.add_effect(source, effect, variables)

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
        return self._effects_module.get_modifier(bonus_type)

    def trigger_on_hit_effects(
        self,
        target: "Character",
    ) -> TriggerData:
        """
        Triggers any on-hit effects when this character hits a target.

        Args:
            target (Character):
                The character that was hit.

        Returns:
            TriggerData:
                Data about the triggered effects.
        """
        return self._effects_module.trigger_on_hit_effects(target)

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
            data = json.load(f)
            return Character(**data)
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
                    character = Character(**character_data)
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
