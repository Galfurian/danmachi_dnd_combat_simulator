from typing import Any, TYPE_CHECKING

from combat.damage import DamageComponent
from core.utils import VarInfo, cprint, roll_and_describe
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from character.main import Character
    from effects.damage_over_time_effect import DamageOverTimeEffect
    from effects.healing_over_time_effect import HealingOverTimeEffect
    from effects.incapacitating_effect import IncapacitatingEffect
    from effects.modifier_effect import ModifierEffect
    from effects.trigger_effect import (
        TriggerEvent,
        TriggerType,
        TriggerEffect,
        ValidTriggerEffect,
    )


class Effect(BaseModel):
    """
    Base class for all game effects that can be applied to characters.

    Effects can modify character stats, deal damage over time, provide healing,
    or trigger special behaviors under certain conditions.
    """

    name: str = Field(
        description="The name of the effect.",
    )
    description: str = Field(
        "",
        description="A brief description of the effect.",
    )
    duration: int | None = Field(
        default=None,
        description=(
            "The duration of the effect in turns. "
            "None for permanent effects, 0 for instant effects."
        ),
    )

    @property
    def display_name(self) -> str:
        return self.name.lower().capitalize()

    @property
    def color(self) -> str:
        """Returns the color string associated with this effect type."""
        return "dim white"  # Default fallback

    @property
    def colored_name(self) -> str:
        """Returns the effect name with color formatting applied."""
        return self.colorize(self.display_name)

    @property
    def emoji(self) -> str:
        """Returns the emoji associated with this effect type."""
        return "❔"  # Default fallback

    def colorize(self, message: str) -> str:
        """Applies effect color formatting to a message."""
        return f"[{self.color}]{message}[/]"

    def is_permanent(self) -> bool:
        """Check if the effect is permanent (i.e., has no duration limit).

        Returns:
            bool: True if the effect is permanent (None duration) or instant (0 duration), False otherwise.

        """
        return self.duration is None or self.duration <= 0

    def can_apply(
        self,
        actor: "Character",
        target: "Character",
    ) -> bool:
        """
        Check if the effect can be applied to the target.

        Args:
            actor (Character):
                The character applying the effect.
            target (Character):
                The character receiving the effect.

        Returns:
            bool:
                True if the effect can be applied, False otherwise.

        """
        if actor.is_dead():
            cprint(f"    [bold red]{actor.name} is dead and cannot apply effects![/]")
            return False
        if target.is_dead():
            cprint(
                f"    [bold red]{target.name} is dead and cannot receive effects![/]"
            )
            return False
        # Check if the target is already affected by the same modifiers.
        return target.can_add_effect(
            actor,
            self,
            actor.get_expression_variables(),
        )


class ActiveEffect(BaseModel):
    """
    Represents an active effect applied to a character, including its source,
    target, effect details, mind level, and duration.
    """

    source: "Character" = Field(
        description="The source of the effect (the caster)",
    )
    target: "Character" = Field(
        description="The target of the effect (the recipient)",
    )
    effect: Effect = Field(
        description="The effect being applied",
    )
    duration: int | None = Field(
        default=None,
        description="Remaining duration in turns, None for indefinite effects",
    )
    variables: list[VarInfo] = Field(
        default_factory=list,
        description="List of variable info for dynamic calculations",
    )

    def turn_update(self) -> None:
        """
        Update the effect for the current turn by calling the effect's
        turn_update method.

        """

        if isinstance(self.effect, DamageOverTimeEffect):
            # Calculate the damage amount using the provided expression.
            outcome = roll_and_describe(
                self.effect.damage.damage_roll,
                self.variables,
            )
            if outcome.value < 0:
                raise ValueError(
                    "Damage value must be non-negative for DamageOverTimeEffect"
                    f" '{self.effect.name}', got {outcome.value}."
                )
            # Apply the damage to the target.
            base, adjusted, taken = self.target.take_damage(
                outcome.value, self.effect.damage.damage_type
            )
            # If the damage value is positive, print the damage message.
            dot_str = f"    {self.effect.emoji} "
            dot_str += self.target.colored_name + " takes "
            # Create a damage string for display.
            dot_str += f"{self.effect.damage.color_roll(taken)} "
            # If the base damage differs from the adjusted damage (due to resistances),
            # include the original and adjusted values in the damage string.
            if base != adjusted:
                dot_str += f"[dim](reduced: {base} → {adjusted})[/] "
            # Append the rolled damage expression to the damage string.
            dot_str += f"({outcome.description})"
            # Print the damage string.
            cprint(dot_str)
            # If the target is defeated, print a message.
            if not self.target.is_alive():
                cprint(f"    [bold red]{self.target.name} has been defeated![/]")

        elif isinstance(self.effect, HealingOverTimeEffect):

            # Calculate the heal amount using the provided expression.
            outcome = roll_and_describe(
                self.effect.heal_per_turn,
                self.variables,
            )
            # Assert that the heal value is a positive integer.
            if outcome.value < 0:
                raise ValueError(
                    "Heal value must be non-negative for HealingOverTimeEffect"
                    f" '{self.effect.name}', got {outcome.value}."
                )
            # Apply the heal to the target.
            hot_value = self.target.heal(outcome.value)
            # If the heal value is positive, print the heal message.
            message = f"    {self.effect.emoji} "
            message += self.target.char_type.colorize(self.target.name)
            message += (
                f" heals for {hot_value} ([white]{outcome.description}[/]) hp from "
            )
            message += self.effect.colored_name + "."
            cprint(message)

        elif isinstance(self.effect, IncapacitatingEffect):

            if not self.duration:
                raise ValueError("Effect duration is not set.")
            if self.duration <= 0:
                raise ValueError("Effect duration is already zero or negative.")
            self.duration -= 1

        elif isinstance(self.effect, ModifierEffect):

            pass

        elif isinstance(self.effect, TriggerEffect):

            raise ValueError("This should not be called.")

    def model_post_init(self, _) -> None:
        if not isinstance(self.effect, Effect):
            raise ValueError("Effect must be an Effect instance.")
        if self.duration is not None and self.duration < 0:
            raise ValueError("Duration must be a non-negative integer or None.")
        if not all(isinstance(var, VarInfo) for var in self.variables):
            raise ValueError("All items in variables must be VarInfo instances.")


class ActiveTrigger(ActiveEffect):
    """
    Represents an active trigger effect with additional state for tracking
    trigger usage, cooldowns, and activation status.
    """

    triggers_used: int = Field(
        default=0,
        description="Number of times the trigger has been activated",
    )
    cooldown_remaining: int = Field(
        default=0,
        description="Remaining cooldown turns before trigger can activate again",
    )
    has_triggered_this_turn: bool = Field(
        default=False,
        description="Whether the trigger has activated this turn",
    )

    @property
    def trigger(self) -> "TriggerEffect":
        """
        Get the effect as a TriggerEffect (narrowed type for clarity).

        Raises:
            TypeError:
                If the effect is not a TriggerEffect.

        Returns:
            TriggerEffect:
                The effect cast as a TriggerEffect.
        """
        if not isinstance(self.effect, TriggerEffect):
            raise TypeError(f"Expected TriggerEffect, got {type(self.effect)}")
        return self.effect

    def check_trigger(self, event: "TriggerEvent") -> bool:
        """
        Check if the trigger condition is met for the given event.

        Args:
            event (TriggerEvent):
                The event to check against the trigger condition.

        Returns:
            bool:
                True if the trigger condition is met and the trigger can
                activate, False otherwise.

        """
        # Check if we have exceeded max triggers.
        if self.exceeded_max_triggers():
            return False
        # Check if we're on cooldown.
        if self.is_in_cooldown():
            return False
        # If we've already triggered this turn.
        if self.already_triggered_this_turn():
            return False
        # Finally check the trigger condition itself.
        return self.trigger.trigger_condition.is_met(event)

    def activate_trigger(
        self,
    ) -> tuple[list[DamageComponent], list["ValidTriggerEffect"]]:
        """
        Activate the trigger and return effects and damage bonuses.

        Returns:
            tuple[list[DamageComponent], list[ValidTriggerEffect]]:
                Damage bonuses and effects with mind levels.

        """

        if not self.trigger.damage_bonus:
            raise ValueError("TriggerEffect must have a damage_bonus defined.")
        if not self.trigger.trigger_effects:
            raise ValueError("TriggerEffect must have trigger_effects defined.")

        # Increment triggers used.
        self.increment_triggers_used()
        # Mark as triggered this turn if applicable.
        self.mark_as_triggered_this_turn()
        # Start the cooldown if applicable.
        self.start_cooldown()

        return self.trigger.damage_bonus, self.trigger.trigger_effects

    def is_cooldown_defined(self) -> bool:
        """
        Check if the trigger has a defined cooldown.

        Returns:
            bool:
                True if the trigger has a defined cooldown, False otherwise.
        """
        if self.trigger.cooldown_turns is None:
            return False
        return self.trigger.cooldown_turns > 0

    def is_in_cooldown(self) -> bool:
        """
        Check if the trigger is currently on cooldown.

        Returns:
            bool:
                True if the trigger is on cooldown, False otherwise.
        """
        if self.is_cooldown_defined():
            return self.cooldown_remaining > 0
        return False

    def start_cooldown(self) -> None:
        """
        Start the cooldown of the trigger by setting it to the defined cooldown
        turns.
        """
        if self.is_cooldown_defined():
            self.cooldown_remaining = self.trigger.cooldown_turns

    def decrement_cooldown(self) -> None:
        """
        Decrement the cooldown counter by one turn if it's greater than zero.
        """
        if self.is_cooldown_defined() and self.cooldown_remaining > 0:
            self.cooldown_remaining -= 1

    def is_turn_based_trigger(self) -> bool:
        """
        Check if the trigger is turn-based (i.e., activates on turn start or
        end).

        Returns:
            bool:
                True if the trigger is turn-based, False otherwise.
        """

        if not self.trigger.trigger_condition.trigger_type:
            return False
        return self.trigger.trigger_condition.trigger_type in [
            TriggerType.ON_TURN_START,
            TriggerType.ON_TURN_END,
        ]

    def mark_as_triggered_this_turn(self) -> None:
        """
        Mark the trigger as having activated this turn.
        """
        if self.is_turn_based_trigger():
            self.has_triggered_this_turn = True

    def clear_triggered_this_turn(self) -> None:
        """
        Clear the flag indicating the trigger has activated this turn.
        """
        if self.is_turn_based_trigger():
            self.has_triggered_this_turn = False

    def already_triggered_this_turn(self) -> bool:
        """
        Check if the trigger has already activated this turn.

        Returns:
            bool:
                True if the trigger has activated this turn, False otherwise.
        """
        return self.is_turn_based_trigger() and self.has_triggered_this_turn

    def increment_triggers_used(self) -> None:
        """
        Increment the count of how many times the trigger has been activated.
        """
        if self.trigger.max_triggers is not None:
            self.triggers_used += 1

    def exceeded_max_triggers(self) -> bool:
        """
        Check if the trigger has exceeded its maximum allowed activations.

        Returns:
            bool:
                True if the maximum number of triggers has been reached, False
                otherwise.
        """
        if self.trigger.max_triggers is None:
            return False
        return self.triggers_used >= self.trigger.max_triggers
