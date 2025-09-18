"""Character Display Module - handles character display, formatting, and UI functionality."""

from typing import TYPE_CHECKING, List

from core.constants import (
    CharacterType,
    get_effect_color,
)
from core.utils import make_bar

if TYPE_CHECKING:
    from .main import Character


class CharacterDisplay:
    """Handles display, formatting, and UI functionality for Character objects."""

    def __init__(self, character: "Character") -> None:
        """
        Initialize the display module with a reference to the character.

        Args:
            character (Character): The character instance to display.
        """
        self._character = character

    def get_status_line(
        self,
        show_all_effects: bool = False,
        show_numbers: bool = False,
        show_bars: bool = False,
        show_ac: bool = True,
    ) -> str:
        """
        Get a formatted status line for the character with health, mana, effects, etc.

        Args:
            show_all_effects (bool): Whether to show all effects or truncate them. Defaults to False.
            show_numbers (bool): Whether to show numerical values for stats. Defaults to False.
            show_bars (bool): Whether to show bar representations for stats. Defaults to False.
            show_ac (bool): Whether to show the armor class (AC). Defaults to True.

        Returns:
            str: A formatted string representing the character's status line.
        """
        # Collect all effects with better formatting
        effects_list = []
        if self._character.effects_module.active_effects:
            for e in self._character.effects_module.active_effects:
                color = get_effect_color(e.effect)
                # Truncate long effect names and show duration more compactly
                effect_name = (
                    e.effect.name[:12] + "..."
                    if len(e.effect.name) > 15
                    else e.effect.name
                )
                effects_list.append(f"[{color}]{effect_name}[/]({e.duration if e.duration else '∞'})")

        # Build status line with better spacing
        hp_bar = (
            make_bar(
                self._character.hp, self._character.HP_MAX, color="green", length=8
            )
            if show_bars
            else ""
        )

        # Use dynamic name width based on name length, but cap it
        name_width = min(max(len(self._character.name), 8), 16)
        status = f"{self._character.char_type.emoji} [bold]{self._character.name:<{name_width}}[/] "

        # Show AC only for player and allies (not enemies) with yellow color
        if show_ac:
            status += f"| [yellow]AC:{self._character.AC:>2}[/] "

        # Build HP display based on parameters with green color
        hp_display = ""
        if show_numbers and show_bars:
            hp_display = f"| [green]HP:{self._character.hp:>3}/{self._character.HP_MAX}[/]{hp_bar} "
        elif show_numbers:
            hp_display = (
                f"| [green]HP:{self._character.hp:>3}/{self._character.HP_MAX}[/] "
            )
        elif show_bars:
            hp_display = f"| [green]HP:[/]{hp_bar} "
        else:
            # Default to showing numbers if neither is specified
            hp_display = (
                f"| [green]HP:{self._character.hp:>3}/{self._character.HP_MAX}[/] "
            )
        status += hp_display

        if self._character.MIND_MAX > 0:
            mind_bar = (
                make_bar(
                    self._character.mind,
                    self._character.MIND_MAX,
                    color="blue",
                    length=8,
                )
                if show_bars
                else ""
            )

            # Build MP display based on parameters with blue color
            mp_display = ""
            if show_numbers and show_bars:
                mp_display = f"| [blue]MP:{self._character.mind:>3}/{self._character.MIND_MAX}[/]{mind_bar} "
            elif show_numbers:
                mp_display = f"| [blue]MP:{self._character.mind:>3}/{self._character.MIND_MAX}[/] "
            elif show_bars:
                mp_display = f"| [blue]MP:[/]{mind_bar} "
            else:
                # Default to showing numbers if neither is specified
                mp_display = f"| [blue]MP:{self._character.mind:>3}/{self._character.MIND_MAX}[/] "
            status += mp_display

        # Show concentration info only for the player with magenta/purple color
        if (
            self._character.char_type == CharacterType.PLAYER
            and self._character.concentration_module.get_concentration_count()
            > 0
        ):
            concentration_count = (
                self._character.concentration_module.get_concentration_count()
            )
            concentration_limit = self._character.CONCENTRATION_LIMIT
            conc_bar = (
                make_bar(
                    concentration_count,
                    concentration_limit,
                    color="magenta",
                    length=concentration_limit,
                )
                if show_bars
                else ""
            )

            # Build concentration display based on parameters with magenta color
            conc_display = ""
            if show_numbers and show_bars:
                conc_display = f"| [magenta]C:{concentration_count}/{concentration_limit}[/]{conc_bar} "
            elif show_numbers:
                conc_display = (
                    f"| [magenta]C:{concentration_count}/{concentration_limit}[/] "
                )
            elif show_bars:
                conc_display = f"| [magenta]C:[/]{conc_bar} "
            else:
                # Default to showing numbers if neither is specified
                conc_display = (
                    f"| [magenta]C:{concentration_count}/{concentration_limit}[/] "
                )
            status += conc_display

        # Handle effects more intelligently
        if effects_list:
            if show_all_effects or len(effects_list) <= 3:
                # Show all effects if requested or 3 or fewer
                status += f"| {' '.join(effects_list)}"
            else:
                # Show first 2 effects + count of remaining
                remaining_count = len(effects_list) - 2
                status += (
                    f"| {' '.join(effects_list[:2])} [dim]+{remaining_count} more[/]"
                )

        return status

    def get_detailed_effects(self) -> str:
        """
        Get a detailed multi-line view of all active effects.

        Returns:
            str: A detailed string of all active effects with descriptions.
        """
        if not self._character.effects_module.active_effects:
            return "No active effects"

        effects_info = []
        for e in self._character.effects_module.active_effects:
            color = get_effect_color(e.effect)
            effects_info.append(
                f"  [{color}]{e.effect.name}[/] ({e.duration} turns): {e.effect.description}"
            )

        return "Active Effects:\n" + "\n".join(effects_info)
