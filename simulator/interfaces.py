from typing import List, Optional, Protocol

from actions import BaseAction, Spell
from character import Character
from rich.console import Console

console = Console()


class PlayerInterface(Protocol):

    def choose_action(
        self, actor: Character, allowed: List[BaseAction]
    ) -> Optional[BaseAction]:
        """Choose an action for the actor.

        Args:
            actor (Character): The character for whom to choose an action.
            allowed (List[BaseAction]): The list of allowed actions.

        Returns:
            Optional[BaseAction]: The chosen action, or None if no action is selected.
        """
        ...

    def choose_target(
        self,
        actor: Character,
        targets: List[Character],
        action: Optional[BaseAction] = None,
    ) -> Optional[Character]:
        """Choose a target for the actor's action.

        Args:
            actor (Character): The character for whom to choose a target.
            targets (List[Character]): The list of potential targets.
            action (Optional[BaseAction]): The action for which to choose a target, if applicable.

        Returns:
            Optional[Character]: The chosen target, or None if no target is selected.
        """
        ...

    def choose_targets(
        self,
        actor: Character,
        targets: List[Character],
        max_targets: int,
        action: Optional[BaseAction] = None,
    ) -> Optional[List[Character]]:
        """Choose multiple targets for an area spell or group buff.

        Args:
            actor (Character): The character for whom to choose targets.
            targets (List[Character]): The list of potential targets.
            max_targets (int): The maximum number of targets to choose.
            action (Optional[BaseAction]): The action for which to choose targets, if applicable.

        Returns:
            Optional[List[Character]]: The chosen targets, or None if no targets are selected.
        """
        ...

    def choose_spell(self, actor: Character, allowed: list[Spell]) -> Optional[Spell]:
        """Choose a spell for the actor.

        Args:
            actor (Character): The character for whom to choose a spell.
            allowed (list[Spell]): The list of allowed spells.

        Returns:
            Optional[Spell]: The chosen spell, or None if no spell is selected.
        """
        ...

    def choose_mind(self, actor: Character, spell: Spell) -> int:
        """Choose the MIND level for a spell.

        Args:
            actor (Character): The character for whom to choose the MIND level.
            spell (Spell): The spell for which to choose the MIND level.

        Returns:
            int: The chosen MIND level.
        """
        ...

    def generate_action_card(self, actor: Character, action: BaseAction) -> str:
        """Generates a card representation of the action.
        Args:
            actor (Character): The character performing the action.
            action (BaseAction): The action to represent.
        Returns:
            str: A string representation of the action card.
        """
        ...
