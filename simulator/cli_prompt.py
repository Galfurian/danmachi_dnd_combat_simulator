# cli_prompt.py
from typing import Any, Generator, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from actions.base_action import BaseAction
from actions.attack_action import BaseAttack
from actions.spell_action import Spell, SpellAttack, SpellHeal, SpellBuff, SpellDebuff
from character import Character
from prompt_toolkit import ANSI
from effect import Buff, Debuff

from constants import *
from interfaces import (
    ActionOption,
    CastSpellOption,
    MenuOption,
    MindLevelOption,
    PlayerInterface,
    SpellOption,
    SubmenuOption,
    TargetOption,
)
from utils import evaluate_expression, substitute_variables


# main console for everything else
console = Console()
# one session keeps history
session = PromptSession(erase_when_done=True)


def to_ansi(content: Any) -> str:
    with console.capture() as capture:
        console.print(content, markup=True, end="")
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
        self, actions: List[MenuOption]
    ) -> Optional[MenuOption | ActionOption]:
        assert actions, "No actions available for the actor"
        # Generate a table of actions (including "Cast a Spell" if present)
        tbl, metadata = self._create_action_table(actions)
        if not tbl.rows:
            return None
        # Generate a prompt with the table and a question.
        prompt = "\n" + table_to_str(tbl) + "\nAction > "
        while True:
            # Prompt the user for input.
            answer = session.prompt(ANSI(prompt)).lower()
            # If the user didn't type anything, return None.
            if not answer:
                continue
            # If the user typed a number, return the corresponding action.
            if metadata.get(answer):
                action = metadata[answer]
                if isinstance(action, ActionOption):
                    return action
                if isinstance(action, SubmenuOption):
                    return action

    def choose_target(
        self, targets: List[MenuOption]
    ) -> Optional[MenuOption | TargetOption]:
        # Get the list of targets.
        targets = sorted(targets, key=lambda t: t.name)
        # If there are no targets, return None.
        if not targets:
            return None
        # Create a table of targets.
        tbl = self._create_target_table(targets)
        tbl.add_row()
        tbl.add_row("0", "Back", "", "")
        # Generate a prompt with the table and a question.
        prompt = "\n"
        prompt += table_to_str(tbl) + "\nTarget > "
        # Create a completer for the target names.
        completer = WordCompleter(
            [t.name for t in targets] + ["Back"], ignore_case=True
        )
        while True:
            # Prompt the user for input.
            answer = show_prompt(prompt, completer, True).lower()
            # If the user didn't type anything, return None.
            if not answer:
                continue
            # If the user typed a number, return the corresponding target.
            if answer.isdigit():
                if 1 <= int(answer) <= len(targets):
                    return targets[int(answer) - 1]
                if int(answer) == 0:
                    return None
            else:
                if answer == "back":
                    return None
                # Find the target with the matching name.
                target = next((t for t in targets if t.name.lower() == answer), None)
                # If a valid target was found, return it.
                if isinstance(target, Character):
                    return target

    def choose_targets(
        self, targets: List[MenuOption], max_targets: int
    ) -> Optional[MenuOption | List[TargetOption]]:
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
        if len(spell.mind_cost) == 1:
            return spell.mind_cost[0]
        # Get the resources for the prompt.
        resources = actor.get_expression_modifiers()
        prompt = "\n"
        prompt = to_ansi(f"\n[bold]Upcasting [cyan]{spell.name}[/] is allowed[/]:\n")
        for mind_level in spell.mind_cost:
            resources["MIND"] = mind_level
            max_targets = (
                ""
                if not spell.multi_target_expr
                else f", Targets: {evaluate_expression(
                spell.multi_target_expr, resources
            )}"
            )
            if isinstance(spell, SpellHeal):
                prompt += f"    {mind_level} → "
                prompt += f"Heal: {spell.get_heal_expr(actor, mind_level)} "
                prompt += f"[{spell.get_min_heal(actor, mind_level):>3}-{spell.get_max_heal(actor, mind_level):<3}]"
                prompt += max_targets + "\n"
            elif isinstance(spell, SpellAttack):
                prompt += f"    {mind_level} → "
                prompt += f"Damage: {spell.get_damage_expr(actor, mind_level)} "
                prompt += f"[{spell.get_min_damage(actor, mind_level):>3}-{spell.get_max_damage(actor, mind_level):<3}]"
                prompt += max_targets + "\n"
            elif isinstance(spell, SpellBuff):
                for bonus, modifier in spell.get_modifier_expressions(
                    actor, mind_level
                ).items():
                    prompt += (
                        f"    {mind_level} → Buff: {modifier} to {bonus.name.title()}"
                    )
                    if spell.effect.consume_on_hit:
                        prompt += " (one-shot)"
                    prompt += max_targets + "\n"
            elif isinstance(spell, SpellDebuff):
                for bonus, modifier in spell.get_modifier_expressions(
                    actor, mind_level
                ).items():
                    prompt += (
                        f"    {mind_level} → Debuff: {modifier} to {bonus.name.title()}"
                    )
                    prompt += max_targets + "\n"
        prompt += "    0 → Back\nMind > "

        completer = WordCompleter(
            [str(c) for c in spell.mind_cost] + ["Back"], ignore_case=True
        )
        while True:
            answer = show_prompt(prompt, completer, True)
            if answer.isdigit():
                if int(answer) in spell.mind_cost:
                    return int(answer)
                if int(answer) == 0:
                    return -1
            elif answer.lower() == "back":
                return -1

    def choose_spell(self, actor: Character, allowed: list[Spell]) -> Optional[Spell]:
        # Get the, list of spells the actor can cast.
        has_standard_action = actor.has_action_type(ActionType.STANDARD)
        has_bonus_action = actor.has_action_type(ActionType.BONUS)
        spells: list[Spell] = [
            spell
            for spell in allowed
            if (
                spell.type == ActionType.STANDARD
                and has_standard_action
                or spell.type == ActionType.BONUS
                and has_bonus_action
            )
            and not actor.is_on_cooldown(spell)
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
        completer = WordCompleter([s.name for s in spells] + ["Exit"], ignore_case=True)
        while True:
            # Prompt the user for input.
            answer = show_prompt(prompt, completer, True).lower()
            # If the user didn't type anything, return None.
            if not answer:
                continue
            # Check if the user typed a number or a spell name.
            if answer.isdigit():
                # If the user typed a number, return the corresponding spell.
                if 1 <= int(answer) <= len(spells):
                    return spells[int(answer) - 1]
                # User wants to go back.
                if int(answer) == 0:
                    return None
            else:
                if answer == "exit":
                    return None
                # Find the spell with the matching name.
                spell = next((s for s in spells if s.name.lower() == answer), None)
                if spell:
                    return spell

    def _create_action_table(
        self, options: list[MenuOption]
    ) -> tuple[Table, dict[str, MenuOption]]:
        # Sort actions by ActionType (then by name for stability)
        options = self._sort_options(options)

        # Create a Rich table of actions for the player to choose from.
        tbl = Table(title="Actions", pad_edge=False)
        tbl.add_column("#", style="cyan", no_wrap=True)
        tbl.add_column("Name", style="bold")
        tbl.add_column("Type", style="magenta")
        tbl.add_column("Category", style="blue")

        # Store in a dictionary the letter associated with each submenu action.
        metadata: dict[str, MenuOption] = {}

        for i, option in enumerate(options, 1):
            if isinstance(option, ActionOption):
                a, a_type, a_cat = (
                    option.action,
                    option.action.type,
                    option.action.category,
                )
                tbl.add_row(
                    chr(i),
                    a.name,
                    apply_action_type_color(a_type, a_type.name.title()),
                    apply_action_category_color(a_cat, a_cat.name.title()),
                )
                metadata[chr(i)] = option
            elif isinstance(option, SubmenuOption):
                # Add a special row for casting a spell.
                tbl.add_row(chr(int("a") + i), option.name, "", "")
                metadata[chr(int("a") + i)] = option
        return tbl, metadata

    def _create_target_table(self, targets: list[MenuOption]) -> Table:

        # Create a Rich table of actions for the player to choose from.
        tbl = Table(title="Targets", pad_edge=False)
        tbl.add_column("#", style="cyan", no_wrap=True)
        tbl.add_column("Name", style="bold")
        tbl.add_column("HP", justify="center")
        tbl.add_column("AC", justify="right")

        # Store in a dictionary the letter associated with each submenu action.
        metadata: dict[str, MenuOption] = {}

        for i, target in enumerate(targets, 1):
            tbl.add_row(
                str(i),
                target.name,
                f"{target.:>3}/{target.HP_MAX:<3}",
                str(target.AC),
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
                apply_action_type_color(spell.type, spell.type.name.title()),
                apply_action_category_color(
                    spell.category, spell.category.name.title()
                ),
                str(
                    spell.mind_cost[0] if len(spell.mind_cost) == 1 else spell.mind_cost
                ),
            )
        return tbl

    def _sort_options(self, options: List[MenuOption]) -> List[MenuOption]:
        """
        Sorts the options by their action type and name.
        """
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

        def sort_key(option: MenuOption) -> tuple[int, int, str]:
            if isinstance(option, ActionOption):
                # Sort actions by ActionType and ActionCategory (then by name for stability)
                return (
                    type_priority.get(option.action.type, 99),
                    category_priority.get(option.action.category, 99),
                    option.action.name.lower(),
                )
            if isinstance(option, SpellOption):
                # Sort spells by ActionType and ActionCategory (then by name for stability)
                return (
                    type_priority.get(option.spell.type, 99),
                    category_priority.get(option.spell.category, 99),
                    option.spell.name.lower(),
                )
            if isinstance(option, MindLevelOption):
                # Sort mind levels by their level (as integer)
                return (0, 0, str(option.level))
            # Default case for any other MenuOption type
            return (99, 99, option.name.lower())

        # Sort actions by ActionType (then by name for stability)
        options.sort(key=sort_key)

        return options
