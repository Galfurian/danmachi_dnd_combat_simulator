from logging import info, debug, warning, error
from typing import List
from rich.console import Console
import random

from constants import *
from utils import *


console = Console()


class ActiveEffect:
    def __init__(self, source, effect, mind_level: int) -> None:
        self.source = source
        self.effect = effect
        self.mind_level: int = mind_level
        self.duration: int = effect.duration

    def to_dict(self):
        """Converts the ActiveEffect instance to a dictionary."""
        return {
            "source": self.source,
            "effect": self.effect.name,
            "mind_level": self.mind_level,
        }

    @staticmethod
    def from_dict(data: dict):
        """Creates an ActiveEffect instance from a dictionary."""
        return ActiveEffect(
            source=data["source"],
            effect=data["effect"],  # Assuming effect is a string name of the effect
            mind_level=data.get("mind_level", 0),
        )


class Class:
    def __init__(self, name: str, hp_mult: int, mind_mult: int):
        self.name = name
        self.hp_mult = hp_mult
        self.mind_mult = mind_mult

    def to_dict(self):
        """Converts the Class instance to a dictionary."""
        return {
            "name": self.name,
            "hp_mult": self.hp_mult,
            "mind_mult": self.mind_mult,
        }

    @staticmethod
    def from_dict(data: dict):
        """Creates a Class instance from a dictionary."""
        return Class(
            name=data["name"],
            hp_mult=data.get("hp_mult", 0),
            mind_mult=data.get("mind_mult", 0),
        )


class Character:
    def __init__(
        self,
        name,
        levels: dict[Class, int],
        strength,
        dexterity,
        constitution,
        intelligence,
        wisdom,
        charisma,
        spellcasting_ability,
    ):
        # Determines if the character is a player or an NPC.
        self.is_player = False
        # Name of the character.
        self.name = name
        # Stats.
        self.stats = {
            "strength": strength,
            "dexterity": dexterity,
            "constitution": constitution,
            "intelligence": intelligence,
            "wisdom": wisdom,
            "charisma": charisma,
        }
        # Resources.
        self.levels: dict[Class, int] = levels
        # Set Armor Class and Initiative.
        self.ac = 0
        self.initiative = random.randint(1, 20) + self.DEX
        # Spellcasting Ability.
        self.spellcasting_ability = spellcasting_ability
        # Calculate hp and mind based on class multipliers.
        self.hp_max = 0
        self.mind_max = 0
        for cls, cls_level in levels.items():
            # HP: base multiplier + modifier, minimum 1 per level
            self.hp_max += max(1, (cls.hp_mult + self.CON)) * cls_level
            # Mind: base multiplier + modifier, minimum 0 per level
            self.mind_max += max(0, (cls.mind_mult + self.SPELLCASTING)) * cls_level

        self.hp = self.hp_max
        self.mind = self.mind_max
        # List of equipped weapons.
        self.equipped_weapons: list = []
        self.total_hands = 2
        self.hands_used = 0
        # List of equipped armor.
        self.equipped_armor = list()
        # List of active effects.
        self.active_effects: List[ActiveEffect] = list()
        # List of actions.
        self.actions = {}
        # List of spells
        self.spells = {}
        # Modifiers
        self.attack_modifiers = {}
        self.damage_modifiers = {}
        # Turn flags to track used actions.
        self.turn_flags = {
            "standard_action_used": False,
            "bonus_action_used": False,
        }

        for cls_name, cls_level in levels.items():
            if not isinstance(cls_name, Class):
                error(f"Invalid class {cls_name} for character {name}.")
                continue
            if not isinstance(cls_level, int) or cls_level < 1:
                error(
                    f"Invalid level {cls_level} for class {cls_name.name} in character {name}."
                )
                continue

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
    def AC(self):
        """Calculates the character's Armor Class (AC) based on equipped defences and active effects."""
        return self.ac

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

    def take_damage(self, amount, damage_type: DamageType):
        """Reduces the character's hp by the given amount."""
        # Ensure the amount is non-negative.
        amount = max(amount, 0)
        # Apply damage reduction from armor or effects.
        # Remove the amount of damage from the character's hp.
        self.hp = max(self.hp - amount, 0)
        # Return the actual damage we removed.
        return amount

    def heal(self, amount):
        """Increases the character's hp by the given amount, up to max_hp."""
        # Compute the actual amount we can heal.
        amount = max(0, min(amount, self.hp_max - self.hp))
        # Ensure we don't exceed the maximum hp.
        self.hp += amount
        # Return the actual amount healed.
        return amount

    def use_mind(self, amount):
        """Reduces the character's mind by the given amount. Returns True if successful, False otherwise."""
        if self.mind >= amount:
            self.mind -= amount
            return True
        return False

    def is_alive(self):
        """Checks if the character's hp is above zero."""
        return self.hp > 0

    def get_spell_attack_bonus(self, spell_level=0):
        """Calculates the spell attack bonus for spells cast by this character."""
        ability = self.stats[self.spellcasting_ability]
        bonus = get_stat_modifier(ability) + (spell_level // 2)
        return bonus

    def learn_action(self, action):
        """Adds an Action object to the character's known actions."""
        self.actions[action.name.lower()] = action
        info(f"{self.name} learned {action.name}!")

    def unlearn_action(self, action):
        """Removes an Action object from the character's known actions."""
        if action.name.lower() in self.actions:
            del self.actions[action.name.lower()]
            debug(f"{self.name} unlearned {action.name}!")
        else:
            error(f"{self.name} does not know the action: {action.name}")

    def learn_spell(self, spell):
        """Adds a Spell object to the character's known spells."""
        self.spells[spell.name.lower()] = spell
        info(f"{self.name} learned {spell.name}!")

    def unlearn_spell(self, spell):
        """Removes a Spell object from the character's known spells."""
        if spell.name.lower() in self.spells:
            del self.spells[spell.name.lower()]
            debug(f"{self.name} unlearned {spell.name}!")
        else:
            error(f"{self.name} does not know the spell: {spell.name}")

    def use_action(self, action_name, target):
        """
        Executes an action against a target character.
        """
        action = self.actions.get(action_name.lower())
        if not action:
            error(f"{self.name} does not know the action: {action_name}")
            return False
        return action.execute(self, target)

    def use_spell(self, spell_name, target):
        """
        Executes a spell against a target character.
        The rank of the spell, if we are upcasting it.
        """
        spell = self.spells.get(spell_name.lower())
        if not spell:
            error(f"{self.name} does not know the spell: {spell_name}")
            return False
        return spell.execute(self, target)

    def add_effect(self, source, effect, mind_level=0):
        """
        Applies an effect to the character. Categorizes it as permanent or active.
        """
        self.active_effects.append(ActiveEffect(source, effect, mind_level))

    def remove_effect(self, effect: ActiveEffect):
        """
        Removes a specific effect from the character and reverts its changes.
        """
        debug(f"Removing effect: {effect.effect.name} from {self.name}")
        # Call the effect's remove method to revert its changes.
        effect.effect.remove(effect.source, self)
        # Remove the active effect from the list.
        self.active_effects.remove(effect)

    def has_effect(self, effect) -> bool:
        """
        Checks if the character has a specific active effect.
        Args:
            effect (Effect): The effect to check.
        Returns:
            bool: True if the effect is active, False otherwise.
        """
        for active in self.active_effects:
            if active.effect == effect:
                return True
        return False

    def can_equip_weapon(self, weapon) -> bool:
        """
        Checks if the character can equip a specific weapon.

        Args:
            weapon (Weapon): The weapon to check.

        Returns:
            bool: True if the weapon can be equipped, False otherwise.
        """
        return (self.hands_used + weapon.hands_required) <= self.total_hands

    def can_equip_armor(self, armor) -> bool:
        """Checks if the character can equip a specific armor.

        Args:
            armor (Armor): The armor to check.

        Returns:
            bool: True if the armor can be equipped, False otherwise.
        """
        # Check if the armor slot is already occupied.
        for equipped in self.equipped_armor:
            if equipped.armor_slot == armor.armor_slot:
                warning(
                    f"{self.name} already has armor in slot {armor.armor_slot.name}. Cannot equip {armor.name}."
                )
                return False
        # If the armor slot is not occupied, we can equip it.
        return True

    def equip_weapon(self, weapon) -> None:
        """Equips a weapon to the character's weapon slots.

        Args:
            weapon (Weapon): The weapon to equip.
        """
        if self.can_equip_weapon(weapon):
            self.equipped_weapons.append(weapon)
            self.hands_used += weapon.hands_required
            return True
        warning(f"{self.name} does not have enough free hands to equip {weapon.name}.")
        return False

    def remove_weapon(self, weapon) -> None:
        """Removes a weapon from the character's equipped weapons.

        Args:
            weapon (Weapon): The weapon to remove.
        """
        if weapon in self.equipped_weapons:
            debug(f"Unequipping weapon: {weapon.name} from {self.name}")
            self.equipped_weapons.remove(weapon)
            self.hands_used -= weapon.hands_required
            return True
        warning(f"{self.name} does not have {weapon.name} equipped.")
        return False

    def add_armor(self, armor) -> None:
        """
        Adds an armor effect to the character's list of equipped armor.
        """
        if self.can_equip_armor(armor):
            debug(f"Equipping armor: {armor.name} for {self.name}")
            # Add the armor to the character's armor list.
            self.equipped_armor.append(armor)
            # Apply the armor's effects to the character.
            armor.wear(self)

    def remove_armor(self, armor) -> None:
        """
        Removes an armor effect from the character's list of equipped armor.
        """
        if armor in self.equipped_armor:
            debug(f"Unequipping armor: {armor.name} from {self.name}")
            # Remove the armor from the character's armor list.
            self.equipped_armor.remove(armor)
            # Revert the armor's effects on the character.
            armor.strip(self)

    def turn_update(self):
        """
        Updates the duration of all active effects. Removes expired effects.
        This should be called at the end of a character's turn or a round.
        """
        effects_to_remove = []
        for active in self.active_effects:
            active.effect.turn_update(active.source, self, active.mind_level)
            # Decrease the duration of the effect.
            active.duration -= 1
            # If the duration is less than or equal to zero, remove the effect.
            if active.duration <= 0:
                console.print(
                    f"    :hourglass_done: [bold yellow]{active.effect.name}[/] has expired on [bold]{self.name}[/]."
                )
                effects_to_remove.append(active)
        for active in effects_to_remove:
            self.remove_effect(active)

    def get_status_line(self):
        """
        Returns a status line string for the character, including name, hp, mind, and AC.
        """
        effects = (
            ", ".join(e.effect.name for e in self.active_effects)
            if self.active_effects
            else ""
        )
        return (
            f"[bold]{self.name}[/] "
            f"HP: [green]{self.hp}[/]/[bold green]{self.hp_max}[/] "
            f"MIND: [blue]{self.mind}[/]/[bold blue]{self.mind_max}[/] "
            f"AC: [bold yellow]{self.AC}[/] "
            f"{f'Effects: {effects}' if effects else ''}"
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "is_player": self.is_player,
            "levels": {cls.name: lvl for cls, lvl in self.levels.items()},
            "stats": self.stats,
            "spellcasting_ability": self.spellcasting_ability,
            "equipped_weapons": [w.name for w in self.equipped_weapons],
            "equipped_armor": [a.name for a in self.equipped_armor],
            "actions": list(self.actions.keys()),
            "spells": list(self.spells.keys()),
        }

    @staticmethod
    def from_dict(data: dict, registries: dict) -> "Character":
        cls_registry = registries["classes"]
        weapon_registry = registries["weapons"]
        armor_registry = registries["armors"]
        action_registry = registries["actions"]
        spell_registry = registries["spells"]

        # Load the levels from the class registry.
        levels = {}
        for cls_name, cls_level in data["levels"].items():
            if cls_name not in cls_registry:
                warning(f"Class {cls_name} not found in registry.")
                continue
            levels[cls_registry[cls_name]] = cls_level

        char = Character(
            name=data["name"],
            levels=levels,
            strength=data["stats"]["strength"],
            dexterity=data["stats"]["dexterity"],
            constitution=data["stats"]["constitution"],
            intelligence=data["stats"]["intelligence"],
            wisdom=data["stats"]["wisdom"],
            charisma=data["stats"]["charisma"],
            spellcasting_ability=data.get("spellcasting_ability", None),
        )
        char.is_player = data.get("is_player", False)
        # Load the weapons.
        for equipped_weapon in data.get("equipped_weapons", []):
            if equipped_weapon in weapon_registry:
                char.equipped_weapons.append(weapon_registry[equipped_weapon])
            else:
                warning(f"Weapon {equipped_weapon} not found in registry.")
        # Load the armor.
        for equipped_armor in data.get("equipped_armor", []):
            if equipped_armor in armor_registry:
                char.add_armor(armor_registry[equipped_armor])
            else:
                warning(f"Armor {equipped_armor} not found in registry.")
        # Load the actions.
        for action_name in data.get("actions", []):
            if action_name in action_registry:
                char.learn_action(action_registry[action_name])
            else:
                warning(f"Action {action_name} not found in registry.")
        # Load the spells.
        for spell_name in data.get("spells", []):
            if spell_name in spell_registry:
                char.learn_spell(spell_registry[spell_name])
            else:
                warning(f"Spell {spell_name} not found in registry.")
        return char
