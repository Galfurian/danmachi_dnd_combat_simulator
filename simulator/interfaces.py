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
        self, actor: Character, targets: List[Character]
    ) -> Optional[Character]:
        """Choose a target for the actor's action.

        Args:
            actor (Character): The character for whom to choose a target.
            targets (List[Character]): The list of potential targets.

        Returns:
            Optional[Character]: The chosen target, or None if no target is selected.
        """
        ...

    def choose_targets(
        self, actor: Character, targets: List[Character], max_targets: int
    ) -> Optional[List[Character]]:
        """Choose multiple targets for an area spell or group buff.

        Args:
            actor (Character): The character for whom to choose targets.
            targets (List[Character]): The list of potential targets.
            max_targets (int): The maximum number of targets to choose.

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
