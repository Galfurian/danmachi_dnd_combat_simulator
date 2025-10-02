"""
Base attack module for the simulator.

Defines the base classes for character attacks, including weapon attacks
and natural attacks, with common functionality for execution and effects.
"""

from typing import Any

from actions.base_action import BaseAction, ValidActionEffect
from combat.damage import DamageComponent, roll_damage_components
from core.constants import GLOBAL_VERBOSE_LEVEL, ActionCategory, BonusType
from core.logging import log_warning
from core.utils import cprint
from effects.base_effect import EventResponse
from effects.event_system import DamageTakenEvent, HitEvent, LowHealthEvent
from pydantic import Field


class BaseAttack(BaseAction):
    """Base class for all attack actions in the combat system.

    This class provides a foundation for implementing various types of attacks,
    such as weapon attacks and natural attacks. It includes shared functionality
    like damage calculation, targeting, and serialization, while allowing
    subclasses to extend or override specific behavior.
    """

    category: ActionCategory = ActionCategory.OFFENSIVE

    attack_roll: str = Field(
        description="The attack roll expression (e.g., '1d20 + 5')",
    )
    damage: list[DamageComponent] = Field(
        description="List of damage components for the attack",
    )

    def model_post_init(self, _: Any) -> None:
        """Validates fields after model initialization."""
        if not self.attack_roll:
            raise ValueError("attack_roll must be a non-empty string")
        if not self.damage or not isinstance(self.damage, list):
            raise ValueError("damage must be a non-empty list of DamageComponent")
        # Remove spaces before and after '+' and '-'.
        self.attack_roll = self.attack_roll.replace(" +", "+").replace("+ ", "+")
        self.attack_roll = self.attack_roll.replace(" -", "-").replace("- ", "-")

    @property
    def colored_name(self) -> str:
        """
        Returns the colored name of the attack for display purposes.
        """
        return f"[bold blue]{self.name}[/]"

    # ============================================================================
    # COMBAT EXECUTION METHODS
    # ============================================================================

    def execute(self, actor: Any, target: Any) -> bool:
        """Execute this attack against a target.

        Args:
            actor (Any): The character performing the attack.
            target (Any): The character being attacked.

        Returns:
            bool: True if attack was executed successfully, False on validation errors.

        """
        from character.main import Character

        # =====================================================================
        # 1. VALIDATION AND PREPARATION
        # =====================================================================

        if not isinstance(actor, Character):
            raise ValueError("The actor must be a Character instance.")
        if not isinstance(target, Character):
            raise ValueError("The target must be a Character instance.")

        # Check if the ability is on cooldown.
        if actor.actions.is_on_cooldown(self):
            return False

        # =====================================================================
        # 2. ATTACK ROLL (TO-HIT, CRIT, FUMBLE)
        # =====================================================================
        """Perform an attack roll using the same logic as BaseAttack."""

        # Get the attack modifier from effects.
        modifiers = actor.effects.get_base_modifier(BonusType.ATTACK)

        if not all(isinstance(modifier, str) for modifier in modifiers):
            log_warning(
                "Modifiers for attack roll must be strings.",
                {"ability": self.name, "modifiers": modifiers},
            )
            return False

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

        # =============================
        # 3a. Roll the base damage
        # =============================

        # Roll the base damage.
        damage, damage_details = roll_damage_components(
            actor,
            target,
            self.damage,
        )
        # If the attack is a critical hit, roll damage another time.
        if attack.is_critical():
            crit_damage, crit_details = roll_damage_components(
                actor, target, self.damage
            )
            damage += crit_damage
            damage_details += crit_details

        # =============================
        # 3b. Get On-Hit events.
        # =============================

        # Roll damage from ON_HIT events.
        event_damage, event_damage_details = roll_damage_components(
            actor,
            target,
            event_damage_bonuses,
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
            actor,
            target,
            modifiers,
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

        msg = (
            f"    🎯 {actor.colored_name} "
            f"attacks {target.colored_name} with "
            f"{self.colored_name} "
        )

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
        elif GLOBAL_VERBOSE_LEVEL >= 1:
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

    # ============================================================================
    # DAMAGE CALCULATION METHODS
    # ============================================================================

    def get_damage_expr(self, actor: Any) -> str:
        """
        Returns the damage expression with variables substituted.

        Args:
            actor (Any):
                The character performing the action.

        Returns:
            str:
                Complete damage expression with variables replaced by values.

        """
        return super()._common_get_damage_expr(actor, self.damage)

    def get_min_damage(self, actor: Any) -> int:
        """
        Returns the minimum possible damage value for the attack.

        Args:
            actor (Any):
                The character performing the action.

        Returns:
            int:
                Minimum total damage across all damage components.

        """
        return super()._common_get_min_damage(actor, self.damage)

    def get_max_damage(self, actor: Any) -> int:
        """Returns the maximum possible damage value for the attack.

        Args:
            actor (Any):
                The character performing the action.

        Returns:
            int:
                Maximum total damage across all damage components.

        """
        return super()._common_get_max_damage(actor, self.damage)


def deserialize_attack(data: dict[str, Any]) -> BaseAttack | None:
    """
    Deserialize a dictionary into the appropriate BaseAttack subclass.

    Args:
        data (dict[str, Any]):
            The dictionary representation of the attack.

    Returns:
        BaseAttack:
            An instance of the appropriate BaseAttack subclass.

    Raises:
        ValueError:
            If the action class is unknown or missing.

    """
    from actions.attacks.natural_attack import NaturalAttack
    from actions.attacks.weapon_attack import WeaponAttack

    action_type = data.get("action_type")

    if action_type == "WeaponAttack":
        cprint("Deserializing WeaponAttack: {data}", style="yellow")
        return WeaponAttack(**data)
    if action_type == "NaturalAttack":
        cprint("Deserializing NaturalAttack: {data}", style="green")
        return NaturalAttack(**data)

    return None
