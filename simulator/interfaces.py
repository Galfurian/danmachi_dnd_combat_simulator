from enum import Enum
from typing import List, Optional, Protocol

from actions.base_action import BaseAction
from actions.spell_action import Spell
from character import Character
from rich.console import Console

console = Console()


class MenuOption(object):

    def __init__(self, name: str) -> None:
        self.name = name


class SubmenuOption(MenuOption):

    def __init__(self, name: str) -> None:
        super().__init__(name)


class ActionOption(MenuOption):

    def __init__(self, action: BaseAction) -> None:
        super().__init__(action.name)
        self.action = action


class TargetOption(MenuOption):

    def __init__(self, target: Character) -> None:
        super().__init__(target.name)
        self.target = target


class SpellOption(MenuOption):

    def __init__(self, spell: Spell) -> None:
        super().__init__(spell.name)
        self.spell = spell


class MindLevelOption(MenuOption):

    def __init__(self, level: int) -> None:
        super().__init__(f"{level}")
        self.level = level


class PlayerInterface(Protocol):

    def choose_action(
        self, actions: List[MenuOption]
    ) -> Optional[MenuOption | ActionOption]:
        """Choose an action.

        Args:
            actions (List[ActionOption]): The list of available actions.

        Returns:
            Optional[ActionOption]: The chosen action, or None if no action is selected.
        """
        ...

    def choose_target(
        self, targets: List[MenuOption]
    ) -> Optional[MenuOption | TargetOption]:
        """Choose a target.

        Args:
            targets (List[TargetOption]): The list of potential targets.

        Returns:
            Optional[TargetOption]: The chosen target, or None if no target is selected.
        """
        ...

    def choose_targets(
        self, targets: List[MenuOption], max_targets: int
    ) -> Optional[MenuOption | List[TargetOption]]:
        """Choose multiple targets for an area spell or group buff.

        Args:
            targets (List[TargetOption]): The list of potential targets.
            max_targets (int): The maximum number of targets to choose.

        Returns:
            Optional[List[TargetOption]]: The chosen targets, or None if no targets are selected.
        """
        ...

    def choose_spell(
        self, spells: list[MenuOption]
    ) -> Optional[MenuOption | SpellOption]:
        """Choose a spell.

        Args:
            spells (list[SpellOption]): The list of available spells.

        Returns:
            Optional[SpellOption]: The chosen spell, or None if no spell is selected.
        """
        ...

    def choose_mind(
        self, mind_levels: list[MenuOption]
    ) -> Optional[MenuOption | MindLevelOption]:
        """Choose the MIND level for a spell.

        Args:
            mind_levels (list[MindLevelOption]): The list of available MIND levels.

        Returns:
            int: The chosen MIND level.
        """
        ...
