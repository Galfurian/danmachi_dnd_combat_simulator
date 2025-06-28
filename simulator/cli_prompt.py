# cli_prompt.py
from typing import List
from rich.console import Console
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from actions import BaseAction, Spell
from character import Character
from colors import *

from constants import ActionType
from interfaces import PlayerInterface, to_ansi


# main console for everything else
console = Console()
# one session keeps history
session = PromptSession(erase_when_done=True)


def table_to_str(table: Table, *, colour: bool = True) -> str:
    """
    Render a Rich Table → str.

    • If `colour` is True (default) you get ANSI escape sequences.
    • If False, output is plain ASCII (good for logs or tests).
    """
    if colour:
        with console.capture() as cap:
            console.print(table)
        return cap.get()  # with ANSI codes
    else:
        tmp = Console(record=True, color_system=None)  # no colour
        tmp.print(table)
        return tmp.export_text()  # plain string


class PromptToolkitCLI(PlayerInterface):
    """
    • Shows a Rich table of abilities each time.
    • Offers autocomplete + numeric shortcuts.
    • Wipes the typed prompt line after ⏎ (erase_when_done=True).
    """

    def __init__(self) -> None:
        pass

    def choose_action(self, actor: Character) -> BaseAction | int | None:
        # Turn the action dictionary into a list of actions.
        actions = list(actor.actions.values())
        # If the actor has no actions, return None.
        if not actions:
            return None
        # Filter actions based on the actor's available action types.
        has_standard_action = actor.has_action_type(ActionType.STANDARD)
        has_bonus_action = actor.has_action_type(ActionType.BONUS)
        actions = [
            action
            for action in actions
            if (action.type == ActionType.STANDARD and has_standard_action)
            or (action.type == ActionType.BONUS and has_bonus_action)
        ]
        # Generate a table of actions (including "Cast a Spell" if present)
        tbl = self._create_action_table(actions)
        if not tbl.rows:
            return None
        # If the actor has spells, add "Cast a Spell" as an option.
        if actor.spells:
            tbl.add_row()
            tbl.add_row("0", "Cast a Spell", "", "")
        # Generate a prompt with the table and a question.
        prompt = to_ansi(
            "\n" + actor.get_status_line() + "\n" + table_to_str(tbl) + "\nAction > "
        )
        # Create a completer for the action names (including "Cast a Spell" if present)
        completer = WordCompleter([a.name for a in actions], ignore_case=True)
        # Prompt the user for input.
        answer = session.prompt(
            prompt,
            completer=completer,
            complete_while_typing=True,
        )
        # If the user didn't type anything, return None.
        if not answer:
            return None
        # If the user typed a number, return the corresponding action.
        if answer.isdigit() and 1 <= int(answer) <= len(actions):
            return actions[int(answer) - 1]
        # If the user typed "Cast a Spell", prompt for spell selection.
        if answer.isdigit() and int(answer) == 0:
            spell = self._choose_spell(actor)
            # If the user didn't select a spell, show the prompt again.
            if isinstance(spell, int) and spell == 0:
                return self.choose_action(actor)
            return spell
        # If the selection is not a number, check if it matches an action name.
        action = next((a for a in actions if a.name.lower() == answer.lower()), None)
        # If no valid action was selected, prompt again.
        if not action:
            return self.choose_action(actor)
        return action

    def choose_target(
        self, actor: Character, targets: List[Character]
    ) -> Character | int | None:
        # Get the list of targets.
        targets = sorted(targets, key=lambda t: t.name)
        # If there are no targets, return None.
        if not targets:
            return None
        # Create a table of targets.
        tbl = self._create_target_list(targets)
        tbl.add_row()
        tbl.add_row("0", "Back", "", "")
        # Generate a prompt with the table and a question.
        prompt = to_ansi(
            "\n" + actor.get_status_line() + "\n" + table_to_str(tbl) + "\nTarget > "
        )
        # Create a completer for the target names.
        completer = WordCompleter([t.name for t in targets], ignore_case=True)
        # Prompt the user for input.
        answer = session.prompt(
            prompt,
            completer=completer,
            complete_while_typing=True,
        )
        # If the user didn't type anything, return None.
        if not answer:
            return None
        # If the user typed a number, return the corresponding target.
        if answer.isdigit() and 1 <= int(answer) <= len(targets):
            return targets[int(answer) - 1]
        if int(answer) == 0:
            return 0
        # Find the target with the matching name.
        target = next((t for t in targets if t.name.lower() == answer.lower()), None)
        # If no valid target was selected, prompt again.
        if not target:
            # Otherwise, prompt again for target selection.
            return self.choose_target(actor, targets)
        return target

    def choose_targets(
        self, actor: Character, targets: List[Character]
    ) -> List[Character] | int | None:
        selected = set()
        while True:
            tbl = Table(
                title="Select Targets (toggle with number, ENTER when done)",
                pad_edge=False,
            )
            tbl.add_column("#", style="cyan", no_wrap=True)
            tbl.add_column("Name", style="bold")
            tbl.add_column("HP", justify="right")
            tbl.add_column("AC", justify="right")
            tbl.add_column("Selected", justify="center")

            for i, t in enumerate(targets, 1):
                tbl.add_row(
                    str(i),
                    t.name,
                    str(t.hp),
                    str(t.ac),
                    "[green]✓[/]" if t in selected else "",
                )
            tbl.add_row()
            tbl.add_row("0", "Done", "", "", "")

            prompt = to_ansi(
                "\n"
                + actor.get_status_line()
                + "\n"
                + table_to_str(tbl)
                + "\nSelect > "
            )
            completer = WordCompleter(
                [str(i) for i in range(len(targets) + 1)], ignore_case=True
            )
            answer = session.prompt(
                prompt, completer=completer, complete_while_typing=True
            )

            if not answer:
                continue
            if answer.isdigit():
                idx = int(answer)
                if idx == 0:
                    return list(selected) if selected else None
                elif 1 <= idx <= len(targets):
                    t = targets[idx - 1]
                    if t in selected:
                        selected.remove(t)
                    else:
                        selected.add(t)

    def choose_mind(self, actor: Character, spell: Spell) -> int:
        """Prompts the user to select the amount of MIND to spend on a spell (if upcast is allowed)."""
        choices = spell.mind_choices()
        if len(choices) == 1:
            return choices[0]
        prompt = to_ansi(
            f"\n[cyan]Choose MIND to spend for [bold]{spell.name}[/]: {choices}[/]\n> "
        )
        completer = WordCompleter([str(c) for c in choices], ignore_case=True)
        while True:
            answer = session.prompt(prompt, completer=completer)
            if answer.isdigit() and int(answer) in choices:
                return int(answer)
            console.print("[red]Invalid input. Choose a valid MIND cost.[/]")

    def _choose_spell(self, actor):
        spells = list(actor.spells.values())
        # Generate a table of spells.
        tbl = self._create_action_table(spells)
        if not tbl.rows:
            return None
        tbl.add_row()
        tbl.add_row("0", "Back", "", "")
        # Generate a prompt with the table and a question.
        prompt = to_ansi(
            "\n" + actor.get_status_line() + "\n" + table_to_str(tbl) + "\nSpell > "
        )
        # Create a completer for the spell names.
        completer = WordCompleter([s.name for s in spells], ignore_case=True)
        # Prompt the user for input.
        answer = session.prompt(
            prompt,
            completer=completer,
            complete_while_typing=True,
        )
        # If the user didn't type anything, return None.
        if not answer:
            return None
        # If the user typed a number, return the corresponding spell.
        if answer.isdigit() and 1 <= int(answer) <= len(spells):
            return spells[int(answer) - 1]
        if int(answer) == 0:
            return 0
        # Find the spell with the matching name.
        spell = next((s for s in spells if s.name.lower() == answer.lower()), None)
        # If no valid spell was selected, prompt again.
        if not spell:
            return self._choose_spell(actor)
        return spell

    def _create_target_list(self, targets):
        """
        Create a Rich table of targets for the player to choose from.
        """
        tbl = Table(title="Targets", pad_edge=False)
        tbl.add_column("#", style="cyan", no_wrap=True)
        tbl.add_column("Name", style="bold")
        tbl.add_column("HP", justify="right")
        tbl.add_column("AC", justify="right")
        for i, target in enumerate(targets, 1):
            tbl.add_row(
                str(i),
                target.name,
                str(target.hp),
                str(target.ac),
            )
        return tbl

    def _create_action_table(self, actions) -> Table:
        tbl = Table(title="Actions", pad_edge=False)
        tbl.add_column("#", style="cyan", no_wrap=True)
        tbl.add_column("Name", style="bold")
        tbl.add_column("Type", style="magenta")
        tbl.add_column("Cost", justify="right")
        for i, action in enumerate(actions, 1):
            tbl.add_row(
                str(i),
                action.name,
                action.type.name.title(),
                str(getattr(action, "cost", 0)),
            )
        return tbl
