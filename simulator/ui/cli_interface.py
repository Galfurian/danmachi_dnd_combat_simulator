# cli_prompt.py
from typing import Any, List, Optional

from rich.console import Console
from rich.table import Table

from prompt_toolkit import PromptSession
from prompt_toolkit import ANSI

from entities.character import *
from actions.base_action import *
from actions.spell_action import *
from actions.attack_action import *
from core.constants import *
from core.utils import *


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


class PlayerInterface:
    """
    - Shows a Rich table of abilities each time.
    - Offers autocomplete + numeric shortcuts.
    - Wipes the typed prompt line after ⏎ (erase_when_done=True).
    """

    def __init__(self) -> None:
        pass

    def choose_action(
        self, actions: List[BaseAction], submenus: list[str] = []
    ) -> Optional[BaseAction | str]:
        if not actions:
            return None
        # Sort targets and submenus for consistent display.
        actions_sorted = self.sort_actions(actions)
        submenus_sorted = sorted(submenus, key=lambda s: s.lower())
        # Create a table of actions.
        table = Table(title=f"Actions", pad_edge=False)
        table.add_column("#", style="cyan")
        table.add_column("Name", style="bold")
        table.add_column("Type", style="magenta")
        table.add_column("Category", style="blue")
        for i, action in enumerate(actions_sorted, 1):
            table.add_row(
                str(i),
                action.name,
                action.type.name.title(),
                action.category.name.title(),
            )
        # Add the submenu actions if any.
        if submenus:
            table.add_row()
            for i, submenu in enumerate(submenus, 0):
                table.add_row(chr(97 + i), submenu, "Submenu", "")
        # Generate a prompt with the table and a question.
        prompt = "\n" + table_to_str(table) + "\nAction > "
        while True:
            # Prompt the user for input.
            answer = session.prompt(ANSI(prompt))

            # Keep asking until the user provides a valid input.
            if not answer:
                continue

            # If the user typed a number, return the corresponding action.
            index = self.get_digit_choice(answer)
            if 0 <= index < len(actions_sorted):
                return actions_sorted[index]

            # If the user typed a letter, return the corresponding submenu.
            index = self.get_alpha_choice(answer)
            if 0 <= index < len(submenus_sorted):
                return submenus_sorted[index]

    def choose_target(
        self,
        targets: List[Character],
        submenus: list[str] = [],
    ) -> Optional[Character | str]:
        # If there are no targets, return None.
        if not targets:
            return None
        # Sort targets and submenus for consistent display.
        sorted_targets = sorted(targets, key=lambda t: t.name.lower())
        sorted_submenus = sorted(submenus, key=lambda s: s.lower())
        # Create a table of targets.
        table = Table(title=f"Targets", pad_edge=False)
        table.add_column("#", style="cyan", no_wrap=True)
        table.add_column("Name", style="bold")
        table.add_column("HP", justify="right")
        table.add_column("AC", justify="right")
        for i, target in enumerate(sorted_targets, 1):
            table.add_row(
                str(i),
                target.name,
                f"{target.hp:>3}/{target.HP_MAX:<3}",
                str(target.AC),
            )
        # Add the submenu actions if any.
        if sorted_submenus:
            table.add_row()
            for i, submenu in enumerate(sorted_submenus, 0):
                table.add_row(chr(97 + i), submenu, "Submenu", "")
        # Generate a prompt with the table and a question.
        prompt = "\n" + table_to_str(table) + "\nTarget > "
        while True:
            # Prompt the user for input.
            answer = session.prompt(ANSI(prompt))
            # Keep asking until the user provides a valid input.
            if not answer:
                continue
            # If the user typed a number, return the corresponding action.
            index = self.get_digit_choice(answer)
            if 0 <= index < len(sorted_targets):
                return sorted_targets[index]

            # If the user typed a letter, return the corresponding submenu.
            index = self.get_alpha_choice(answer)
            if 0 <= index < len(sorted_submenus):
                return sorted_submenus[index]

    def choose_targets(
        self,
        targets: List[Character],
        max_targets: int,
        submenus: list[str] = [],
    ) -> Optional[List[Character] | str]:
        if not targets:
            return None
        if max_targets <= 0:
            return None
        # Sort targets and submenus for consistent display.
        sorted_targets = sorted(targets, key=lambda t: t.name.lower())
        sorted_submenus = sorted(submenus, key=lambda s: s.lower())
        # Prepare a set of selected targets.
        selected: set[Character] = set()
        # Create the table.
        table = Table(pad_edge=False)
        table.add_column("#", style="cyan", no_wrap=True)
        table.add_column("Name", style="bold")
        table.add_column("HP", justify="right")
        table.add_column("AC", justify="right")
        table.add_column("Selected", justify="center")
        while True:
            table.rows.clear()
            # Add the targets to the table.
            for i, t in enumerate(sorted_targets, 1):
                table.add_row(
                    str(i),
                    t.name,
                    str(t.hp),
                    str(t.AC),
                    "[green]✓[/]" if t in selected else "",
                )
            # Add the submenu actions if any.
            if sorted_submenus:
                table.add_row()
                for i, submenu in enumerate(sorted_submenus, 0):
                    table.add_row(chr(97 + i), submenu, "Submenu", "", "")
            # Prepare the prompt with the table.
            prompt = "\n" + table_to_str(table) + "\nSelect > "
            # Prompt the user for input.
            answer = session.prompt(ANSI(prompt))
            # If the user didn't type anything, continue the loop.
            if not answer:
                continue

            # If the user typed a number, toggle the selection of the corresponding target.
            index = self.get_digit_choice(answer)
            if 0 <= index < len(sorted_targets):
                # Get the target at the index.
                target = sorted_targets[index]
                # Check if the target is already selected, in that case remove it.
                if target in selected:
                    selected.remove(target)
                    continue
                # If the target is not selected, add it to the selection.
                if len(selected) >= max_targets:
                    continue
                # Select the target.
                selected.add(target)
                continue

            # If the user typed a letter, return the corresponding submenu.
            index = self.get_alpha_choice(answer)
            if 0 <= index < len(sorted_submenus):
                # If the user selected a submenu, return it.
                return sorted_submenus[index]

    def choose_spell(
        self,
        spells: list[Spell],
        submenus: list[str] = [],
    ) -> Optional[Spell | str]:
        # Sort targets and submenus for consistent display.
        sorted_spells = self.sort_actions(spells)
        sorted_submenus = sorted(submenus, key=lambda s: s.lower())
        # Generate a table of spells.
        table = Table(title=f"Spells", pad_edge=False)
        table.add_column("#", style="cyan")
        table.add_column("Name", style="bold")
        table.add_column("Type", style="magenta")
        table.add_column("Category", style="blue")
        for i, spell in enumerate(sorted_spells, 1):
            table.add_row(
                str(i),
                spell.name,
                f"[{get_action_type_color(spell.type)}]{spell.type.name.title()}[/]",
                f"[{get_action_category_color(spell.category)}]{spell.category.name.title()}[/]",
            )
        # Add the submenu actions if any.
        if sorted_submenus:
            table.add_row()
            for i, submenu in enumerate(sorted_submenus, 0):
                table.add_row(chr(97 + i), submenu, "Submenu", "")
        # Generate a prompt with the table and a question.
        prompt = "\n" + table_to_str(table) + "\nSpell > "
        # Create a completer for the spell names.
        while True:
            # Prompt the user for input.
            answer = session.prompt(ANSI(prompt))

            # If the user didn't type anything, continue the loop.
            if not answer:
                continue

            # If the user typed a number, return the corresponding spell.
            index = self.get_digit_choice(answer)
            if 0 <= index < len(sorted_spells):
                return sorted_spells[index]

            # If the user typed a letter, return the corresponding submenu.
            index = self.get_alpha_choice(answer)
            if 0 <= index < len(sorted_submenus):
                return sorted_submenus[index]

    def choose_mind(self, actor: Character, spell: Spell) -> int:
        """Prompts the user to select the amount of MIND to spend on a spell (if upcast is allowed)."""
        if len(spell.mind_cost) == 1:
            return spell.mind_cost[0]
        # Get the variables for the prompt.
        variables = actor.get_expression_variables()
        prompt = "\n"
        prompt = to_ansi(f"\n[bold]Upcasting [cyan]{spell.name}[/] is allowed[/]:\n")
        for mind_level in spell.mind_cost:
            variables["MIND"] = mind_level
            max_targets = (
                ""
                if not spell.multi_target_expr
                else f", Targets: {evaluate_expression(
                spell.multi_target_expr, variables
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
        prompt += "\nMind > "

        while True:
            # Prompt the user for input.
            answer = session.prompt(ANSI(prompt))
            if not answer:
                continue

            # If the user typed a number, return the corresponding mind cost.
            index = self.get_digit_choice(answer)
            if 0 <= index < len(spell.mind_cost):
                return spell.mind_cost[index]

    @staticmethod
    def sort_actions(actions: List[Any]) -> List[Any]:
        """
        Sorts actions by their type and name.
        """
        assert all(
            isinstance(action, BaseAction) for action in actions
        ), "All actions must be instances of BaseAction."
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
        return actions

    @staticmethod
    def get_digit_choice(answer: str) -> int:
        """
        Converts a single digit input to an index (0 for '0', 1 for '1', etc.).
        """
        if isinstance(answer, str) and len(answer) == 1 and answer.isdigit():
            return int(answer) - 1
        return -1

    @staticmethod
    def get_alpha_choice(answer: Any) -> int:
        """
        Converts a single character input to an index (0 for 'a', 1 for 'b', etc.).
        """
        if isinstance(answer, str) and len(answer) == 1 and answer.isalpha():
            return ord(answer.lower()) - ord("a")
        return -1
