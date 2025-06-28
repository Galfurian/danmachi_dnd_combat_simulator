from typing import List, Protocol

from prompt_toolkit import ANSI
from actions import BaseAction, Spell
from character import Character
from rich.console import Console

console = Console()


class PlayerInterface(Protocol):

    def choose_action(self, actor: Character) -> BaseAction | int | None:
        """Choose an action for the actor."""
        ...

    def choose_target(
        self, actor: Character, targets: List[Character]
    ) -> Character | int | None:
        """Choose a target for the actor's action."""
        ...

    def choose_targets(
        self, actor: Character, targets: List[Character]
    ) -> List[Character] | int | None:
        """Choose multiple targets for an area spell or group buff."""
        ...

    def choose_mind(self, actor: Character, spell: Spell) -> int:
        """Choose the MIND level to use for a spell or action."""
        ...


def to_ansi(s: str) -> ANSI:
    with console.capture() as capture:
        console.print(s, markup=True, end="")
    return ANSI(capture.get())
