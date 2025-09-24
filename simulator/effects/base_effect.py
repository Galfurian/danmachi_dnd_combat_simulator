from typing import Any, TYPE_CHECKING

from combat.damage import DamageComponent
from core.constants import BonusType
from core.utils import VarInfo
from pydantic import BaseModel, Field, model_validator

if TYPE_CHECKING:
    from effects.trigger_effect import TriggerEvent, TriggerEffect, ValidTriggerEffect


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

    def turn_update(
        self,
        effect: "ActiveEffect",
    ) -> None:
        """Update the effect for the current turn.

        Args:
            effect (ActiveEffect):
                The active effect instance containing actor, target, and
                variables.

        """
        raise NotImplementedError(
            f"turn_update not implemented for effect {self.name}",
        )

    def is_permanent(self) -> bool:
        """Check if the effect is permanent (i.e., has no duration limit).

        Returns:
            bool: True if the effect is permanent (None duration) or instant (0 duration), False otherwise.

        """
        return self.duration is None or self.duration <= 0

    def can_apply(self, actor: Any, target: Any) -> bool:
        """Check if the effect can be applied to the target.

        Args:
            actor (Any): The character applying the effect.
            target (Any): The character receiving the effect.

        Returns:
            bool: True if the effect can be applied, False otherwise.

        """
        try:
            if not actor:
                print(
                    f"Actor cannot be None when checking if effect {self.name} can be applied",
                )
                return False

            if not target:
                print(
                    f"Target cannot be None when checking if effect {self.name} can be applied",
                )
                return False

            return False  # Base implementation

        except Exception as e:
            print(
                f"Error checking if effect {self.name} can be applied: {e!s}",
                e,
            )
            return False


class Modifier(BaseModel):
    """
    Handles different types of modifiers that can be applied to characters.

    Modifiers represent bonuses or penalties to various character attributes
    such as HP, AC, damage, or other stats.
    """

    bonus_type: BonusType = Field(
        description="The type of bonus the modifier applies.",
    )
    value: Any = Field(
        description=(
            "The value of the modifier. Can be an integer, string expression, or DamageComponent."
        ),
    )

    @model_validator(mode="after")
    def check_bonus_type(self) -> Any:
        from combat.damage import DamageComponent

        if self.bonus_type == BonusType.DAMAGE:
            self.value = DamageComponent(**self.value)
            return self

        if self.bonus_type == BonusType.ATTACK:
            assert isinstance(
                self.value, str
            ), f"Modifier value for '{self.bonus_type}' must be a string expression."
            return self

        if self.bonus_type in [
            BonusType.HP,
            BonusType.MIND,
            BonusType.AC,
            BonusType.INITIATIVE,
        ]:
            # Should be either an integer or a string expression
            if not isinstance(self.value, (int, str)):
                raise ValueError(
                    f"Modifier value for '{self.bonus_type}' must be an integer or string expression."
                )
            return self

        raise ValueError(f"Unknown bonus type: {self.bonus_type}")

    def __eq__(self, other: object) -> bool:
        """
        Check if two modifiers are equal.

        Args:
            other (object): The other object to compare with.

        Returns:
            bool: True if the modifiers are equal, False otherwise.

        """
        if not isinstance(other, Modifier):
            return False
        return self.bonus_type == other.bonus_type and self.value == other.value

    def __hash__(self) -> int:
        """Make the modifier hashable for use in sets and dictionaries."""
        from combat.damage import DamageComponent

        if isinstance(self.value, DamageComponent):
            # For DamageComponent, use its string representation for hashing
            return hash(
                (self.bonus_type, self.value.damage_roll, self.value.damage_type)
            )
        return hash((self.bonus_type, self.value))

    def __repr__(self) -> str:
        """String representation of the modifier."""
        return f"Modifier({self.bonus_type.name}, {self.value})"


class ActiveEffect(BaseModel):
    """
    Represents an active effect applied to a character, including its source,
    target, effect details, mind level, and duration.
    """

    source: Any = Field(
        description="The source of the effect (the caster)",
    )
    target: Any = Field(
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

    @model_validator(mode="after")
    def check_fields(self) -> Any:
        from character.main import Character

        if not isinstance(self.source, Character):
            raise ValueError("Source must be a Character instance.")
        if not isinstance(self.target, Character):
            raise ValueError("Target must be a Character instance.")
        if not isinstance(self.effect, Effect):
            raise ValueError("Effect must be an Effect instance.")
        if self.duration is not None and self.duration < 0:
            raise ValueError("Duration must be a non-negative integer or None.")
        if not all(isinstance(var, VarInfo) for var in self.variables):
            raise ValueError("All items in variables must be VarInfo instances.")
        return self

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
        Check if the trigger condition is met and the effect can be activated.

        Args:
            character (Any):
                The character to check the trigger condition against.
            event_data (dict[str, Any]):
                Context data about the triggering event.

        Returns:
            bool:
                True if the trigger condition is met and the effect can be
                activated, False otherwise.
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
        from effects.trigger_effect import TriggerType

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
        from effects.trigger_effect import TriggerType

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
