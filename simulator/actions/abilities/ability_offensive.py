"""
Ability offensive module for the simulator.

Defines offensive abilities that deal damage to enemies, including
special attacks, area effects, and other combat abilities.
"""

from typing import TYPE_CHECKING, Any, Literal

from actions.abilities.base_ability import BaseAbility
from actions.base_action import ValidActionEffect
from combat.damage import DamageComponent, roll_damage_components
from core.constants import GLOBAL_VERBOSE_LEVEL, ActionCategory, BonusType
from core.dice_parser import VarInfo
from core.logging import log_warning
from core.utils import cprint
from effects.base_effect import EventResponse
from effects.event_system import DamageTakenEvent, HitEvent, LowHealthEvent
from pydantic import Field

if TYPE_CHECKING:
    from character.main import Character


class AbilityOffensive(BaseAbility):

    action_type: Literal["AbilityOffensive"] = "AbilityOffensive"

    category: ActionCategory = ActionCategory.OFFENSIVE

    attack_roll: str = Field(
        default="",
        description="Expression for attack roll, e.g. '1d20 + 5'",
    )
    damage: list[DamageComponent] = Field(
        description="List of damage components for this ability",
    )

    def model_post_init(self, _: Any) -> None:
        """Validates fields after model initialization."""
        if not self.damage or not isinstance(self.damage, list):
            raise ValueError("damage must be a non-empty list of DamageComponent")
        # Remove spaces before and after '+' and '-'.
        self.attack_roll = self.attack_roll.replace(" +", "+").replace("+ ", "+")
        self.attack_roll = self.attack_roll.replace(" -", "-").replace("- ", "-")

    @property
    def colored_name(self) -> str:
        """
        Returns the ability name with color formatting for display.
        """
        return f"[bold blue]{self.name}[/]"

    def _execute_ability(
        self,
        actor: "Character",
        target: "Character",
        variables: list[VarInfo],
    ) -> bool:
        """
        Abstract method to be implemented by subclasses for specific ability execution.

        Args:
            actor (Character):
                The character performing the action.
            target (Character):
                The character being targeted.
            variables (list[VarInfo]):
                The variables available for the action execution.

        Returns:
            bool:
                True if action executed successfully, False otherwise.
        """
        # =====================================================================
        # ATTACK ROLL
        # =====================================================================

        # Get the attack modifier from effects.
        modifiers = actor.effects.get_base_modifier(BonusType.ATTACK)

        # Roll the attack.
        attack = self._roll_attack(actor, self.attack_roll, modifiers)

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

        # Determine if the attack hits, crits, or fumbles.
        if (attack.value < target.AC) or attack.is_fumble():
            msg = (
                f"    ❌ {actor.colored_name} uses {self.colored_name} on "
                f"{target.colored_name}, {attack_details}, but "
            )
            msg += f"{"fumbles" if attack.is_fumble() else "misses"}!"
            cprint(msg)
            return True

        # Prepare a list to hold all the effects to apply.
        effects_to_apply: list[ValidActionEffect] = []

        # Add the base effects of the ability to the list of effects to apply.
        effects_to_apply.extend(self.effects)

        # Get any on-hit triggers from effects.
        event_responses: list[EventResponse] = actor.effects.on_event(
            HitEvent(
                source=actor,
                target=target,
            )
        )
        # Collect all the new effects from the event responses.
        event_damage_bonuses: list[DamageComponent] = []
        for response in event_responses:
            for effect in response.new_effects:
                if isinstance(effect, ValidActionEffect):
                    effects_to_apply.append(effect)
            event_damage_bonuses.extend(response.damage_bonus)

        # =====================================================================
        # 3. DAMAGE CALCULATION (INCLUDING CRIT/FUMBLE MODIFIERS)
        # =====================================================================

        variables = actor.get_expression_variables()

        # =============================
        # 3a. Roll the base damage
        # =============================

        # Roll the base damage.
        damage, damage_details = roll_damage_components(
            actor=actor,
            target=target,
            damage_components=self.damage,
            variables=variables,
        )
        # If the attack is a critical hit, roll damage another time.
        if attack.is_critical():
            crit_damage, crit_details = roll_damage_components(
                actor=actor,
                target=target,
                damage_components=self.damage,
                variables=variables,
            )
            damage += crit_damage
            damage_details += crit_details

        # =============================
        # 3b. Get On-Hit events.
        # =============================

        # Roll damage from ON_HIT events.
        event_damage, event_damage_details = roll_damage_components(
            actor=actor,
            target=target,
            damage_components=event_damage_bonuses,
            variables=variables,
        )
        # Add the ON_HIT event damage.
        damage += event_damage
        damage_details += event_damage_details

        # =============================
        # 3c. Add bonus damage.
        # =============================

        # Get all damage modifiers from effects.
        modifiers = actor.effects.get_damage_modifier()
        if not all(isinstance(modifier, str) for modifier in modifiers):
            log_warning(
                "Modifiers for damage roll must be strings.",
                {"ability": self.name, "modifiers": modifiers},
            )
            return False
        # Roll the bonus damage.
        bonus_damage, bonus_damage_details = roll_damage_components(
            actor=actor,
            target=target,
            damage_components=modifiers,
            variables=variables,
        )
        # Sum up the base damage.
        damage += bonus_damage
        damage_details += bonus_damage_details

        # =====================================================================
        # OTHER EVENTS
        # =====================================================================

        event_responses = target.effects.on_event(
            DamageTakenEvent(
                source=actor,
                target=target,
                amount=damage,
            )
        )
        for response in event_responses:
            for effect in response.new_effects:
                if isinstance(effect, ValidActionEffect):
                    effects_to_apply.append(effect)

        event_responses = target.effects.on_event(
            LowHealthEvent(
                source=actor,
            )
        )
        for response in event_responses:
            for effect in response.new_effects:
                if isinstance(effect, ValidActionEffect):
                    effects_to_apply.append(effect)

        # =====================================================================
        # 4. EFFECT APPLICATION
        # =====================================================================

        # Apply the effects.
        effects_applied, effects_not_applied = self._common_apply_effects(
            actor,
            target,
            effects_to_apply,
        )

        # =====================================================================
        # 5. RESULT DISPLAY AND LOGGING
        # =====================================================================

        msg = f"    🔥 {actor.colored_name} "
        msg += f"uses {self.colored_name} "
        msg += f"on {target.colored_name}"

        if GLOBAL_VERBOSE_LEVEL == 0:
            msg += f" dealing {damage} damage"
            if attack.is_critical():
                msg += " (critical hit!)"
            if effects_applied:
                msg += f" applying {self._effect_list_string(effects_applied)}"
            if effects_not_applied:
                msg += f" but fails to apply {self._effect_list_string(effects_not_applied)}"
            if not target.is_alive():
                msg += f" defeating {target.colored_name}"
            msg += "."
        else:
            msg += f"({attack_details}), "
            if damage_details:
                msg += f" dealing {damage} damage → "
                msg += " + ".join(damage_details)
            else:
                msg += f" dealing {damage} damage"
                msg += " (fumble!)"
            if attack.is_critical():
                msg += " (critical hit!)"
            msg += ".\n"
            if effects_applied:
                msg += f"        {target.colored_name} gains "
                msg += self._effect_list_string(effects_applied)
                msg += ".\n"
            if effects_not_applied:
                msg += f"        {target.colored_name} doesn't gain "
                msg += self._effect_list_string(effects_not_applied)
                msg += ".\n"
            if not target.is_alive():
                msg += f"        {target.colored_name} is defeated."

        cprint(msg)

        for response in event_responses:
            cprint(f"    ⚡ {response.message}")

        return True
