"""
User interface module for the simulator.

Provides console-based user interface components for interacting with the
simulator, including prompts, menus, and output formatting.
"""

from typing import Any

from actions.base_action import BaseAction
from actions.spells.base_spell import BaseSpell
from actions.spells.spell_buff import SpellBuff
from actions.spells.spell_debuff import SpellDebuff
from actions.spells.spell_heal import SpellHeal
from actions.spells.spell_offensive import SpellOffensive
from character.main import Character
from combat.damage import get_damage_expr, get_max_damage, get_min_damage
from core.constants import ActionCategory, ActionClass
from core.dice_parser import (
    VarInfo,
    evaluate_expression,
    get_max_roll,
    get_min_roll,
    simplify_expression,
)
from core.utils import ccapture
from prompt_toolkit import ANSI, PromptSession
from rich.table import Table

# one session keeps history
session: PromptSession = PromptSession(erase_when_done=True)


class PlayerInterface:
    """
    Command-line interface for player interactions in the combat simulator.

    Provides Rich table-based menus for action selection, target selection,
    spell selection, and other combat-related choices. Uses prompt_toolkit
    for interactive input with numeric and alphabetic shortcuts.
    """

    def __init__(self) -> None:
        """Initialize the PlayerInterface with no configuration needed."""

    def choose_action(
        self,
        actions: list[BaseAction],
        submenus: list[str] = [],
        exit_entry: str | None = "Back",
    ) -> BaseAction | str | None:
        """Choose an action from a list of available actions.

        Args:
            actions (list[BaseAction]): The list of available actions to choose from.
            submenus (list[str], optional): A list of submenu options. Defaults to [].
            exit_entry (Optional[str], optional): Text for exit option. Defaults to "Back".

        Returns:
            Optional[BaseAction | str]: The selected action, "q" for exit, or a submenu option.

        """
        if not actions and not submenus:
            return None
        sorted_submenus = [*sorted(submenus, key=lambda s: s.lower())]
        # Sort targets and submenus for consistent display.
        actions_sorted = self.sort_actions(actions)
        # Create a table of actions.
        table = Table(title="Actions", pad_edge=False)
        table.add_column("#", style="cyan")
        table.add_column("Name", style="bold")
        table.add_column("Type", style="magenta")
        table.add_column("Category", style="blue")
        for i, action in enumerate(actions_sorted, 1):
            table.add_row(
                str(i),
                action.name,
                f"{action.action_class.colored_name}",
                f"{action.category.colored_name}",
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
        prompt = "\n" + ccapture(table) + "\nAction > "
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
        targets: list[Character],
        submenus: list[str] = [],
        exit_entry: str | None = "Back",
    ) -> Character | str | None:
        """Choose a target from a list of characters.

        Args:
            targets (list[Character]): The list of target characters to choose from.
            submenus (list[str], optional): A list of submenu options. Defaults to [].
            exit_entry (Optional[str], optional): Text for exit option. Defaults to "Back".

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
        table = Table(title="Targets", pad_edge=False)
        table.add_column("#", style="cyan", no_wrap=True)
        table.add_column("Name", style="bold")
        table.add_column("HP", justify="right")
        table.add_column("AC", justify="right")
        for i, target in enumerate(sorted_targets, 1):
            table.add_row(
                str(i),
                target.name,
                f"{target.stats.hp:>3}/{target.HP_MAX:<3}",
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
        prompt = "\n" + ccapture(table) + "\nTarget > "
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
        targets: list[Character],
        max_targets: int,
        submenus: list[str] = [],
        exit_entry: str | None = "Back",
    ) -> list[Character] | str | None:
        """Choose multiple targets from a list of characters.

        Args:
            targets (list[Character]): The list of target characters to choose from.
            max_targets (int): The maximum number of targets that can be selected.
            submenus (list[str], optional): A list of submenu options. Defaults to [].
            exit_entry (Optional[str], optional): Text for exit option. Defaults to "Back".

        Returns:
            Optional[list[Character] | str]: The list of selected characters, "q" for exit, or a submenu option.

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
                    str(t.stats.hp),
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
            prompt = "\n" + ccapture(table) + "\nSelect > "
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
        spells: list[BaseSpell],
        submenus: list[str] = [],
        exit_entry: str | None = "Back",
    ) -> BaseSpell | str | None:
        """Choose a spell from a list of available spells.

        Args:
            spells (list[BaseSpell]): The list of available spells to choose from.
            submenus (list[str], optional): A list of submenus to display. Defaults to [].
            exit_entry (Optional[str], optional): Text for exit option. Defaults to "Back".

        Returns:
            Optional[BaseSpell | str]: The selected spell, "q" for exit, or submenu.

        """
        # Add "Back" to the submenus if requested.
        sorted_submenus = sorted(submenus, key=lambda s: s.lower())
        # Sort targets and submenus for consistent display.
        sorted_spells = self.sort_actions(spells)
        # Generate a table of spells.
        table = Table(title="Spells", pad_edge=False)
        table.add_column("#", style="cyan")
        table.add_column("Name", style="bold")
        table.add_column("Type", style="magenta")
        table.add_column("Category", style="blue")
        for i, spell in enumerate(sorted_spells, 1):
            table.add_row(
                str(i),
                spell.name,
                f"{spell.action_class.colored_name}",
                f"{spell.category.colored_name}",
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
        prompt = "\n" + ccapture(table) + "\nSpell > "
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

    def choose_rank(
        self,
        actor: Character,
        spell: BaseSpell,
        exit_entry: str | None = "Back",
    ) -> int:
        """
        Prompt the user to select the rank at which to cast a spell.

        Args:
            actor (Character):
                The character casting the spell.
            spell (BaseSpell):
                The spell being cast.
            exit_entry (str | None):
                Text for exit option. Defaults to "Back".

        Returns:
            int:
                The selected rank's mind cost, or -1 if the user chose to exit.

        """
        # Only one rank available, return it.
        if len(spell.mind_cost) == 1:
            return 0

        prompt = "\n"
        prompt = f"\n[bold]Upcasting [cyan]{spell.name}[/] is allowed[/]:\n"
        for rank, mind_level in enumerate(spell.mind_cost, 0):
            # Set the mind level in the variables for evaluation.
            variables = actor.get_expression_variables()
            variables.append(VarInfo(name="RANK", value=rank + 1))
            variables.append(VarInfo(name="MIND", value=mind_level))

            # Get the maximum number of targets if applicable.
            max_targets = evaluate_expression(spell.target_expr, variables)

            prompt += f"    Rank {rank + 1} consumes {mind_level} mind → "

            # Format each spell type accordingly.
            if isinstance(spell, SpellHeal):
                expr = simplify_expression(spell.heal_roll, variables)
                min_heal = get_min_roll(spell.heal_roll, variables)
                max_heal = get_max_roll(spell.heal_roll, variables)
                prompt += f"Heals {expr} (~ {min_heal:>2}-{max_heal:<2})"
                if max_targets > 1:
                    prompt += f" (up to {max_targets} targets)"
                prompt += "\n"

            elif isinstance(spell, SpellOffensive):
                expr = get_damage_expr(spell.damage, variables)
                min_damage = get_min_damage(spell.damage, variables)
                max_damage = get_max_damage(spell.damage, variables)
                prompt += f"Deals {expr} (~ {min_damage:>2}-{max_damage:<2})"
                if max_targets > 1:
                    prompt += f" (up to {max_targets} targets)"
                prompt += "\n"

            elif isinstance(spell, SpellBuff | SpellDebuff):
                modifiers = spell.get_modifier_expressions(variables)
                if max_targets > 1:
                    prompt += f" (up to {max_targets} targets)"
                prompt += ", ".join(
                    f"{modifier} to {bonus.name.title()}"
                    for bonus, modifier in modifiers.items()
                )
                prompt += "\n"
        if exit_entry:
            prompt += "\n[bold]Press [red]q[/] to go back[/]."
        prompt += "\nMind > "

        while True:
            # Prompt the user for input.
            answer = session.prompt(ANSI(ccapture(prompt)))
            if not answer:
                continue

            # If the user typed a number, return the corresponding rank.
            selected_rank: int = self.get_digit_choice(answer)
            # Return the selected rank if valid, 0-indexed to match list indices.
            if 0 < selected_rank <= len(spell.mind_cost):
                return selected_rank - 1
            # If the user typed 'q', return -1 to indicate going back.
            if isinstance(answer, str) and answer.lower() == "q":
                return -1

    @staticmethod
    def sort_actions(actions: list[Any]) -> list[Any]:
        """
        Sort actions by their type, category, and name for consistent display.

        Prioritizes action classes (Standard, Bonus, Free) then categories
        (Offensive, Healing, Buff, Debuff, Utility, Debug), then alphabetically by name.

        Args:
            actions (list[Any]): List of BaseAction instances to sort.

        Returns:
            list[Any]: The sorted list of actions.

        Raises:
            AssertionError: If any action is not an instance of BaseAction.

        """
        assert all(
            isinstance(action, BaseAction) for action in actions
        ), "All actions must be instances of BaseAction."
        # Optional: define sort priority if you want custom order
        type_priority = {
            ActionClass.STANDARD: 0,
            ActionClass.BONUS: 1,
            ActionClass.FREE: 2,
        }
        category_priority = {
            ActionCategory.OFFENSIVE: 0,
            ActionCategory.HEALING: 1,
            ActionCategory.BUFF: 2,
            ActionCategory.DEBUFF: 3,
            ActionCategory.UTILITY: 4,
            ActionCategory.DEBUG: 5,
        }
        # Sort actions by ActionClass (then by name for stability)
        actions.sort(
            key=lambda action: (
                type_priority.get(action.action_class, 99),
                category_priority.get(action.category, 99),
                action.name.lower(),
            )
        )
        return actions

    @staticmethod
    def get_digit_choice(answer: str) -> int:
        """
        Convert a single digit string input to its integer value.

        Args:
            answer (str): User input string to parse.

        Returns:
            int: The integer value of the digit (0-9), or -1 if invalid input.

        """
        if isinstance(answer, str) and len(answer) == 1 and answer.isdigit():
            return int(answer)
        return -1

    @staticmethod
    def get_alpha_choice(answer: Any) -> int:
        """
        Convert a single alphabetic character to its index position.

        Maps 'a' or 'A' to 0, 'b' or 'B' to 1, etc. Case-insensitive.

        Args:
            answer (Any): User input to parse.

        Returns:
            int: The index position (0-25 for a-z), or -1 if invalid input.

        """
        if isinstance(answer, str) and len(answer) == 1 and answer.isalpha():
            return ord(answer.lower()) - ord("a")
        return -1
