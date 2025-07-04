import json
from logging import debug, warning
from typing import Any, Tuple
from rich.console import Console

from constants import *
from actions import *
from effect_manager import *
from effect import *
from utils import *


console = Console()


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


class CharacterRace:
    def __init__(self, name: str, natural_ac: int = 0):
        self.name = name
        self.natural_ac = natural_ac

    def to_dict(self) -> dict[str, Any]:
        """Converts the CharacterRace instance to a dictionary.

        Returns:
            dict[str, Any]: The dictionary representation of the CharacterRace instance.
        """
        return {
            "name": self.name,
            "natural_ac": self.natural_ac,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "CharacterRace":
        """Creates a CharacterRace instance from a dictionary.

        Args:
            data (dict): The dictionary representation of the CharacterRace.

        Returns:
            CharacterRace: The CharacterRace instance.
        """
        return CharacterRace(
            name=data["name"],
            natural_ac=data.get("natural_ac", 0),
        )


class Character:
    def __init__(
        self,
        name: str,
        race: CharacterRace,
        levels: dict[CharacterClass, int],
        strength: int,
        dexterity: int,
        constitution: int,
        intelligence: int,
        wisdom: int,
        charisma: int,
        spellcasting_ability: Optional[str] = None,
    ):
        # Determines if the character is a player or an NPC.
        self.type: CharacterType = CharacterType.ENEMY
        # Name of the character.
        self.name: str = name
        # The character race.
        self.race: CharacterRace = race
        # The character's class levels.
        self.levels: dict[CharacterClass, int] = levels
        # Stats.
        self.stats: dict[str, int] = {
            "strength": strength,
            "dexterity": dexterity,
            "constitution": constitution,
            "intelligence": intelligence,
            "wisdom": wisdom,
            "charisma": charisma,
        }
        # Spellcasting Ability.
        self.spellcasting_ability: Optional[str] = spellcasting_ability
        # List of equipped weapons.
        self.equipped_weapons: list[Any] = []
        self.total_hands: int = 2
        self.hands_used: int = 0
        # List of equipped armor.
        self.equipped_armor: list[Any] = []
        # Manages active effects on the character.
        self.effect_manager: EffectManager = EffectManager(self)
        # List of actions.
        self.actions: dict[str, BaseAction] = {}
        # List of spells
        self.spells: dict[str, Spell] = {}
        # Turn flags to track used actions.
        self.turn_flags: dict[str, bool] = {
            "standard_action_used": False,
            "bonus_action_used": False,
        }
        # Resistances and vulnerabilities to damage types.
        self.resistances: set[DamageType] = set()
        self.vulnerabilities: set[DamageType] = set()
        # Keep track of abilitiies cooldown.
        self.cooldowns: dict[str, int] = {}
        # Maximum HP and Mind.
        self.hp: int = self.HP_MAX
        self.mind: int = self.MIND_MAX

    @property
    def HP_MAX(self) -> int:
        """Returns the maximum HP of the character."""
        hp_max: int = 0
        # Add the class levels' HP multipliers to the max HP.
        for cls, cls_level in self.levels.items():
            hp_max += max(1, (cls.hp_mult + self.CON)) * cls_level
        # Add the effect modifiers to the max HP.
        hp_max += self.effect_manager.get_modifier(BonusType.HP)
        return hp_max

    @property
    def MIND_MAX(self) -> int:
        """Returns the maximum Mind of the character."""
        mind_max: int = 0
        # Add the class levels' Mind multipliers to the max Mind.
        for cls, cls_level in self.levels.items():
            mind_max += max(0, (cls.mind_mult + self.SPELLCASTING)) * cls_level
        # Add the effect modifiers to the max Mind.
        mind_max += self.effect_manager.get_modifier(BonusType.MIND)
        return mind_max

    @property
    def STR(self):
        """Returns the DnD strength modifier."""
        return get_stat_modifier(self.stats["strength"])

    @property
    def DEX(self):
        """Returns the DnD dexterity modifier."""
        return get_stat_modifier(self.stats["dexterity"])

    @property
    def CON(self):
        """Returns the DnD constitution modifier."""
        return get_stat_modifier(self.stats["constitution"])

    @property
    def INT(self):
        """Returns the DnD intelligence modifier."""
        return get_stat_modifier(self.stats["intelligence"])

    @property
    def WIS(self):
        """Returns the DnD wisdom modifier."""
        return get_stat_modifier(self.stats["wisdom"])

    @property
    def CHA(self):
        """Returns the DnD charisma modifier."""
        return get_stat_modifier(self.stats["charisma"])

    @property
    def SPELLCASTING(self):
        """Returns the DnD spellcasting ability modifier."""
        if self.spellcasting_ability and self.spellcasting_ability in self.stats:
            return get_stat_modifier(self.stats[self.spellcasting_ability])
        return 0

    @property
    def AC(self) -> int:
        """
        Calculates Armor Class (AC) using DnD 5e rules:
        - If wearing body armor, AC = armor.base + DEX modifier (if allowed by type)
        - Shields stack with body armor or base AC
        - If no armor is worn, AC = 10 + DEX + race bonus
        """
        # Base AC is 10 + DEX modifier.
        base_ac = 10 + self.DEX

        # Add armor and shield AC.
        armor_ac = None
        shield_ac = 0
        for armor in self.equipped_armor:
            slot: ArmorSlot = getattr(armor, "armor_slot")
            if slot == ArmorSlot.TORSO:
                armor_type: ArmorType = getattr(armor, "armor_type")
                assert (
                    armor_type in ArmorType
                ), f"Invalid armor type: {armor_type} for armor {armor.name}"
                if armor_type == ArmorType.LIGHT:
                    armor_ac = armor.ac + self.DEX
                elif armor_type == ArmorType.MEDIUM:
                    armor_ac = armor.ac + min(self.DEX, 2)
                elif armor_type == ArmorType.HEAVY:
                    armor_ac = armor.ac
                else:
                    armor_ac = armor.ac
            elif slot == ArmorSlot.SHIELD:
                shield_ac += armor.ac

        # Add effect bonuses to AC.
        effect_ac = self.effect_manager.get_modifier(BonusType.AC)

        # Determine final AC.
        if armor_ac is not None:
            return armor_ac + shield_ac + effect_ac
        race_bonus = self.race.natural_ac if self.race else 0
        return base_ac + race_bonus + shield_ac + effect_ac

    @property
    def INITIATIVE(self) -> int:
        """Calculates the character's initiative based on dexterity and any active effects.

        Returns:
            int: The total initiative value.
        """
        # Base initiative is DEX modifier.
        initiative = self.DEX
        # Add any initiative bonuses from active effects.
        initiative += self.effect_manager.get_modifier(BonusType.INITIATIVE)
        return initiative

    def reset_turn_flags(self):
        """Resets the turn flags for the character."""
        self.turn_flags["standard_action_used"] = False
        self.turn_flags["bonus_action_used"] = False

    def use_action_type(self, action_type: ActionType):
        """Marks an action type as used for the current turn."""
        if action_type == ActionType.STANDARD:
            self.turn_flags["standard_action_used"] = True
        elif action_type == ActionType.BONUS:
            self.turn_flags["bonus_action_used"] = True

    def has_action_type(self, action_type: ActionType):
        """Checks if the character can use a specific action type this turn."""
        if action_type == ActionType.STANDARD:
            return not self.turn_flags["standard_action_used"]
        elif action_type == ActionType.BONUS:
            return not self.turn_flags["bonus_action_used"]
        return True

    def turn_done(self) -> bool:
        """
        Checks if the character has used both a standard and bonus action this turn.
        Returns True if both actions are used, False otherwise.
        """
        # Check if the character has any bonus actions available
        has_bonus_actions = False
        for action in list(self.actions.values()) + list(self.spells.values()):
            if action.type == ActionType.BONUS:
                has_bonus_actions = True
                break
        if has_bonus_actions:
            return (
                self.turn_flags["standard_action_used"]
                and self.turn_flags["bonus_action_used"]
            )
        else:
            return self.turn_flags["standard_action_used"]

    def take_damage(self, amount: int, damage_type: DamageType) -> Tuple[int, int, int]:
        """
        Applies damage to the character, factoring in resistances and vulnerabilities.

        Args:
            amount (int): The raw base damage.
            damage_type (DamageType): The type of damage being dealt.

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
        return base, adjusted, actual

    def heal(self, amount: int) -> int:
        """Increases the character's hp by the given amount, up to max_hp.

        Args:
            amount (int): The amount of healing to apply.

        Returns:
            int: The actual amount healed, which may be less than the requested amount if it exceeds max_hp.
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
            amount (int): The amount of mind points to use.

        Returns:
            bool: True if the mind points were successfully used, False otherwise.
        """
        if self.mind >= amount:
            self.mind -= amount
            return True
        return False

    def is_alive(self) -> bool:
        """Checks if the character is alive (hp > 0).

        Returns:
            bool: True if the character is alive, False otherwise.
        """
        return self.hp > 0

    def get_spell_attack_bonus(self, spell_level: int = 1) -> int:
        """Calculates the spell attack bonus for the character.

        Args:
            spell_level (int, optional): The level of the spell being cast. Defaults to

        Returns:
            int: The spell attack bonus for the character.
        """
        return self.SPELLCASTING + spell_level

    def learn_action(self, action: Any):
        """Adds an Action object to the character's known actions.

        Args:
            action (Any): The action to learn.
        """
        if not action.name.lower() in self.actions:
            self.actions[action.name.lower()] = action
            debug(f"{self.name} learned {action.name}!")

    def unlearn_action(self, action: Any):
        """Removes an Action object from the character's known actions.

        Args:
            action (Any): The action to unlearn.
        """
        if action.name.lower() in self.actions:
            del self.actions[action.name.lower()]
            debug(f"{self.name} unlearned {action.name}!")

    def learn_spell(self, spell: Any):
        """Adds a Spell object to the character's known spells.

        Args:
            spell (Any): The spell to learn.
        """
        if not spell.name.lower() in self.spells:
            self.spells[spell.name.lower()] = spell
            debug(f"{self.name} learned {spell.name}!")

    def unlearn_spell(self, spell: Any):
        """Removes a Spell object from the character's known spells.

        Args:
            spell (Any): The spell to unlearn.
        """
        if spell.name.lower() in self.spells:
            del self.spells[spell.name.lower()]
            debug(f"{self.name} unlearned {spell.name}!")

    def can_equip_weapon(self, weapon: Any) -> bool:
        """
        Checks if the character can equip a specific weapon.

        Args:
            weapon (Weapon): The weapon to check.

        Returns:
            bool: True if the weapon can be equipped, False otherwise.
        """
        if not hasattr(weapon, "hands_required"):
            warning(
                f"{self.name} cannot equip {weapon.name} because it is not a valid weapon."
            )
            return False
        return (self.hands_used + weapon.hands_required) <= self.total_hands

    def can_equip_armor(self, armor: Any) -> bool:
        """Checks if the character can equip a specific armor.

        Args:
            armor (Armor): The armor to check.

        Returns:
            bool: True if the armor can be equipped, False otherwise.
        """
        if not hasattr(armor, "armor_slot"):
            warning(
                f"{self.name} cannot equip {armor.name} because it is not a valid armor."
            )
            return False
        # Check if the armor slot is already occupied.
        for equipped in self.equipped_armor:
            if equipped.armor_slot == armor.armor_slot:
                warning(
                    f"{self.name} already has armor in slot {armor.armor_slot.name}. Cannot equip {armor.name}."
                )
                return False
        # If the armor slot is not occupied, we can equip it.
        return True

    def equip_weapon(self, weapon: Any) -> bool:
        """Equips a weapon to the character's weapon slots.

        Args:
            weapon (Weapon): The weapon to equip.
        """
        if not hasattr(weapon, "hands_required"):
            warning(
                f"{self.name} cannot equip {weapon.name} because it is not a valid weapon."
            )
            return False
        if self.can_equip_weapon(weapon):
            self.equipped_weapons.append(weapon)
            self.hands_used += weapon.hands_required
            return True
        warning(f"{self.name} does not have enough free hands to equip {weapon.name}.")
        return False

    def remove_weapon(self, weapon: Any) -> bool:
        """Removes a weapon from the character's equipped weapons.

        Args:
            weapon (Weapon): The weapon to remove.
        """
        if not hasattr(weapon, "hands_required"):
            warning(
                f"{self.name} cannot remove {weapon.name} because it is not a valid weapon."
            )
            return False
        if weapon in self.equipped_weapons:
            debug(f"Unequipping weapon: {weapon.name} from {self.name}")
            self.equipped_weapons.remove(weapon)
            self.hands_used -= weapon.hands_required
            return True
        warning(f"{self.name} does not have {weapon.name} equipped.")
        return False

    def add_armor(self, armor: Any) -> bool:
        """
        Adds an armor effect to the character's list of equipped armor.
        """
        if not hasattr(armor, "armor_slot"):
            warning(
                f"{self.name} cannot equip {armor.name} because it is not a valid armor."
            )
            return False
        if self.can_equip_armor(armor):
            debug(f"Equipping armor: {armor.name} for {self.name}")
            # Add the armor to the character's armor list.
            self.equipped_armor.append(armor)
            return True
        warning(
            f"{self.name} cannot equip {armor.name} because the armor slot is already occupied."
        )
        return False

    def remove_armor(self, armor: Any) -> bool:
        """
        Removes an armor effect from the character's list of equipped armor.
        """
        if not hasattr(armor, "armor_slot"):
            warning(
                f"{self.name} cannot unequip {armor.name} because it is not a valid armor."
            )
            return False
        if armor in self.equipped_armor:
            debug(f"Unequipping armor: {armor.name} from {self.name}")
            # Remove the armor from the character's armor list.
            self.equipped_armor.remove(armor)
            return True
        warning(f"{self.name} does not have {armor.name} equipped.")
        return False

    def turn_update(self):
        """Updates the duration of all active effects, and cooldowns. Removes
        expired effects. This should be called at the end of a character's turn
        or a round."""
        self.effect_manager.turn_update()
        # Iterate the cooldowns and decrement them.
        for action_name in list(self.cooldowns.keys()):
            if self.cooldowns[action_name] > 0:
                self.cooldowns[action_name] -= 1
        # Clear expired cooldowns.
        self.cooldowns = {
            action_name: cd for action_name, cd in self.cooldowns.items() if cd > 0
        }

    def add_cooldown(self, action: BaseAction, duration: int):
        """Adds a cooldown to an action.

        Args:
            action_name (BaseAction): The action to add a cooldown to.
            duration (int): The duration of the cooldown in turns.
        """
        if action.name not in self.cooldowns:
            self.cooldowns[action.name] = duration

    def is_on_cooldown(self, action: BaseAction) -> bool:
        """Checks if an action is currently on cooldown.

        Args:
            action (BaseAction): The action to check.

        Returns:
            bool: True if the action is on cooldown, False otherwise.
        """
        return self.cooldowns.get(action.name, 0) > 0

    def get_status_line(self):
        effects = (
            ", ".join(
                f"[{get_effect_color(e.effect)}]"
                + e.effect.name
                + f"[/] ({e.duration})"
                for e in self.effect_manager.active_effects
            )
            if self.effect_manager.active_effects
            else ""
        )
        hp_bar = make_bar(self.hp, self.HP_MAX, color="green")

        status = f"{get_character_type_emoji(self.type)} [bold]{self.name:<14}[/] "
        status += f"| AC: [bold yellow]{self.AC}[/] "
        status += (
            f"| HP: [green]{self.hp:>3}[/]/[bold green]{self.HP_MAX:<3}[/] {hp_bar} "
        )
        if self.MIND_MAX > 0:
            mind_bar = make_bar(self.mind, self.MIND_MAX, color="blue")
            status += f"| MIND: [blue]{self.mind:>3}[/]/[bold blue]{self.MIND_MAX:<3}[/] {mind_bar} "
        if effects:
            status += f"| Effects: {effects}"
        return status

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type.name,
            "race": self.race.name,
            "levels": {cls.name: lvl for cls, lvl in self.levels.items()},
            "stats": self.stats,
            "spellcasting_ability": self.spellcasting_ability,
            "equipped_weapons": [w.name for w in self.equipped_weapons],
            "equipped_armor": [a.name for a in self.equipped_armor],
            "actions": list(self.actions.keys()),
            "spells": list(self.spells.keys()),
        }

    @staticmethod
    def from_dict(data: dict[str, Any], registries: dict[str, Any]) -> "Character":
        cls_registry = registries["classes"]
        race_registry = registries["races"]

        # Load the race from the races registry.
        race = race_registry[data["race"]]

        # Load the levels from the class registry.
        levels: dict[CharacterClass, int] = {}
        for cls_name, cls_level in data["levels"].items():
            if cls_name not in cls_registry:
                warning(f"CharacterClass {cls_name} not found in registry.")
                continue
            levels[cls_registry[cls_name]] = cls_level

        # Create the character instance.
        char = Character(
            name=data["name"],
            race=race,
            levels=levels,
            strength=data["stats"]["strength"],
            dexterity=data["stats"]["dexterity"],
            constitution=data["stats"]["constitution"],
            intelligence=data["stats"]["intelligence"],
            wisdom=data["stats"]["wisdom"],
            charisma=data["stats"]["charisma"],
            spellcasting_ability=data.get("spellcasting_ability", None),
        )

        # Load resistances and vulnerabilities if present in the data.
        if "resistances" in data:
            for res in data["resistances"]:
                try:
                    char.resistances.add(DamageType[res.upper()])
                except KeyError:
                    warning(
                        f"Invalid damage type '{res}' in resistances for {char.name}."
                    )
        if "vulnerabilities" in data:
            for vuln in data["vulnerabilities"]:
                try:
                    char.vulnerabilities.add(DamageType[vuln.upper()])
                except KeyError:
                    warning(
                        f"Invalid damage type '{vuln}' in vulnerabilities for {char.name}."
                    )

        # Set the character as a player if specified.
        char.type = CharacterType[data.get("type", "ENEMY").upper()]

        # Load the weapons.
        for equipped_weapon_data in data.get("equipped_weapons", []):
            char.equip_weapon(BaseAction.from_dict(equipped_weapon_data))

        # Load the armor.
        for equipped_armor_data in data.get("equipped_armor", []):
            char.add_armor(Effect.from_dict(equipped_armor_data))

        # Load the actions.
        for action_data in data.get("actions", []):
            char.learn_action(BaseAction.from_dict(action_data))

        # Load the spells.
        for spell_data in data.get("spells", []):
            char.learn_spell(BaseAction.from_dict(spell_data))

        return char


def load_character_classes(file_path: str) -> dict[str, CharacterClass]:
    """
    Loads character classes from a JSON file.

    Args:
        file_path (str): The path to the JSON file containing character classes.

    Returns:
        dict[str, CharacterClass]: A dictionary mapping class names to CharacterClass instances.
    """
    classes: dict[str, CharacterClass] = {}
    with open(file_path, "r") as f:
        class_data = json.load(f)
        for entry in class_data:
            character_class = CharacterClass.from_dict(entry)
            classes[character_class.name] = character_class
    return classes


def load_character_races(file_path: str) -> dict[str, CharacterRace]:
    """Loads character races from a JSON file.

    Args:
        file_path (str): The path to the JSON file containing character races.

    Returns:
        dict[str, CharacterRace]: A dictionary mapping race names to CharacterRace instances.
    """
    races: dict[str, CharacterRace] = {}
    with open(file_path, "r") as f:
        race_data = json.load(f)
        for entry in race_data:
            character_race = CharacterRace.from_dict(entry)
            races[character_race.name] = character_race
    return races


def load_characters(file_path: str, registries: dict[str, Any]) -> dict[str, Character]:
    """
    Loads characters from a JSON file.

    Args:
        file_path (str): The path to the JSON file containing character data.
        registries (dict[str, Any]): A dictionary containing registries for classes and races.

    Returns:
        dict[str, Character]: A dictionary mapping character names to Character instances.
    """
    characters: dict[str, Character] = {}
    with open(file_path, "r") as f:
        character_data = json.load(f)
        for entry in character_data:
            character = Character.from_dict(entry, registries)
            characters[character.name] = character
    return characters


def load_player_character(
    file_path: str, registries: dict[str, Any]
) -> Character | None:
    """
    Loads the player character from a JSON file.

    Args:
        file_path (str): The path to the JSON file containing player character data.
        registries (dict[str, Any]): A dictionary containing registries for classes and races.

    Returns:
        Character: The loaded player character.
    """
    with open(file_path, "r") as f:
        player_data = json.load(f)
        player = Character.from_dict(player_data, registries)
        # Mark the character as a player character.
        player.type = CharacterType.PLAYER
        return player
