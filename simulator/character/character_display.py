"""
Character display module for the simulator.

Provides display and UI functionality for characters, including
health bars, status displays, and character information formatting.
"""

from typing import Any

from core.utils import make_bar


class CharacterDisplay:
    """
    Handles display, formatting, and UI functionality for Character objects.
    
    Attributes:
        owner (Any):
            The Character instance that this display is associated with.

    """

    def __init__(self, owner: Any) -> None:
        """
        Initialize the CharacterDisplay with its owner.

        Args:
            owner (Any):
                The Character instance that this display is associated with.

        """
        self.owner = owner

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
        if self.owner.effects_module.active_effects:
            for e in self.owner.effects_module.active_effects:
                color = e.effect.color
                # Truncate long effect names and show duration more compactly
                effect_name = (
                    e.effect.name[:12] + "..."
                    if len(e.effect.name) > 15
                    else e.effect.name
                )
                effects_list.append(
                    f"[{color}]{effect_name}[/]({e.duration if e.duration else '∞'})"
                )

        # Build status line with better spacing
        hp_bar = (
            make_bar(self.owner.stats.hp, self.owner.HP_MAX, color="green", length=8)
            if show_bars
            else ""
        )

        # Use dynamic name width based on name length, but cap it
        name_width = min(max(len(self.owner.name), 8), 16)
        status = (
            f"{self.owner.char_type.emoji} [bold]{self.owner.name:<{name_width}}[/] "
        )

        # Show AC only for player and allies (not enemies) with yellow color
        if show_ac:
            status += f"| [yellow]AC:{self.owner.AC:>2}[/] "

        # Build HP display based on parameters with green color
        hp_display = ""
        if show_numbers and show_bars:
            hp_display = (
                f"| [green]HP:{self.owner.stats.hp:>3}/{self.owner.HP_MAX}[/]{hp_bar} "
            )
        elif show_numbers:
            hp_display = f"| [green]HP:{self.owner.stats.hp:>3}/{self.owner.HP_MAX}[/] "
        elif show_bars:
            hp_display = f"| [green]HP:[/]{hp_bar} "
        else:
            # Default to showing numbers if neither is specified
            hp_display = f"| [green]HP:{self.owner.stats.hp:>3}/{self.owner.HP_MAX}[/] "
        status += hp_display

        if self.owner.MIND_MAX > 0:
            mind_bar = (
                make_bar(
                    self.owner.stats.mind,
                    self.owner.MIND_MAX,
                    color="blue",
                    length=8,
                )
                if show_bars
                else ""
            )

            # Build MP display based on parameters with blue color
            mp_display = ""
            if show_numbers and show_bars:
                mp_display = f"| [blue]MP:{self.owner.stats.mind:>3}/{self.owner.MIND_MAX}[/]{mind_bar} "
            elif show_numbers:
                mp_display = (
                    f"| [blue]MP:{self.owner.stats.mind:>3}/{self.owner.MIND_MAX}[/] "
                )
            elif show_bars:
                mp_display = f"| [blue]MP:[/]{mind_bar} "
            else:
                # Default to showing numbers if neither is specified
                mp_display = (
                    f"| [blue]MP:{self.owner.stats.mind:>3}/{self.owner.MIND_MAX}[/] "
                )
            status += mp_display

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
        if not self.owner.effects_module.active_effects:
            return "No active effects"

        effects_info = []
        for e in self.owner.effects_module.active_effects:
            color = e.effect.color
            effects_info.append(
                f"  [{color}]{e.effect.name}[/] ({e.duration} turns): {e.effect.description}"
            )

        return "Active Effects:\n" + "\n".join(effects_info)
