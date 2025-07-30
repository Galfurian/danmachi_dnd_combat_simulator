"""Character Action Management Module - handles action-related functionality."""

from typing import TYPE_CHECKING, Any, List
from logging import debug

from actions.base_action import BaseAction
from actions.attacks import BaseAttack, NaturalAttack, WeaponAttack
from actions.spells import Spell
from core.constants import ActionType
from catchery import *

if TYPE_CHECKING:
    from character.main import Character


class CharacterActions:
    """
    Manages character actions, turn state, cooldowns, and action availability for a Character.
    """

    def __init__(self, character: "Character") -> None:
        """Initialize the action manager.

        Args:
            character (Character): The Character instance this action manager belongs to.
        """
        self._character = character
        # Turn flags to track used actions.
        self.turn_flags: dict[str, bool] = {
            "standard_action_used": False,
            "bonus_action_used": False,
        }

    def reset_turn_flags(self) -> None:
        """Reset the turn flags for the character."""
        self.turn_flags["standard_action_used"] = False
        self.turn_flags["bonus_action_used"] = False

    def use_action_type(self, action_type: ActionType) -> None:
        """Mark an action type as used for the current turn.

        Args:
            action_type (ActionType): The type of action to mark as used.
        """
        if action_type == ActionType.STANDARD:
            self.turn_flags["standard_action_used"] = True
        elif action_type == ActionType.BONUS:
            self.turn_flags["bonus_action_used"] = True

    def has_action_type(self, action_type: ActionType) -> bool:
        """Check if the character can use a specific action type this turn.

        Args:
            action_type (ActionType): The type of action to check availability for.

        Returns:
            bool: True if the action type is available, False otherwise.
        """
        # Check if incapacitated first
        if self._character.is_incapacitated():
            return False

        if action_type == ActionType.STANDARD:
            return not self.turn_flags["standard_action_used"]
        elif action_type == ActionType.BONUS:
            return not self.turn_flags["bonus_action_used"]
        return True

    def get_available_natural_weapon_attacks(self) -> List["NaturalAttack"]:
        """Return a list of natural weapon attacks available to the character.

        Returns:
            List[NaturalAttack]: A list of natural weapon attacks.
        """
        result: List[NaturalAttack] = []
        # Iterate through the natural weapons and check if they are available.
        for weapon in self._character.natural_weapons:
            for attack in weapon.attacks:
                if self.is_on_cooldown(attack):
                    continue
                if not self.has_action_type(attack.action_type):
                    continue
                # Only include NaturalAttack instances
                if isinstance(attack, NaturalAttack):
                    result.append(attack)
        return result

    def get_available_weapon_attacks(self) -> List["WeaponAttack"]:
        """Return a list of weapon attacks that the character can use this turn.

        Returns:
            List[WeaponAttack]: A list of weapon attacks.
        """
        result: List[WeaponAttack] = []
        # Iterate through the equipped weapons and check if they are available.
        for weapon in self._character.equipped_weapons:
            for attack in weapon.attacks:
                if self.is_on_cooldown(attack):
                    continue
                if not self.has_action_type(attack.action_type):
                    continue
                # Only include WeaponAttack instances
                if isinstance(attack, WeaponAttack):
                    result.append(attack)
        return result

    def get_available_attacks(self) -> List[BaseAction]:
        """Return a list of all attacks (weapon + natural) that the character can use this turn.

        Returns:
            List[BaseAction]: A list of all available attacks.
        """
        result: List[BaseAction] = []
        result.extend(self.get_available_weapon_attacks())
        result.extend(self.get_available_natural_weapon_attacks())
        return result

    def get_available_actions(self) -> List[BaseAction]:
        """Return a list of actions that the character can use this turn.

        Returns:
            List[BaseAction]: A list of available actions.
        """
        available_actions: List[BaseAction] = []
        for action in self._character.actions.values():
            if not self.is_on_cooldown(action) and self.has_action_type(
                action.action_type
            ):
                available_actions.append(action)
        return available_actions

    def get_available_spells(self) -> List[Spell]:
        """Return a list of spells that the character can use this turn.

        Returns:
            List[Spell]: A list of available spells.
        """
        available_spells: List[Spell] = []
        for spell in self._character.spells.values():
            if not self.is_on_cooldown(spell) and self.has_action_type(
                spell.action_type
            ):
                # Check if the character has enough mind points to cast the spell.
                if self._character.mind >= (
                    spell.mind_cost[0] if spell.mind_cost else 0
                ):
                    available_spells.append(spell)
        return available_spells

    def turn_done(self) -> bool:
        """Check if the character has used both a standard and bonus action this turn.

        Returns:
            bool: True if the character's turn is done, False if they can still act.
        """
        available_actions: List[BaseAction] = (
            self.get_available_actions() + self.get_available_spells()
        )
        # Check if the character has any bonus actions available.
        has_bonus_actions: bool = any(
            action.action_type == ActionType.BONUS for action in available_actions
        )
        if has_bonus_actions and not self.turn_flags["bonus_action_used"]:
            return False
        return self.turn_flags["standard_action_used"]

    def add_cooldown(self, action: BaseAction) -> None:
        """Add a cooldown to an action.

        Args:
            action (BaseAction): The action to add a cooldown to.
        """
        if action.name not in self._character.cooldowns and action.has_cooldown():
            self._character.cooldowns[action.name] = action.get_cooldown()

    def is_on_cooldown(self, action: BaseAction) -> bool:
        """Check if an action is currently on cooldown.

        Args:
            action (BaseAction): The action to check.

        Returns:
            bool: True if the action is on cooldown, False otherwise.
        """
        return self._character.cooldowns.get(action.name, 0) > 0

    def initialize_uses(self, action: BaseAction) -> None:
        """Initialize the uses of an action to its maximum uses.

        Args:
            action (BaseAction): The action to initialize uses for.
        """
        if action.name not in self._character.uses:
            if action.has_limited_uses():
                self._character.uses[action.name] = action.get_maximum_uses()

    def get_remaining_uses(self, action: BaseAction) -> int:
        """Return the remaining uses of an action.

        Args:
            action (BaseAction): The action to check.

        Returns:
            int: The remaining uses of the action. Returns -1 for unlimited use actions.
        """
        # Unlimited uses.
        if not action.has_limited_uses():
            return -1
        return self._character.uses.get(action.name, 0)

    def decrement_uses(self, action: BaseAction) -> bool:
        """Decrement the uses of an action by 1.

        Args:
            action (BaseAction): The action to decrement uses for.

        Returns:
            bool: True if the uses were decremented, False if not.
        """
        # Don't decrement unlimited use actions.
        if not action.has_limited_uses():
            return True
        if action.name in self._character.uses:
            if self._character.uses[action.name] > 0:
                self._character.uses[action.name] -= 1
                return True
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
        return False

    def turn_update(self) -> None:
        """Update the duration of all active effects and cooldowns."""
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

    def learn_action(self, action: BaseAction) -> None:
        """Add an Action object to the character's known actions.

        Args:
            action (BaseAction): The action to learn.
        """
        if not action.name.lower() in self._character.actions:
            self._character.actions[action.name.lower()] = action
            debug(f"{self._character.name} learned {action.name}!")

    def unlearn_action(self, action: BaseAction) -> None:
        """Remove an Action object from the character's known actions.

        Args:
            action (BaseAction): The action to unlearn.
        """
        if action.name.lower() in self._character.actions:
            del self._character.actions[action.name.lower()]
            debug(f"{self._character.name} unlearned {action.name}!")

    def learn_spell(self, spell: Spell) -> None:
        """
        Add a Spell object to the character's known spells.

        Args:
            spell (Spell): The spell to learn.
        """
        if not spell.name.lower() in self._character.spells:
            self._character.spells[spell.name.lower()] = spell
            debug(f"{self._character.name} learned {spell.name}!")

    def unlearn_spell(self, spell: Spell) -> None:
        """
        Remove a Spell object from the character's known spells.

        Args:
            spell (Spell): The spell to unlearn.
        """
        if spell.name.lower() in self._character.spells:
            del self._character.spells[spell.name.lower()]
            debug(f"{self._character.name} unlearned {spell.name}!")
