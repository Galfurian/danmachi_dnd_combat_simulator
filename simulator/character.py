from logging import info, debug, warning, error
from typing import List
import random

from constants import *
from utils import *


class ActiveEffect:
    def __init__(self, source, effect) -> None:
        self.source = source
        self.effect = effect


class Class:
    def __init__(self, name: str, hp_mult: int, mind_mult: int):
        self.name = name
        self.hp_mult = hp_mult
        self.mind_mult = mind_mult


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
        self.spellcasting_ability: str = spellcasting_ability
        # Calculate hp and mind based on class multipliers.
        self.hp_max = 0
        self.mind_max = 0
        for level in levels:
            self.hp_max += level.hp_mult * self.CON
            self.mind_max += level.mind_mult * self.SPELCASTING
        self.hp = self.hp_max
        self.mind = self.mind_max
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
    def SPELCASTING(self):
        """Returns the DnD spellcasting ability modifier."""
        if self.spellcasting_ability in self.stats:
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
        return (
            self.turn_flags["standard_action_used"]
            and self.turn_flags["bonus_action_used"]
        )

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
        debug(f"{self.name} learned {action.name}!")

    def learn_spell(self, spell):
        """Adds a Spell object to the character's known spells."""
        self.spells[spell.name.lower()] = spell
        debug(f"{self.name} learned {spell.name}!")

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

    def add_effect(self, source, effect):
        """
        Applies an effect to the character. Categorizes it as permanent or active.
        """
        self.active_effects.append(ActiveEffect(source, effect))

    def remove_effect(self, effect):
        """
        Removes a specific effect from the character and reverts its changes.
        """
        for active_effect in self.active_effects:
            if active_effect.effect == effect:
                debug(f"Removing effect: {effect.name} from {self.name}")
                # Call the effect's remove method to revert its changes.
                active_effect.effect.remove(active_effect.source, self)
                break

    def add_armor(self, armor):
        """
        Adds an armor effect to the character's list of equipped armor.
        """
        debug(f"Equipping armor: {armor.name} for {self.name}")
        # Add the armor to the character's armor list.
        self.equipped_armor.append(armor)
        # Apply the armor's effects to the character.
        armor.wear(self)

    def remove_armor(self, armor):
        """
        Removes an armor effect from the character's list of equipped armor.
        """
        if armor in self.equipped_armor:
            debug(f"Unequipping armor: {armor.name} from {self.name}")
            # Revert the armor's effects on the character.
            armor.strip(self)
            # Remove the armor from the character's armor list.
            self.equipped_armor.remove(armor)

    def turn_update(self):
        """
        Updates the duration of all active effects. Removes expired effects.
        This should be called at the end of a character's turn or a round.
        """
        effects_to_remove = []
        for active_effect in self.active_effects:
            if active_effect.effect.turn_update(active_effect.source, self):
                effects_to_remove.append(active_effect)
        for active_effect in effects_to_remove:
            self.remove_effect(active_effect)

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
