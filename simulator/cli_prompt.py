# cli_prompt.py
from typing import Any, List, Optional
from rich.console import Console
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from actions import BaseAction, Spell, SpellAttack, SpellBuff, SpellDebuff, SpellHeal
from character import Character
from prompt_toolkit import ANSI
from effect import Buff

from constants import (
    ActionCategory,
    ActionType,
    get_action_category_color,
    get_action_type_color,
)
from interfaces import PlayerInterface
from utils import evaluate_expression, substitute_variables


# main console for everything else
console = Console()
# one session keeps history
session = PromptSession(erase_when_done=True)


def to_ansi(s: str) -> str:
    with console.capture() as capture:
        console.print(s, markup=True, end="")
    return capture.get()


def table_to_str(table: Table, *, colour: bool = True) -> str:
    """
    Render a Rich Table → str.

    - If `colour` is True (default) you get ANSI escape sequences.
    - If False, output is plain ASCII (good for logs or tests).
    """
    if colour:
        with console.capture() as cap:
            console.print(table)
        return cap.get()  # with ANSI codes
    else:
        tmp = Console(record=True, color_system=None)  # no colour
        tmp.print(table)
        return tmp.export_text()  # plain string


def show_prompt(
    message: str,
    completer: Optional[WordCompleter] = None,
    complete_while_typing: bool = True,
) -> str:
    """
    Show a prompt with the given message and return the user's input.
    """
    return session.prompt(
        ANSI(message),
        completer=completer,
        complete_while_typing=complete_while_typing,
    )


class PromptToolkitCLI(PlayerInterface):
    """
    - Shows a Rich table of abilities each time.
    - Offers autocomplete + numeric shortcuts.
    - Wipes the typed prompt line after ⏎ (erase_when_done=True).
    """

    def __init__(self) -> None:
        pass

    def choose_action(
        self, actor: Character, allowed: List[BaseAction]
    ) -> Optional[BaseAction]:
        # Filter actions based on the actor's available action types.
        has_standard_action = actor.has_action_type(ActionType.STANDARD)
        has_bonus_action = actor.has_action_type(ActionType.BONUS)
        actions = [
            action
            for action in allowed
            if (action.type == ActionType.STANDARD and has_standard_action)
            or (action.type == ActionType.BONUS and has_bonus_action)
        ]
        if not actions:
            return None
        # Generate a table of actions (including "Cast a Spell" if present)
        tbl = self._create_action_table(actions)
        if not tbl.rows:
            return None
        # If the actor has spells, add "Cast a Spell" as an option.
        if actor.spells:
            tbl.add_row()
            tbl.add_row("0", "Cast a Spell", "", "")
        # Generate a prompt with the table and a question.
        prompt = "\n" + table_to_str(tbl) + "\nAction > "
        # Create a completer for the action names (including "Cast a Spell" if present)
        completer = WordCompleter([a.name for a in actions], ignore_case=True)
        while True:
            # Prompt the user for input.
            answer = show_prompt(prompt, completer, True)
            # If the user didn't type anything, return None.
            if not answer:
                continue
            # If the user typed a number, return the corresponding action.
            if answer.isdigit() and 1 <= int(answer) <= len(actions):
                return actions[int(answer) - 1]
            # If the user typed "Cast a Spell", prompt for spell selection.
            if answer.isdigit() and int(answer) == 0:
                spell: Optional[Spell] = self.choose_spell(
                    actor, list(actor.spells.values())
                )
                # If the user didn't select a spell, show the prompt again.
                if not spell:
                    continue
                return spell
            # If the selection is not a number, check if it matches an action name.
            action = next(
                (a for a in actions if a.name.lower() == answer.lower()), None
            )
            # If no valid action was selected, prompt again.
            if isinstance(action, BaseAction):
                return action

    def choose_target(
        self, actor: Character, targets: List[Character]
    ) -> Optional[Character]:
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
        prompt = "\n" + table_to_str(tbl) + "\nTarget > "
        # Create a completer for the target names.
        completer = WordCompleter([t.name for t in targets], ignore_case=True)
        while True:
            # Prompt the user for input.
            answer = show_prompt(prompt, completer, True)
            # If the user didn't type anything, return None.
            if not answer:
                continue
            # If the user typed a number, return the corresponding target.
            if answer.isdigit() and 1 <= int(answer) <= len(targets):
                return targets[int(answer) - 1]
            if int(answer) == 0:
                return None
            # Find the target with the matching name.
            target = next(
                (t for t in targets if t.name.lower() == answer.lower()), None
            )
            # If a valid target was found, return it.
            if isinstance(target, Character):
                return target

    def choose_targets(
        self,
        actor: Character,
        targets: List[Character],
        max_targets: int,
    ) -> Optional[List[Character]]:
        assert (
            max_targets and max_targets > 1
        ), "max_targets must be greater than 1 for multiple target selection"
        completer = WordCompleter(
            [str(i) for i in range(len(targets) + 1)], ignore_case=True
        )
        selected: set[Character] = set()
        while True:
            tbl = Table(pad_edge=False)
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
                    str(t.AC),
                    "[green]✓[/]" if t in selected else "",
                )
            tbl.add_row("0", "Done", "", "", "")
            # Prepare the prompt with the table.
            prompt = "\n"
            prompt += f"Select up to {max_targets} targets\n"
            prompt += table_to_str(tbl) + "\nSelect > "
            # Prompt the user for input.
            answer = show_prompt(prompt, completer, True)
            # If the user didn't type anything, continue the loop.
            if not answer:
                continue
            # If the user did not type a number, continue the loop.
            if not answer.isdigit():
                continue
            # Transform the answer into an integer index.
            idx = int(answer)
            # If the user typed 0, return the selected targets or None if none were selected.
            if idx == 0:
                return list(selected) if selected else None
            if 1 <= idx <= len(targets):
                # Get the target at the index.
                target = targets[idx - 1]
                # Check if the target is already selected, in that case remove it.
                if target in selected:
                    selected.remove(target)
                    continue
                # If the target is not selected, add it to the selection.
                if len(selected) >= max_targets:
                    console.print(
                        f"[yellow]You can only select up to {max_targets} target(s).[/]"
                    )
                    continue
                # Select the target.
                selected.add(target)

    def choose_mind(self, actor: Character, spell: Spell) -> int:
        """Prompts the user to select the amount of MIND to spend on a spell (if upcast is allowed)."""
        choices = spell.mind_choices()
        if len(choices) == 1:
            return choices[0]
        prompt = to_ansi(f"\n[bold]Upcasting [cyan]{spell.name}[/] is allowed[/]:\n")
        for mind_level in choices:
            max_targets = (
                ""
                if not spell.multi_target_expr
                else f", Targets: {evaluate_expression(
                spell.multi_target_expr, actor, mind_level
            )}"
            )
            if isinstance(spell, SpellHeal):
                heal_roll = substitute_variables(spell.heal_roll, actor, mind_level)
                prompt += f"    {mind_level} → Heal: {heal_roll}"
                prompt += max_targets + "\n"
            elif isinstance(spell, SpellAttack):
                attack_roll = substitute_variables(spell.damage_roll, actor, mind_level)
                prompt += f"    {mind_level} → Attack: {attack_roll}"
                prompt += max_targets + "\n"
            elif isinstance(spell, SpellBuff) and isinstance(spell.effect, Buff):
                for modifier in spell.effect.modifiers.values():
                    prompt += f"    {mind_level} → Buff: {substitute_variables(modifier, actor, mind_level)}"
                    prompt += max_targets + "\n"
            elif isinstance(spell, SpellDebuff) and isinstance(spell.effect, Buff):
                for modifier in spell.effect.modifiers.values():
                    prompt += f"    {mind_level} → Debuff: {substitute_variables(modifier, actor, mind_level)}"
                    prompt += max_targets + "\n"
        prompt += "    0 → Back\nMind > "

        completer = WordCompleter([str(c) for c in choices], ignore_case=True)
        while True:
            answer = show_prompt(prompt, completer, True)
            if answer.isdigit():
                if int(answer) in choices:
                    return int(answer)
                if int(answer) == 0:
                    return -1

    def choose_spell(self, actor: Character, allowed: list[Spell]) -> Optional[Spell]:
        # Get the, list of spells the actor can cast.
        has_standard_action = actor.has_action_type(ActionType.STANDARD)
        has_bonus_action = actor.has_action_type(ActionType.BONUS)
        spells: list[Spell] = [
            spell
            for spell in allowed
            if (spell.type == ActionType.STANDARD and has_standard_action)
            or (spell.type == ActionType.BONUS and has_bonus_action)
        ]
        # Generate a table of spells.
        tbl = self._create_spell_table(spells)
        if not tbl.rows:
            return None
        tbl.add_row()
        tbl.add_row("0", "Exit", "", "")
        # Generate a prompt with the table and a question.
        prompt = "\n" + table_to_str(tbl) + "\nSpell > "
        # Create a completer for the spell names.
        completer = WordCompleter([s.name for s in spells], ignore_case=True)
        while True:
            # Prompt the user for input.
            answer = show_prompt(prompt, completer, True)
            # If the user didn't type anything, return None.
            if not answer:
                continue
            # User wants to go back.
            if int(answer) == 0:
                return None
            # If the user typed a number, return the corresponding spell.
            if answer.isdigit() and 1 <= int(answer) <= len(spells):
                return spells[int(answer) - 1]
            # Find the spell with the matching name.
            spell = next((s for s in spells if s.name.lower() == answer.lower()), None)
            if spell:
                return spell

    def _create_target_list(self, targets: list[Character]) -> Table:
        """
        Create a Rich table of targets for the player to choose from.
        """
        tbl = Table(title="Targets", pad_edge=False)
        tbl.add_column("#", style="cyan", no_wrap=True)
        tbl.add_column("Name", style="bold")
        tbl.add_column("HP", justify="center")
        tbl.add_column("AC", justify="right")
        for i, target in enumerate(targets, 1):
            tbl.add_row(
                str(i),
                target.name,
                f"{target.hp:>3}/{target.HP_MAX:<3}",
                str(target.AC),
            )
        return tbl

    def _create_action_table(self, actions: list[BaseAction]) -> Table:
        # Optional: define sort priority if you want custom order
        type_priority = {
            ActionType.STANDARD: 0,
            ActionType.BONUS: 1,
            ActionType.FREE: 2,
        }
        category_priority = {
            ActionCategory.OFFENSIVE: 0,
            ActionCategory.HEALING: 1,
            ActionCategory.BUFF: 2,
            ActionCategory.DEBUFF: 3,
            ActionCategory.UTILITY: 4,
            ActionCategory.DEBUG: 5,
        }
        # Sort actions by ActionType (then by name for stability)
        actions.sort(
            key=lambda action: (
                type_priority.get(action.type, 99),
                category_priority.get(action.category, 99),
                action.name.lower(),
            )
        )
        # Create a Rich table of actions for the player to choose from.
        tbl = Table(title="Actions", pad_edge=False)
        tbl.add_column("#", style="cyan", no_wrap=True)
        tbl.add_column("Name", style="bold")
        tbl.add_column("Type", style="magenta")
        tbl.add_column("Category", style="blue")
        for i, action in enumerate(actions, 1):
            tbl.add_row(
                str(i),
                action.name,
                self._color_action_type(action.type),
                self._color_action_category(action.category),
            )
        return tbl

    def _create_spell_table(self, spells: list[Spell]) -> Table:
        # Optional: define sort priority if you want custom order
        type_priority = {
            ActionType.STANDARD: 0,
            ActionType.BONUS: 1,
            ActionType.FREE: 2,
        }
        category_priority = {
            ActionCategory.OFFENSIVE: 0,
            ActionCategory.HEALING: 1,
            ActionCategory.BUFF: 2,
            ActionCategory.DEBUFF: 3,
            ActionCategory.UTILITY: 4,
            ActionCategory.DEBUG: 5,
        }
        # Sort actions by ActionType (then by name for stability)
        spells.sort(
            key=lambda spell: (
                type_priority.get(spell.type, 99),
                category_priority.get(spell.category, 99),
                spell.name.lower(),
            )
        )
        # Create a Rich table of spells for the player to choose from.
        tbl = Table(title="Spells", pad_edge=False)
        tbl.add_column("#", style="cyan", no_wrap=True)
        tbl.add_column("Name", style="bold")
        tbl.add_column("Type", style="magenta")
        tbl.add_column("Category", style="blue")
        tbl.add_column("Mind", justify="center")
        for i, spell in enumerate(spells, 1):
            tbl.add_row(
                str(i),
                spell.name,
                self._color_action_type(spell.type),
                self._color_action_category(spell.category),
                str(spell.mind),
            )
        return tbl

    def _color_action_type(self, action_type: ActionType) -> str:
        return f"[{get_action_type_color(action_type)}]{action_type.name.title()}[/]"

    def _color_action_category(self, category: ActionCategory) -> str:
        return f"[{get_action_category_color(category)}]{category.name.title()}[/]"
