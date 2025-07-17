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
        self,
        actions: List[BaseAction],
        submenus: list[str] = [],
        exit_entry: Optional[str] = "Back",
    ) -> Optional[BaseAction | str]:
        """Choose an action from a list of available actions.

        Args:
            actions (List[BaseAction]): The list of available actions to choose from.
            submenus (list[str], optional): A list of submenu options. Defaults to [].

        Returns:
            Optional[BaseAction | str]: The selected action, "q" for exit, or a submenu option.
        """
        if not actions and not submenus:
            return None
        sorted_submenus = [*sorted(submenus, key=lambda s: s.lower())]
        # Sort targets and submenus for consistent display.
        actions_sorted = self.sort_actions(actions)
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
        # Add an empty row if there are submenus or an exit entry.
        if sorted_submenus or exit_entry:
            table.add_row()
        # Add the submenu actions if any.
        for i, submenu in enumerate(sorted_submenus, 0):
            table.add_row(chr(97 + i), submenu, "Submenu", "")
        # Add the exit entry if requested.
        if exit_entry:
            table.add_row("q", exit_entry, "", "")
        # Generate a prompt with the table and a question.
        prompt = "\n" + table_to_str(table) + "\nAction > "
        while True:
            # Prompt the user for input.
            answer = session.prompt(ANSI(prompt))

            # Keep asking until the user provides a valid input.
            if not answer:
                continue

            # If the user typed a number, return the corresponding action.
            index = self.get_digit_choice(answer) - 1
            if 0 <= index < len(actions_sorted):
                return actions_sorted[index]

            # If the user typed a letter, return the corresponding submenu.
            index = self.get_alpha_choice(answer)
            if 0 <= index < len(submenus):
                return submenus[index]

            # If the user typed 'q', return a generic "q".
            if isinstance(answer, str) and answer.lower() == "q":
                return "q"

    def choose_target(
        self,
        targets: List[Character],
        submenus: list[str] = [],
        exit_entry: Optional[str] = "Back",
    ) -> Optional[Character | str]:
        """Choose a target from a list of characters.

        Args:
            targets (List[Character]): The list of target characters to choose from.
            submenus (list[str], optional): A list of submenu options. Defaults to [].

        Returns:
            Optional[Character | str]: The selected target character, "q" for exit, or a submenu option.
        """
        # If there are no targets, return None.
        if not targets:
            return None
        # Add "Back" to the submenus if requested.
        sorted_submenus = sorted(submenus, key=lambda s: s.lower())
        # Sort targets and submenus for consistent display.
        sorted_targets = sorted(targets, key=lambda t: t.name.lower())
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
        # Add an empty row if there are submenus or an exit entry.
        if sorted_submenus or exit_entry:
            table.add_row()
        # Add the submenu actions if any.
        for i, submenu in enumerate(sorted_submenus, 0):
            table.add_row(chr(97 + i), submenu, "Submenu", "")
        # Add the exit entry if requested.
        if exit_entry:
            table.add_row("q", exit_entry, "", "")
        # Generate a prompt with the table and a question.
        prompt = "\n" + table_to_str(table) + "\nTarget > "
        while True:
            # Prompt the user for input.
            answer = session.prompt(ANSI(prompt))
            # Keep asking until the user provides a valid input.
            if not answer:
                continue
            # If the user typed a number, return the corresponding action.
            index = self.get_digit_choice(answer) - 1
            if 0 <= index < len(sorted_targets):
                return sorted_targets[index]

            # If the user typed a letter, return the corresponding submenu.
            index = self.get_alpha_choice(answer)
            if 0 <= index < len(sorted_submenus):
                return sorted_submenus[index]

            # If the user typed 'q', return a generic "q".
            if isinstance(answer, str) and answer.lower() == "q":
                return "q"

    def choose_targets(
        self,
        targets: List[Character],
        max_targets: int,
        submenus: list[str] = [],
        exit_entry: Optional[str] = "Back",
    ) -> Optional[List[Character] | str]:
        """Choose multiple targets from a list of characters.

        Args:
            targets (List[Character]): The list of target characters to choose from.
            max_targets (int): The maximum number of targets that can be selected.
            submenus (list[str], optional): A list of submenu options. Defaults to [].

        Returns:
            Optional[List[Character] | str]: The list of selected characters, "q" for exit, or a submenu option.
        """
        if not targets:
            return None
        if max_targets <= 0:
            return None
        sorted_submenus = ["Confirm", *sorted(submenus, key=lambda s: s.lower())]
        # Sort targets and submenus for consistent display.
        sorted_targets = sorted(targets, key=lambda t: t.name.lower())
        # Prepare a set of selected targets.
        selected: set[Character] = set()
        while True:
            # Create the table.
            table = Table(pad_edge=False)
            table.add_column("#", style="cyan", no_wrap=True)
            table.add_column("Name", style="bold")
            table.add_column("HP", justify="right")
            table.add_column("AC", justify="right")
            table.add_column("Selected", justify="center")
            # Add the targets to the table.
            for i, t in enumerate(sorted_targets, 1):
                table.add_row(
                    str(i),
                    t.name,
                    str(t.hp),
                    str(t.AC),
                    "[green]✓[/]" if t in selected else "",
                )
            # Add an empty row if there are submenus or an exit entry.
            if sorted_submenus or exit_entry:
                table.add_row()
            # Add the submenu actions if any.
            for i, submenu in enumerate(sorted_submenus, 1):
                table.add_row(chr(96 + i), submenu, "Submenu", "", "")
            # Add the exit entry if requested.
            if exit_entry:
                table.add_row("q", exit_entry, "", "", "")
            # Prepare the prompt with the table.
            prompt = "\n" + table_to_str(table) + "\nSelect > "
            # Prompt the user for input.
            answer = session.prompt(ANSI(prompt))
            # If the user didn't type anything, continue the loop.
            if not answer:
                continue

            # If the user typed a number, toggle the selection of the corresponding target.
            index = self.get_digit_choice(answer) - 1
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
                if sorted_submenus[index] == "Confirm":
                    return list(selected) if selected else None
                # If the user selected a submenu, return it.
                return sorted_submenus[index]

            # If the user typed 'q', return a generic "q".
            if isinstance(answer, str) and answer.lower() == "q":
                return "q"

    def choose_spell(
        self,
        spells: list[Spell],
        submenus: list[str] = [],
        exit_entry: Optional[str] = "Back",
    ) -> Optional[Spell | str]:
        """Choose a spell from a list of available spells.

        Args:
            spells (list[Spell]): The list of available spells to choose from.
            submenus (list[str], optional): A list of submenus to display. Defaults to [].

        Returns:
            Optional[Spell | str]: The selected spell, "q" for exit, or submenu.
        """
        # Add "Back" to the submenus if requested.
        sorted_submenus = sorted(submenus, key=lambda s: s.lower())
        # Sort targets and submenus for consistent display.
        sorted_spells = self.sort_actions(spells)
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
        # Add an empty row if there are submenus or an exit entry.
        if sorted_submenus or exit_entry:
            table.add_row()
        # Add the submenu actions if any.
        for i, submenu in enumerate(sorted_submenus, 0):
            table.add_row(chr(97 + i), submenu, "Submenu", "")
        # Add the exit entry if requested.
        if exit_entry:
            table.add_row("q", exit_entry, "", "")
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
            index = self.get_digit_choice(answer) - 1
            if 0 <= index < len(sorted_spells):
                return sorted_spells[index]

            # If the user typed a letter, return the corresponding submenu.
            index = self.get_alpha_choice(answer)
            if 0 <= index < len(sorted_submenus):
                return sorted_submenus[index]

            # If the user typed 'q', return a generic "q".
            if isinstance(answer, str) and answer.lower() == "q":
                return "q"

    def choose_mind(
        self, actor: Character, spell: Spell, exit_entry: Optional[str] = "Back"
    ) -> int:
        """Prompts the user to select the amount of MIND to spend on a spell (if upcast is allowed)."""
        if len(spell.mind_cost) == 1:
            return spell.mind_cost[0]
        # Get the variables for the prompt.
        variables = actor.get_expression_variables()
        prompt = "\n"
        prompt = f"\n[bold]Upcasting [cyan]{spell.name}[/] is allowed[/]:\n"
        for mind_level in spell.mind_cost:
            # Set the mind level in the variables for evaluation.
            variables["MIND"] = mind_level

            # Get the maximum number of targets if applicable.
            max_targets = evaluate_expression(spell.multi_target_expr, variables)

            prompt += f"    {mind_level} Mind → "

            # Format each spell type accordingly.
            if isinstance(spell, SpellHeal):
                prompt += f"Heals {simplify_expression(spell.heal_roll, variables)}"
                prompt += f" (~ {spell.get_min_heal(actor, mind_level):>2}-{spell.get_max_heal(actor, mind_level):<2})"
                if max_targets > 1:
                    prompt += f" (up to {max_targets} targets)"
                prompt += "\n"

            elif isinstance(spell, SpellAttack):
                prompt += f"Deals "
                prompt += "+ ".join(
                    f"{simplify_expression(component.damage_roll, variables)}"
                    f" [{get_damage_type_color(component.damage_type)}]{component.damage_type.name.title()}[/]"
                    for component in spell.damage
                )
                prompt += f" (~ {spell.get_min_damage(actor, mind_level):>2}-{spell.get_max_damage(actor, mind_level):<2})"
                if max_targets > 1:
                    prompt += f" (up to {max_targets} targets)"
                prompt += "\n"

            elif isinstance(spell, SpellBuff):
                # If the spell has a consume_on_hit effect, indicate it.
                if spell.effect.consume_on_hit:
                    prompt += f"(one-shot)"
                if max_targets > 1:
                    prompt += f" (up to {max_targets} targets)"

                # Iterate over each modifier and bonus.
                for bonus_type, value in spell.effect.modifiers.items():
                    if isinstance(value, DamageComponent):
                        prompt += (
                            f" {simplify_expression(value.damage_roll, variables)} "
                            f"[{get_damage_type_color(value.damage_type)}]{value.damage_type.name.title()}[/]"
                        )
                    else:
                        prompt += f" {value} to {bonus_type.name.title()}"
                prompt += "\n"
            elif isinstance(spell, SpellDebuff):
                # Get the modifier expressions for debuffs.
                modifiers = spell.get_modifier_expressions(actor, mind_level)

                # If the spell has a consume_on_hit effect, indicate it.
                if max_targets > 1:
                    prompt += f" (up to {max_targets} targets)"

                # Iterate over each modifier and bonus.
                prompt += f", ".join(
                    f"{modifier} to {bonus.name.title()}"
                    for bonus, modifier in modifiers.items()
                )
                prompt += "\n"
        if exit_entry:
            prompt += f"\n[bold]Press [red]q[/] to go back[/]."
        prompt += "\nMind > "

        while True:
            # Prompt the user for input.
            answer = session.prompt(ANSI(to_ansi(prompt)))
            if not answer:
                continue

            # If the user typed a number, return the corresponding mind cost.
            mind_cost: int = self.get_digit_choice(answer)
            if mind_cost in spell.mind_cost:
                return mind_cost
            # If the user typed 'q', return -1 to indicate going back.
            if isinstance(answer, str) and answer.lower() == "q":
                return -1

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
            return int(answer)
        return -1

    @staticmethod
    def get_alpha_choice(answer: Any) -> int:
        """
        Converts a single character input to an index (0 for 'a', 1 for 'b', etc.).
        """
        if isinstance(answer, str) and len(answer) == 1 and answer.isalpha():
            return ord(answer.lower()) - ord("a")
        return -1
