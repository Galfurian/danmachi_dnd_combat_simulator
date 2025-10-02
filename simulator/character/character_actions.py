"""
Character actions module for the simulator.

Manages the actions available to characters, including attacks, spells,
and abilities, with functionality for action selection and execution.
"""

from typing import Any

from actions.abilities.base_ability import BaseAbility
from actions.attacks.base_attack import BaseAttack
from actions.attacks.natural_attack import NaturalAttack
from actions.attacks.weapon_attack import WeaponAttack
from actions.base_action import BaseAction
from actions.spells.base_spell import BaseSpell
from core.constants import ActionCategory, ActionClass
from core.logging import log_debug, log_warning


class CharacterActions:
    """
    Manages character actions, turn state, cooldowns, and action availability
    for a Character.

    Attributes:
        _owner (Any):
            The Character instance this action manager belongs to.
        abilities (dict[str, BaseAction]):
            Maps ability names to BaseAction objects known by the character.
        spells (dict[str, BaseSpell]):
            Maps spell names to BaseSpell objects known by the character.
        resources (dict[ActionClass, bool]):
            Tracks which action classes (standard, bonus) are available this
            turn.
        cooldowns (dict[str, int]):
            Maps action names to their remaining cooldown turns.
        uses (dict[str, int]):
            Maps action names to their remaining uses if limited.

    """

    _owner: Any
    attacks: dict[str, BaseAttack]
    abilities: dict[str, BaseAbility]
    spells: dict[str, BaseSpell]
    _resources: dict[ActionClass, bool]
    _cooldowns: dict[str, int]
    _uses: dict[str, int]

    def __init__(self, owner: Any) -> None:
        """
        Initialize the CharacterActions with the owning character.

        Args:
            owner (Any): The Character instance this action manager belongs to.

        """
        self._owner = owner
        self.attacks = {}
        self.abilities = {}
        self.spells = {}
        self._resources = {ActionClass.STANDARD: True, ActionClass.BONUS: True}
        self._cooldowns = {}
        self._uses = {}

    def reset_available_actions(self) -> None:
        """
        Reset the used action classes for the character.
        """
        self._resources = {
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
        if action_class in self._resources:
            self._resources[action_class] = False

    def has_action_class(self, action_class: ActionClass) -> bool:
        """Check if the character can use a specific action class this turn.

        Args:
            action_class (ActionClass): The class of action to check availability for.

        Returns:
            bool: True if the action class is available, False otherwise.

        """
        from character.main import Character

        assert isinstance(self._owner, Character), "Owner is not a Character."

        # Check if incapacitated first
        if self._owner.is_incapacitated():
            return False
        # Free and Reaction actions are always available if not incapacitated,
        # for the rest it will properly check the availability.
        return self._resources.get(action_class, True)

    def get_available_natural_weapon_attacks(self) -> list["NaturalAttack"]:
        """Return a list of natural weapon attacks available to the character.

        Returns:
            List[NaturalAttack]: A list of natural weapon attacks.

        """
        from character.main import Character
        from items.weapon import NaturalWeapon

        assert isinstance(self._owner, Character), "Owner is not a Character."

        result: list[NaturalAttack] = []
        # Iterate through the natural weapons and check if they are available.
        for weapon in self._owner.inventory.natural_weapons:

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
        from character.main import Character
        from items.weapon import WieldedWeapon

        assert isinstance(self._owner, Character), "Owner is not a Character."

        result: list[WeaponAttack] = []
        # Iterate through the equipped weapons and check if they are available.
        for weapon in self._owner.inventory.wielded_weapons:

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

    def get_available_attacks(
        self,
        attack_type: type = BaseAttack,
    ) -> list[BaseAction]:
        """
        Return a list of all attacks (weapon + natural) that the character can
        use this turn.

        Returns:
            List[BaseAction]:
                A list of all available attacks.

        """
        result: list[BaseAction] = []
        if issubclass(attack_type, WeaponAttack):
            result.extend(self.get_available_weapon_attacks())
        elif issubclass(attack_type, NaturalAttack):
            result.extend(self.get_available_natural_weapon_attacks())
        else:
            result.extend(self.get_available_weapon_attacks())
            result.extend(self.get_available_natural_weapon_attacks())
        return result

    def get_available_abilities(
        self,
        category: ActionCategory = ActionCategory.NONE,
    ) -> list[BaseAbility]:
        """
        Return a list of abilities that the character can use this turn.

        Params:
            category (ActionCategory):
                The category of abilities to retrieve.

        Returns:
            List[BaseAction]:
                A list of available abilities.

        """
        result: list[BaseAbility] = []
        for action in self.abilities.values():
            if self.is_on_cooldown(action):
                continue
            if not self.has_action_class(action.action_class):
                continue
            if category != ActionCategory.NONE and action.category != category:
                continue
            result.append(action)
        return result

    def get_available_spells(
        self, category: ActionCategory = ActionCategory.NONE
    ) -> list[BaseSpell]:
        """
        Return a list of spells that the character can use this turn.

        Params:
            category (ActionCategory):
                The category of spells to retrieve.

        Returns:
            List[BaseSpell]: A list of available spells.

        """
        from character.main import Character

        assert isinstance(self._owner, Character), "Owner is not a Character."

        available_spells: list[BaseSpell] = []
        for spell in self.spells.values():
            if self.is_on_cooldown(spell):
                continue
            if not self.has_action_class(spell.action_class):
                continue
            if self._owner.stats.mind < (spell.mind_cost[0] if spell.mind_cost else 0):
                continue
            if category != ActionCategory.NONE and spell.category != category:
                continue
            available_spells.append(spell)
        return available_spells

    def turn_start(self) -> None:
        """
        Initialize the character's action state at the start of their turn.
        """

    def turn_end(self) -> None:
        """
        Update the character's action state at the end of their turn.
        This includes decrementing cooldowns and resetting turn flags.
        """
        # Decrement cooldowns.
        for action_name in list(self._cooldowns.keys()):
            if self._cooldowns[action_name] > 0:
                self._cooldowns[action_name] -= 1
            if self._cooldowns[action_name] == 0:
                del self._cooldowns[action_name]
        # Reset available actions.
        self.reset_available_actions()

    def turn_done(self) -> bool:
        """Check if the character has used both a standard and bonus action this turn.

        Returns:
            bool: True if the character's turn is done, False if they can still act.

        """
        result: list[BaseAction] = (
            self.get_available_attacks()
            + self.get_available_abilities()
            + self.get_available_spells()
        )
        # Check if there are any FREE actions available.
        has_free_actions: bool = any(
            action.action_class == ActionClass.FREE for action in result
        )
        has_bonus_actions: bool = any(
            action.action_class == ActionClass.BONUS for action in result
        )
        has_standard_actions: bool = any(
            action.action_class == ActionClass.STANDARD for action in result
        )
        if not has_standard_actions and not has_bonus_actions:
            return True
        return False

    def add_cooldown(self, action: BaseAction) -> None:
        """Add a cooldown to an action.

        Args:
            action (BaseAction): The action to add a cooldown to.

        """
        if action.name not in self._cooldowns and action.has_cooldown():
            self._cooldowns[action.name] = action.get_cooldown()

    def is_on_cooldown(self, action: BaseAction) -> bool:
        """Check if an action is currently on cooldown.

        Args:
            action (BaseAction): The action to check.

        Returns:
            bool: True if the action is on cooldown, False otherwise.

        """
        return self._cooldowns.get(action.name, 0) > 0

    def initialize_uses(self, action: BaseAction) -> None:
        """
        Initialize the uses of an action to its maximum uses.

        Args:
            action (BaseAction):
                The action to initialize uses for.

        """
        if action.name not in self._uses:
            if action.has_limited_uses():
                log_debug(
                    f"Initializing uses for action {action.name} to "
                    f"{action.get_maximum_uses()}"
                )
                self._uses[action.name] = action.get_maximum_uses()

    def get_remaining_uses(self, action: BaseAction) -> int:
        """
        Return the remaining uses of an action.

        Args:
            action (BaseAction):
                The action to check.

        Returns:
            int:
                The remaining uses of the action. Returns -1 for unlimited use
                actions.

        """
        # Unlimited uses.
        if not action.has_limited_uses():
            return -1
        return self._uses.get(action.name, 0)

    def decrement_uses(self, action: BaseAction) -> bool:
        """
        Decrement the uses of an action by 1.

        Args:
            action (BaseAction):
                The action to decrement uses for.

        Returns:
            bool:
                True if the uses were decremented, False if not.

        """
        if not action.has_limited_uses():
            return True
        if action.name in self._uses:
            if self._uses[action.name] > 0:
                log_debug(
                    f"Decrementing uses for action {action.name}. "
                    f"Remaining uses: {self._uses[action.name] - 1}"
                )
                self._uses[action.name] -= 1
                return True
        return False

    def learn(self, action: BaseAction) -> None:
        """
        Add an Action object to the character's known actions.

        Args:
            action (BaseAction):
                The action to learn.

        """
        lname = action.name.lower()

        assert lname not in self.attacks, f"Action '{action.name}' is already known."
        assert lname not in self.abilities, f"Action '{action.name}' is already known."
        assert lname not in self.spells, f"Action '{action.name}' is already known."

        if isinstance(action, BaseAttack):
            log_debug(f"Learning attack: {action.name}")
            self.attacks[lname] = action
        elif isinstance(action, BaseSpell):
            log_debug(f"Learning spell: {action.name}")
            self.spells[lname] = action
        elif isinstance(action, BaseAbility):
            log_debug(f"Learning action: {action.name}")
            self.abilities[lname] = action
        else:
            log_warning(
                f"Unknown action type for learning: {type(action)}",
                {"character": self._owner.name, "action": action.name},
            )
            return

        # Initialize the uses for the action if it has limited uses.
        self.initialize_uses(action)

    def unlearn(self, action: BaseAction) -> None:
        """
        Remove an Action object from the character's known actions.

        Args:
            action (BaseAction):
                The action to unlearn.

        """
        lname = action.name.lower()
        if lname in self.attacks:
            log_debug(f"Unlearning attack: {action.name}")
            del self.attacks[lname]
        elif lname in self.spells:
            log_debug(f"Unlearning spell: {action.name}")
            del self.spells[lname]
        elif lname in self.abilities:
            log_debug(f"Unlearning ability: {action.name}")
            del self.abilities[lname]
        else:
            log_warning(
                f"{self._owner.name} does not know action '{action.name}'",
                {
                    "character": self._owner.name,
                    "action": action.name,
                    "known_attacks": list(self.attacks.keys()),
                    "known_spells": list(self.spells.keys()),
                    "known_abilities": list(self.abilities.keys()),
                },
            )
