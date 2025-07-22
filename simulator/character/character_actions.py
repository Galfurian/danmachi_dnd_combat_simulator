"""
Character Action Management Module.

This module handles all action-related functionality for the Character class,
including turn state management, action availability, cooldowns, uses tracking,
and learning/unlearning actions and spells.
"""

from typing import TYPE_CHECKING, Any, List
from logging import debug

from actions.base_action import BaseAction
from actions.attacks import BaseAttack, NaturalAttack, WeaponAttack
from actions.spells import Spell
from core.constants import ActionType
from core.error_handling import log_warning

if TYPE_CHECKING:
    from character.main import Character


class CharacterActions:
    """Manages character actions, turn state, cooldowns, and action availability."""

    def __init__(self, character: "Character"):
        """Initialize the action manager with a reference to the character.

        Args:
            character: The Character instance this action manager belongs to.
        """
        self._character = character

    def reset_turn_flags(self) -> None:
        """Resets the turn flags for the character."""
        self._character.turn_flags["standard_action_used"] = False
        self._character.turn_flags["bonus_action_used"] = False

    def use_action_type(self, action_type: ActionType) -> None:
        """Marks an action type as used for the current turn."""
        if action_type == ActionType.STANDARD:
            self._character.turn_flags["standard_action_used"] = True
        elif action_type == ActionType.BONUS:
            self._character.turn_flags["bonus_action_used"] = True

    def has_action_type(self, action_type: ActionType) -> bool:
        """Checks if the character can use a specific action type this turn."""
        # Check if incapacitated first
        if self._character.is_incapacitated():
            return False

        if action_type == ActionType.STANDARD:
            return not self._character.turn_flags["standard_action_used"]
        elif action_type == ActionType.BONUS:
            return not self._character.turn_flags["bonus_action_used"]
        return True

    def get_available_natural_weapon_attacks(self) -> List["NaturalAttack"]:
        """Returns a list of natural weapon attacks available to the character.

        Returns:
            list[NaturalAttack]: A list of natural weapon attacks.
        """
        result: List[NaturalAttack] = []
        # Iterate through the natural weapons and check if they are available.
        for weapon in self._character.natural_weapons:
            for attack in weapon.attacks:
                if self.is_on_cooldown(attack):
                    continue
                if not self.has_action_type(attack.type):
                    continue
                # Only include NaturalAttack instances
                if isinstance(attack, NaturalAttack):
                    result.append(attack)
        return result

    def get_available_weapon_attacks(self) -> List["WeaponAttack"]:
        """Returns a list of weapon attacks that the character can use this turn."""
        result: List[WeaponAttack] = []
        # Iterate through the equipped weapons and check if they are available.
        for weapon in self._character.equipped_weapons:
            for attack in weapon.attacks:
                if self.is_on_cooldown(attack):
                    continue
                if not self.has_action_type(attack.type):
                    continue
                # Only include WeaponAttack instances
                if isinstance(attack, WeaponAttack):
                    result.append(attack)
        return result

    def get_available_attacks(self) -> List[BaseAction]:
        """Returns a list of all attacks (weapon + natural) that the character can use this turn."""
        result: List[BaseAction] = []
        result.extend(self.get_available_weapon_attacks())
        result.extend(self.get_available_natural_weapon_attacks())
        return result

    def get_available_actions(self) -> List[BaseAction]:
        """Returns a list of actions that the character can use this turn."""
        available_actions = []
        for action in self._character.actions.values():
            if not self.is_on_cooldown(action) and self.has_action_type(action.type):
                available_actions.append(action)
        return available_actions

    def get_available_spells(self) -> List[Spell]:
        """Returns a list of spells that the character can use this turn."""
        available_spells = []
        for spell in self._character.spells.values():
            if not self.is_on_cooldown(spell) and self.has_action_type(spell.type):
                # Check if the character has enough mind points to cast the spell.
                if self._character.mind >= (
                    spell.mind_cost[0] if spell.mind_cost else 0
                ):
                    available_spells.append(spell)
        return available_spells

    def turn_done(self) -> bool:
        """
        Checks if the character has used both a standard and bonus action this turn.
        Returns True if both actions are used, False otherwise.
        """
        available_actions = self.get_available_actions() + self.get_available_spells()
        # Check if the character has any bonus actions available.
        has_bonus_actions = any(
            action.type == ActionType.BONUS for action in available_actions
        )
        if has_bonus_actions and not self._character.turn_flags["bonus_action_used"]:
            return False
        return self._character.turn_flags["standard_action_used"]

    def add_cooldown(self, action: BaseAction, duration: int):
        """Adds a cooldown to an action.

        Args:
            action_name (BaseAction): The action to add a cooldown to.
            duration (int): The duration of the cooldown in turns.
        """
        if action.name not in self._character.cooldowns and duration > 0:
            self._character.cooldowns[action.name] = duration + 1

    def is_on_cooldown(self, action: BaseAction) -> bool:
        """Checks if an action is currently on cooldown.

        Args:
            action (BaseAction): The action to check.

        Returns:
            bool: True if the action is on cooldown, False otherwise.
        """
        return self._character.cooldowns.get(action.name, 0) > 0

    def initialize_uses(self, action: BaseAction):
        """Initializes the uses of an action to its maximum uses.

        Args:
            action (BaseAction): The action to initialize uses for.
        """
        if action.name not in self._character.uses:
            # For unlimited use actions (-1), don't track uses
            if action.maximum_uses == -1:
                self._character.uses[action.name] = -1  # Unlimited
                debug(
                    f"{self._character.name} initialized {action.name} with unlimited uses."
                )
            else:
                self._character.uses[action.name] = action.maximum_uses
                debug(
                    f"{self._character.name} initialized {action.name} with {action.maximum_uses} uses."
                )

    def get_remaining_uses(self, action: BaseAction) -> int:
        """Returns the remaining uses of an action.

        Args:
            action (BaseAction): The action to check.

        Returns:
            int: The remaining uses of the action. Returns -1 for unlimited use actions.
        """
        if action.maximum_uses == -1:
            return -1  # Unlimited uses
        return self._character.uses.get(action.name, 0)

    def decrement_uses(self, action: BaseAction):
        """Decrements the uses of an action by 1.

        Args:
            action (BaseAction): The action to decrement uses for.
        """
        # Don't decrement unlimited use actions
        if action.maximum_uses == -1:
            return

        if action.name in self._character.uses:
            if self._character.uses[action.name] > 0:
                self._character.uses[action.name] -= 1
                debug(
                    f"{self._character.name} used {action.name}. Remaining uses: {self._character.uses[action.name]}"
                )
            else:
                log_warning(
                    f"{self._character.name} has no remaining uses for {action.name}",
                    {
                        "character": self._character.name,
                        "action": action.name,
                        "remaining_uses": self._character.uses[action.name],
                    },
                )
        else:
            log_warning(
                f"{self._character.name} does not have {action.name} in their uses",
                {
                    "character": self._character.name,
                    "action": action.name,
                    "available_actions": list(self._character.uses.keys()),
                },
            )

    def turn_update(self):
        """Updates the duration of all active effects, and cooldowns. Removes
        expired effects. This should be called at the end of a character's turn
        or a round."""
        self._character.effects_module.turn_update()
        # Iterate the cooldowns and decrement them.
        for action_name in list(self._character.cooldowns.keys()):
            if self._character.cooldowns[action_name] > 0:
                self._character.cooldowns[action_name] -= 1
        # Clear expired cooldowns.
        self._character.cooldowns = {
            action_name: cd
            for action_name, cd in self._character.cooldowns.items()
            if cd > 0
        }

    def learn_action(self, action: Any):
        """Adds an Action object to the character's known actions.

        Args:
            action (Any): The action to learn.
        """
        if not action.name.lower() in self._character.actions:
            self._character.actions[action.name.lower()] = action
            debug(f"{self._character.name} learned {action.name}!")

    def unlearn_action(self, action: Any):
        """Removes an Action object from the character's known actions.

        Args:
            action (Any): The action to unlearn.
        """
        if action.name.lower() in self._character.actions:
            del self._character.actions[action.name.lower()]
            debug(f"{self._character.name} unlearned {action.name}!")

    def learn_spell(self, spell: Any):
        """Adds a Spell object to the character's known spells.

        Args:
            spell (Any): The spell to learn.
        """
        if not spell.name.lower() in self._character.spells:
            self._character.spells[spell.name.lower()] = spell
            debug(f"{self._character.name} learned {spell.name}!")

    def unlearn_spell(self, spell: Any):
        """Removes a Spell object from the character's known spells.

        Args:
            spell (Any): The spell to unlearn.
        """
        if spell.name.lower() in self._character.spells:
            del self._character.spells[spell.name.lower()]
            debug(f"{self._character.name} unlearned {spell.name}!")
