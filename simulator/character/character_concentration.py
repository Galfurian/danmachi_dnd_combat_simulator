"""
Character concentration management module.

This module handles concentration tracking for D&D 5e-style spellcasting,
tracking concentration by spell (not by individual effect instances).
"""

from typing import Any, Dict, List, Optional
from core.utils import cprint
from actions.spells import Spell


class ConcentrationSpell:
    """Represents a concentration spell and all its active effects across targets."""

    def __init__(self, spell: Spell, caster: Any, mind_level: int):
        self.spell: Spell = spell
        self.caster: Any = caster
        self.mind_level: int = mind_level
        self.targets: List[Any] = []  # Characters affected by this concentration spell
        self.active_effects: List[Any] = []  # ActiveEffect instances for this spell

    def add_target(self, target: Any, active_effect: Any) -> None:
        """Add a target and its associated active effect to this concentration spell."""
        if target not in self.targets:
            self.targets.append(target)
        self.active_effects.append(active_effect)

    def remove_target(self, target: Any) -> None:
        """Remove a target and its effects from this concentration spell."""
        if target in self.targets:
            self.targets.remove(target)
        # Remove associated effects for this target
        self.active_effects = [ae for ae in self.active_effects if ae.target != target]

    def is_empty(self) -> bool:
        """Check if this concentration spell has no active effects."""
        return len(self.active_effects) == 0


class CharacterConcentration:
    """Manages concentration spells for a character (typically a spellcaster)."""

    def __init__(self, character_ref):
        """Initialize with reference to parent Character object."""
        self._character = character_ref
        self.concentration_spells: Dict[str, ConcentrationSpell] = (
            {}
        )  # spell_name -> ConcentrationSpell

    def can_add_concentration_spell(self) -> bool:
        """Check if we can add another concentration spell without exceeding the limit."""
        return len(self.concentration_spells) < self._character.CONCENTRATION_LIMIT

    def add_concentration_effect(
        self, spell: Spell, target: Any, active_effect: Any, mind_level: int
    ) -> bool:
        """
        Add a concentration effect. If the spell already exists, add to existing concentration.
        If not, create new concentration spell entry.

        Returns:
            bool: True if the effect was added successfully
        """
        spell_key = spell.name.lower()

        # If this spell is already being concentrated on, just add the new target/effect
        if spell_key in self.concentration_spells:
            conc_spell = self.concentration_spells[spell_key]
            conc_spell.add_target(target, active_effect)
            return True

        # New concentration spell - check if we have room
        if not self.can_add_concentration_spell():
            # Need to drop oldest concentration spell
            self.drop_oldest_concentration_spell()

        # Create new concentration spell entry
        conc_spell = ConcentrationSpell(spell, self._character, mind_level)
        conc_spell.add_target(target, active_effect)
        self.concentration_spells[spell_key] = conc_spell

        return True

    def remove_concentration_effect(self, target: Any, active_effect: Any) -> None:
        """Remove a concentration effect when it expires or is dispelled."""
        for spell_key, conc_spell in list(self.concentration_spells.items()):
            if active_effect in conc_spell.active_effects:
                conc_spell.remove_target(target)

                # If no more effects for this spell, remove the concentration spell entirely
                if conc_spell.is_empty():
                    del self.concentration_spells[spell_key]
                break

    def drop_oldest_concentration_spell(self) -> None:
        """Drop the oldest concentration spell to make room for a new one."""
        if not self.concentration_spells:
            return

        # Get the first (oldest) concentration spell
        oldest_spell_key = next(iter(self.concentration_spells))
        oldest_conc_spell = self.concentration_spells[oldest_spell_key]

        # Show message about breaking concentration
        target_names = [target.name for target in oldest_conc_spell.targets]
        if len(target_names) == 1:
            cprint(
                f"    :no_entry: [bold yellow]{oldest_conc_spell.spell.name}[/] concentration broken on [bold]{target_names[0]}[/] (concentration limit reached)."
            )
        else:
            targets_str = ", ".join(target_names)
            cprint(
                f"    :no_entry: [bold yellow]{oldest_conc_spell.spell.name}[/] concentration broken on [bold]{targets_str}[/] (concentration limit reached)."
            )

        # Remove all effects for this concentration spell
        for active_effect in oldest_conc_spell.active_effects:
            active_effect.target.effects_module.remove_effect(active_effect)

        # Remove the concentration spell
        del self.concentration_spells[oldest_spell_key]

    def break_concentration(self, spell: Optional[Spell] = None) -> bool:
        """
        Break concentration on a specific spell or all concentration spells.

        Args:
            spell: Specific spell to break concentration on. If None, breaks all.

        Returns:
            bool: True if any concentration was broken
        """
        if spell:
            # Break specific spell
            spell_key = spell.name.lower()
            if spell_key in self.concentration_spells:
                conc_spell = self.concentration_spells[spell_key]

                # Show message
                target_names = [target.name for target in conc_spell.targets]
                if len(target_names) == 1:
                    cprint(
                        f"    :no_entry: [bold yellow]{spell.name}[/] concentration broken on [bold]{target_names[0]}[/]."
                    )
                else:
                    targets_str = ", ".join(target_names)
                    cprint(
                        f"    :no_entry: [bold yellow]{spell.name}[/] concentration broken on [bold]{targets_str}[/]."
                    )

                # Remove all effects for this spell
                for active_effect in conc_spell.active_effects:
                    active_effect.target.effects_module.remove_effect(active_effect)

                # Remove the concentration spell
                del self.concentration_spells[spell_key]
                return True
        else:
            # Break all concentration
            if self.concentration_spells:
                spell_info = []
                for conc_spell in self.concentration_spells.values():
                    target_names = [target.name for target in conc_spell.targets]
                    spell_info.append((conc_spell.spell.name, target_names))

                    # Remove all effects
                    for active_effect in conc_spell.active_effects:
                        active_effect.target.effects_module.remove_effect(active_effect)

                # Show message
                if len(spell_info) == 1:
                    spell_name, target_names = spell_info[0]
                    targets_str = ", ".join(target_names)
                    cprint(
                        f"    :no_entry: [bold yellow]{spell_name}[/] concentration broken on [bold]{targets_str}[/]."
                    )
                else:
                    spell_descriptions = [
                        f"{name} on {', '.join(targets)}"
                        for name, targets in spell_info
                    ]
                    cprint(
                        f"    :no_entry: All concentration broken: [bold yellow]{'; '.join(spell_descriptions)}[/]."
                    )

                # Clear all concentration
                self.concentration_spells.clear()
                return True

        return False

    def get_concentration_count(self) -> int:
        """Get the number of concentration spells currently active."""
        return len(self.concentration_spells)

    def get_concentration_spells(self) -> List[ConcentrationSpell]:
        """Get a list of all active concentration spells."""
        return list(self.concentration_spells.values())
