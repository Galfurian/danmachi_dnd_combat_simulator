"""
Character actions module for the simulator.

Manages the actions available to characters, including attacks, spells,
and abilities, with functionality for action selection and execution.
"""

from typing import Any

from actions.attacks.natural_attack import NaturalAttack
from actions.attacks.weapon_attack import WeaponAttack
from actions.base_action import BaseAction
from actions.spells.base_spell import BaseSpell
from catchery import log_warning
from core.constants import ActionClass


class CharacterActions:
    """
    Manages character actions, turn state, cooldowns, and action availability
    for a Character.

    Attributes:
        owner (Any):
            The Character instance this action manager belongs to.
        available_actions (dict[ActionClass, bool]):
            Tracks which action classes (standard, bonus) are available this
            turn.
        cooldowns (dict[str, int]):
            Maps action names to their remaining cooldown turns.
        uses (dict[str, int]):
            Maps action names to their remaining uses if limited.

    """

    def __init__(self, owner: Any) -> None:
        """
        Initialize the CharacterActions with the owning character.

        Args:
            owner (Any): The Character instance this action manager belongs to.

        """
        self.owner = owner
        self.available_actions = {
            ActionClass.STANDARD: True,
            ActionClass.BONUS: True,
        }
        self.cooldowns = {}
        self.uses = {}

    def reset_available_actions(self) -> None:
        """
        Reset the used action classes for the character.
        """
        self.available_actions = {
            ActionClass.STANDARD: True,
            ActionClass.BONUS: True,
        }

    def use_action_class(self, action_class: ActionClass) -> None:
        """Mark an action class as used for the current turn.

        Args:
            action_class (ActionClass): The class of action to mark as used.

        """
        if action_class is ActionClass.NONE:
            return
        if action_class in self.available_actions:
            self.available_actions[action_class] = False

    def has_action_class(self, action_class: ActionClass) -> bool:
        """Check if the character can use a specific action class this turn.

        Args:
            action_class (ActionClass): The class of action to check availability for.

        Returns:
            bool: True if the action class is available, False otherwise.

        """
        # Check if incapacitated first
        if self.owner.is_incapacitated():
            return False
        # Free and Reaction actions are always available if not incapacitated,
        # for the rest it will properly check the availability.
        return self.available_actions.get(action_class, True)

    def get_available_natural_weapon_attacks(self) -> list["NaturalAttack"]:
        """Return a list of natural weapon attacks available to the character.

        Returns:
            List[NaturalAttack]: A list of natural weapon attacks.

        """
        from items.weapon import NaturalWeapon

        result: list[NaturalAttack] = []
        # Iterate through the natural weapons and check if they are available.
        for weapon in self.owner.natural_weapons:

            assert isinstance(
                weapon, NaturalWeapon
            ), f"Expected NaturalWeapon, got {type(weapon)}"

            for attack in weapon.attacks:
                if self.is_on_cooldown(attack):
                    continue
                if not self.has_action_class(attack.action_class):
                    continue
                if not isinstance(attack, NaturalAttack):
                    continue
                result.append(attack)
        return result

    def get_available_weapon_attacks(self) -> list["WeaponAttack"]:
        """Return a list of weapon attacks that the character can use this turn.

        Returns:
            List[WeaponAttack]: A list of weapon attacks.

        """
        from items.weapon import WieldedWeapon

        result: list[WeaponAttack] = []
        # Iterate through the equipped weapons and check if they are available.
        for weapon in self.owner.equipped_weapons:

            assert isinstance(
                weapon, WieldedWeapon
            ), f"Expected WieldedWeapon, got {type(weapon)}"

            for attack in weapon.attacks:
                if self.is_on_cooldown(attack):
                    continue
                if not self.has_action_class(attack.action_class):
                    continue
                # Only include WeaponAttack instances
                if isinstance(attack, WeaponAttack):
                    result.append(attack)
        return result

    def get_available_attacks(self) -> list[BaseAction]:
        """Return a list of all attacks (weapon + natural) that the character can use this turn.

        Returns:
            List[BaseAction]: A list of all available attacks.

        """
        result: list[BaseAction] = []
        result.extend(self.get_available_weapon_attacks())
        result.extend(self.get_available_natural_weapon_attacks())
        return result

    def get_available_actions(self) -> list[BaseAction]:
        """Return a list of actions that the character can use this turn.

        Returns:
            List[BaseAction]: A list of available actions.

        """
        available_actions: list[BaseAction] = []
        for action in self.owner.actions.values():
            if self.is_on_cooldown(action):
                continue
            if not self.has_action_class(action.action_class):
                continue
            available_actions.append(action)
        return available_actions

    def get_available_spells(self) -> list[BaseSpell]:
        """Return a list of spells that the character can use this turn.

        Returns:
            List[BaseSpell]: A list of available spells.

        """
        available_spells: list[BaseSpell] = []
        for spell in self.owner.spells.values():
            if self.is_on_cooldown(spell):
                continue
            if not self.has_action_class(spell.action_class):
                continue
            if self.owner.stats.mind < (spell.mind_cost[0] if spell.mind_cost else 0):
                continue
            available_spells.append(spell)
        return available_spells

    def turn_done(self) -> bool:
        """Check if the character has used both a standard and bonus action this turn.

        Returns:
            bool: True if the character's turn is done, False if they can still act.

        """
        available_actions: list[BaseAction] = (
            self.get_available_actions() + self.get_available_spells()
        )
        # Check if there are any FREE actions available.
        has_free_actions: bool = any(
            action.action_class == ActionClass.FREE for action in available_actions
        )
        has_bonus_actions: bool = any(
            action.action_class == ActionClass.BONUS for action in available_actions
        )
        has_standard_actions: bool = any(
            action.action_class == ActionClass.STANDARD for action in available_actions
        )
        if not has_standard_actions and not has_bonus_actions:
            return True
        return False

    def add_cooldown(self, action: BaseAction) -> None:
        """Add a cooldown to an action.

        Args:
            action (BaseAction): The action to add a cooldown to.

        """
        if action.name not in self.cooldowns and action.has_cooldown():
            self.cooldowns[action.name] = action.get_cooldown()

    def is_on_cooldown(self, action: BaseAction) -> bool:
        """Check if an action is currently on cooldown.

        Args:
            action (BaseAction): The action to check.

        Returns:
            bool: True if the action is on cooldown, False otherwise.

        """
        return self.cooldowns.get(action.name, 0) > 0

    def initialize_uses(self, action: BaseAction) -> None:
        """Initialize the uses of an action to its maximum uses.

        Args:
            action (BaseAction): The action to initialize uses for.

        """
        if action.name not in self.uses:
            if action.has_limited_uses():
                self.uses[action.name] = action.get_maximum_uses()

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
        return self.uses.get(action.name, 0)

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
        if action.name in self.uses:
            if self.uses[action.name] > 0:
                self.uses[action.name] -= 1
                return True
            log_warning(
                f"{self.owner.name} has no remaining uses for {action.name}",
                {
                    "character": self.owner.name,
                    "action": action.name,
                    "remaining_uses": self.uses[action.name],
                },
            )
        else:
            log_warning(
                f"{self.owner.name} does not have {action.name} in their uses",
                {
                    "character": self.owner.name,
                    "action": action.name,
                    "available_actions": list(self.uses.keys()),
                },
            )
        return False

    def learn_action(self, action: BaseAction) -> None:
        """Add an Action object to the character's known actions.

        Args:
            action (BaseAction): The action to learn.

        """
        if action.name.lower() not in self.owner.actions:
            self.owner.actions[action.name.lower()] = action

    def unlearn_action(self, action: BaseAction) -> None:
        """Remove an Action object from the character's known actions.

        Args:
            action (BaseAction): The action to unlearn.

        """
        if action.name.lower() in self.owner.actions:
            del self.owner.actions[action.name.lower()]

    def learn_spell(self, spell: BaseSpell) -> None:
        """
        Add a BaseSpell object to the character's known spells.

        Args:
            spell (BaseSpell): The spell to learn.

        """
        if spell.name.lower() not in self.owner.spells:
            self.owner.spells[spell.name.lower()] = spell

    def unlearn_spell(self, spell: BaseSpell) -> None:
        """
        Remove a BaseSpell object from the character's known spells.

        Args:
            spell (BaseSpell): The spell to unlearn.

        """
        if spell.name.lower() in self.owner.spells:
            del self.owner.spells[spell.name.lower()]

    def turn_update(self) -> None:
        """
        Update the character's action state at the end of their turn.
        This includes decrementing cooldowns and resetting turn flags.
        """
        # Decrement cooldowns.
        for action_name in list(self.cooldowns.keys()):
            if self.cooldowns[action_name] > 0:
                self.cooldowns[action_name] -= 1
            if self.cooldowns[action_name] == 0:
                del self.cooldowns[action_name]
        # Reset available actions.
        self.reset_available_actions()
