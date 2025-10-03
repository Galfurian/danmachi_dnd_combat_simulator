"""
Spell offensive module for the simulator.

Defines offensive spells that deal damage to enemies, including
direct damage spells, area effects, and magical attacks.
"""

from typing import TYPE_CHECKING, Any, Literal

from actions.spells.base_spell import BaseSpell
from combat.damage import DamageComponent, roll_damage_components
from core.constants import GLOBAL_VERBOSE_LEVEL, ActionCategory, BonusType
from core.dice_parser import VarInfo
from core.logging import log_warning
from core.utils import cprint
from pydantic import Field

if TYPE_CHECKING:
    from character.main import Character


class SpellOffensive(BaseSpell):
    """Offensive spell that deals damage through magical attacks.

    This class represents spells designed to inflict damage on targets using
    magical energy. It includes attributes for damage components, optional
    effects, and methods for calculating and applying damage during combat.
    """

    action_type: Literal["SpellOffensive"] = "SpellOffensive"

    category: ActionCategory = ActionCategory.OFFENSIVE

    damage: list[DamageComponent] = Field(
        description="List of damage components for this ability",
    )

    def model_post_init(self, _: Any) -> None:
        """Validates fields after model initialization."""
        if not self.damage or not isinstance(self.damage, list):
            raise ValueError("damage must be a non-empty list of DamageComponent")

    # ============================================================================
    # SPELL ATTACK METHODS
    # ============================================================================

    def _execute_spell(
        self,
        actor: "Character",
        target: "Character",
        variables: list[VarInfo],
    ) -> bool:
        """
        Common logic for executing a spell after validation.

        Args:
            actor (Any):
                The character casting the spell.
            target (Any):
                The character being targeted.
            variables (list[VarInfo]):
                List of variables for expression evaluation.

        Returns:
            bool:
                True if action executed successfully, False otherwise.

        """

        # =====================================================================
        # ATTACK ROLL
        # =====================================================================

        # Get the spell attack bonus from the actor's stats.
        spell_attack_bonus = str(actor.get_spell_attack_bonus(self.level))

        # Get the attack modifier from effects.
        modifiers = actor.effects.get_base_modifier(BonusType.ATTACK)

        # Roll the attack.
        attack = self._roll_attack(actor, spell_attack_bonus, modifiers)

        if not attack.rolls:
            log_warning(
                "Attack roll failed, no rolls returned.",
                {"ability": self.name, "actor": actor.name},
            )
            return False

        # Prepare the roll message.
        attack_details = (
            f"rolled ({attack.description}) {attack.value} vs AC {target.AC}"
        )

        # =====================================================================
        # MISS
        # =====================================================================

        # If the attack misses or is a fumble, display the miss message and return.
        if (attack.value < target.AC) or attack.is_fumble():
            msg = (
                f"    ❌ {actor.colored_name} "
                f"casts {self.colored_name} on "
                f"{target.colored_name}"
            )
            if GLOBAL_VERBOSE_LEVEL == 1:
                msg += f"({attack_details}), "
            msg += f"{"fumbles" if attack.is_fumble() else "misses"}!"
            cprint(msg)
            return True

        # =====================================================================
        # DAMAGE CALCULATION
        # =====================================================================

        # Handle successful hit - calculate and apply damage
        total_damage, damage_details = roll_damage_components(
            actor=actor,
            target=target,
            damage_components=self.damage,
            variables=variables,
        )

        # =====================================================================
        # APPLY EFFECTS
        # =====================================================================

        # Apply the effects.
        effects_applied, effects_not_applied = self._common_apply_effects(
            actor=actor,
            target=target,
            effects=self.effects,
            variables=variables,
        )

        msg = (
            f"    🎯 {actor.colored_name} "
            f"casts {self.colored_name} on "
            f"{target.colored_name}"
        )

        # Display combat results with appropriate detail level
        if GLOBAL_VERBOSE_LEVEL == 0:
            msg += f" dealing {total_damage} damage"
            if effects_applied:
                msg += f" applying {self._effect_list_string(effects_applied)}"
            if effects_not_applied:
                msg += f" but fails to apply {self._effect_list_string(effects_not_applied)}"
            if target.is_dead():
                msg += f" defeating {target.colored_name}"
            msg += "."
        else:
            msg += f" rolled ({attack.description}) {attack.value} vs AC [yellow]{target.AC}[/] → "
            msg += "[magenta]crit![/]\n" if attack.is_critical() else "[green]hit![/]\n"
            msg += f"        Dealing {total_damage} damage to {target.colored_name} → "
            msg += " + ".join(damage_details) + ".\n"
            if effects_applied:
                msg += f"        {target.colored_name} gains "
                msg += self._effect_list_string(effects_applied)
                msg += ".\n"
            if effects_not_applied:
                msg += f"        {target.colored_name} doesn't gain "
                msg += self._effect_list_string(effects_not_applied)
                msg += ".\n"
            if target.is_dead():
                msg += f"        {target.colored_name} is defeated."
        cprint(msg)

        return True
