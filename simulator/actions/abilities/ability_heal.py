"""
Ability heal module for the simulator.

Defines healing abilities that restore hit points to allies, including
various healing spells and abilities with different effects and ranges.
"""

from typing import TYPE_CHECKING, Any, Literal

from actions.abilities.base_ability import BaseAbility
from actions.base_action import ValidActionEffect
from core.constants import GLOBAL_VERBOSE_LEVEL, ActionCategory
from core.dice_parser import (
    VarInfo,
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    roll_and_describe,
    substitute_variables,
)
from core.utils import cprint
from effects.event_system import HealEvent
from pydantic import Field

if TYPE_CHECKING:
    from character.main import Character


class AbilityHeal(BaseAbility):
    """Represents abilities that restore hit points to targets during combat."""

    action_type: Literal["AbilityHeal"] = "AbilityHeal"

    category: ActionCategory = ActionCategory.HEALING

    heal_roll: str = Field(
        description="Expression for healing amount, e.g. '1d8 + 3'",
    )

    def model_post_init(self, _: Any) -> None:
        """Validates fields after model initialization."""
        if not self.heal_roll or not isinstance(self.heal_roll, str):
            raise ValueError("heal_roll must be a non-empty string.")
        # Remove spaces before and after '+' and '-'.
        self.heal_roll = self.heal_roll.replace(" +", "+").replace("+ ", "+")
        self.heal_roll = self.heal_roll.replace(" -", "-").replace("- ", "-")

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
        # Roll healing amount.
        heal = roll_and_describe(expr=self.heal_roll, variables=variables)
        # Apply healing to target.
        actual_healing = target.heal(heal.value)

        # Gather the effects to apply.
        effects_to_apply: list[ValidActionEffect] = []

        # Add the base effects of the ability to the list of effects to apply.
        effects_to_apply.extend(self.effects)

        # Activate events from healing.
        event_responses = target.on_event(
            HealEvent(
                source=actor,
                target=target,
                amount=actual_healing,
            )
        )
        for response in event_responses:
            for new_effect in response.new_effects:
                if isinstance(new_effect, ValidActionEffect):
                    effects_to_apply.append(new_effect)

        # Apply the effects.
        effects_applied, effects_not_applied = self._common_apply_effects(
            actor,
            target,
            effects_to_apply,
        )

        # Display the outcome.
        msg = f"    ✨ {actor.colored_name} "
        msg += f"uses {self.colored_name} "
        msg += f"on {target.colored_name}"

        if GLOBAL_VERBOSE_LEVEL == 0:
            msg += f" healing {actual_healing} 💚"
            if effects_applied:
                msg += f" applying {self._effect_list_string(effects_applied)}"
            if effects_not_applied:
                msg += f" but fails to apply {self._effect_list_string(effects_not_applied)}"
            msg += "."
        else:
            if actual_healing != heal.value:
                msg += f" healing {actual_healing} 💚 (rolled {heal.value}, capped at max 💚)"
            else:
                msg += f" healing {actual_healing} 💚 → {heal.description}"
            msg += ".\n"

            if effects_applied:
                msg += f"        {target.colored_name} gains "
                msg += self._effect_list_string(effects_applied)
                msg += ".\n"

            if effects_not_applied:
                msg += f"        {target.colored_name} doesn't gain "
                msg += self._effect_list_string(effects_not_applied)
                msg += ".\n"

        cprint(msg)

        return True
