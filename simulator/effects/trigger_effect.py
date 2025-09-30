"""
Trigger effect module for the simulator.

Defines effects that trigger based on events, such as conditional
effects, reactive abilities, or event-based modifications.
"""

from typing import Any, Literal

from combat.damage import DamageComponent
from core.dice_parser import VarInfo
from pydantic import BaseModel, Field

from .base_effect import ActiveEffect, Effect, EventResponse
from .damage_over_time_effect import DamageOverTimeEffect
from .event_system import (
    CombatEvent,
    DamageTakenEvent,
    EventType,
    HighHealthEvent,
    HitEvent,
    LowHealthEvent,
    SpellCastEvent,
)
from .incapacitating_effect import IncapacitatingEffect
from .modifier_effect import ModifierEffect

ValidTriggerEffect = DamageOverTimeEffect | ModifierEffect | IncapacitatingEffect


class TriggerCondition(BaseModel):
    """
    Defines the condition that must be met for a trigger to activate.

    This class provides a flexible way to define various trigger conditions
    with parameters, thresholds, and custom validation logic.
    """

    trigger_type: EventType = Field(
        description="Type of trigger event.",
    )
    threshold: float | None = Field(
        default=None,
        description="Numerical threshold (e.g., 0.25 for 25% HP).",
    )
    damage_type: Any | None = Field(
        default=None,
        description="Specific damage type to trigger on (if applicable).",
    )
    spell_category: Any | None = Field(
        default=None,
        description="Specific spell category to trigger on (if applicable).",
    )
    description: str = Field(
        default="",
        description="Human-readable description of the condition.",
    )

    def _generate_description(self) -> str:
        """
        Generate a human-readable description of the trigger condition.

        Returns:
            str:
                The generated description.

        """
        if self.trigger_type == EventType.ON_HIT:
            return "when hitting with an attack"
        if self.trigger_type == EventType.ON_MISS:
            return "when missing with an attack"
        if self.trigger_type == EventType.ON_CRITICAL_HIT:
            return "when scoring a critical hit"
        if self.trigger_type == EventType.ON_DAMAGE_TAKEN:
            if self.damage_type:
                return f"when taking {self.damage_type.name.lower()} damage"
            return "when taking damage"
        if self.trigger_type == EventType.ON_LOW_HEALTH:
            return f"when HP drops below {(self.threshold or 0.25) * 100:.0f}%"
        if self.trigger_type == EventType.ON_HIGH_HEALTH:
            return f"when HP rises above {(self.threshold or 0.75) * 100:.0f}%"
        if self.trigger_type == EventType.ON_TURN_START:
            return "at the start of your turn"
        if self.trigger_type == EventType.ON_TURN_END:
            return "at the end of your turn"
        if self.trigger_type == EventType.ON_DEATH:
            return "upon death"
        if self.trigger_type == EventType.ON_KILL:
            return "upon killing an enemy"
        if self.trigger_type == EventType.ON_HEAL:
            return "when healed"
        if self.spell_category:
            return f"when casting {self.spell_category.name.lower()} spells"
        return "when casting any spell"

    def is_met(self, event: CombatEvent) -> bool:
        """
        Check if the trigger condition is met.

        Args:
            event (CombatEvent):
                The event to evaluate the condition for.

        Returns:
            bool:
                True if the condition is met, False otherwise.

        """
        if self.trigger_type != event.trigger_type:
            raise ValueError("Event type does not match trigger condition type.")

        # There are some trigger types that always activate when the event
        # occurs.
        if event.trigger_type in [
            EventType.ON_HIT,
            EventType.ON_MISS,
            EventType.ON_CRITICAL_HIT,
            EventType.ON_TURN_START,
            EventType.ON_TURN_END,
            EventType.ON_DEATH,
            EventType.ON_HEAL,
            EventType.ON_KILL,
        ]:
            return True

        # If the event is DamageTakenEvent, check damage type and amount.
        if isinstance(event, DamageTakenEvent):
            if self.damage_type:
                return event.damage_type == self.damage_type
            return event.damage_amount > 0
        # If the event is LowHealthEvent, check HP ratio against threshold.
        if isinstance(event, LowHealthEvent):
            return self._get_hp_ratio(event) <= (self.threshold or 0.25)
        # If the event is HighHealthEvent, check HP ratio against threshold.
        if isinstance(event, HighHealthEvent):
            return self._get_hp_ratio(event) >= (self.threshold or 0.75)
        # If the event is SpellCastEvent, check spell category if specified.
        if isinstance(event, SpellCastEvent):
            if self.spell_category:
                return event.spell_category == self.spell_category
            return True

        return False

    def _get_hp_ratio(self, event: CombatEvent) -> float:
        """
        Get the HP ratio (current HP / max HP) of the actor involved in the event.

        Args:
            event (CombatEvent):
                The event containing the actor whose HP ratio is to be calculated.

        Raises:
            ValueError:
                If the actor is not a Character instance.

        Returns:
            float:
                The HP ratio (0.0 to 1.0).

        """
        from character.main import Character

        if not isinstance(event.actor, Character):
            raise ValueError("Actor must be a Character instance to get HP ratio.")

        return (
            event.actor.stats.hp / event.actor.HP_MAX if event.actor.HP_MAX > 0 else 0
        )


class TriggerEffect(Effect):
    """
    Universal trigger effect that can respond to various game events.

    This unified system allows for flexible trigger-based effects that can
    activate on hits, health thresholds, spell casts, and many other conditions.
    Effects can stack, have cooldowns, and provide both immediate and ongoing benefits.
    """

    effect_type: Literal["TriggerEffect"] = "TriggerEffect"

    trigger_condition: TriggerCondition = Field(
        description="Condition that activates the trigger.",
    )
    trigger_effects: list[ValidTriggerEffect] = Field(
        default_factory=list,
        description="Effects to apply when triggered.",
    )
    damage_bonus: list[DamageComponent] = Field(
        default_factory=list,
        description="Additional damage components applied when triggered.",
    )
    consumes_on_trigger: bool = Field(
        True,
        description="Whether the effect is consumed when triggered.",
    )
    cooldown_turns: int | None = Field(
        0,
        ge=0,
        description="Number of turns before trigger can activate again.",
    )
    max_triggers: int | None = Field(
        None,
        description="Maximum number of times trigger can activate (None for unlimited).",
    )

    @property
    def color(self) -> str:
        """Returns the color string for trigger effects."""
        return "bold magenta"

    @property
    def emoji(self) -> str:
        """Returns the emoji for trigger effects."""
        return "⚡"

    def model_post_init(self, _: Any) -> None:
        if not self.trigger_condition.description:
            self.trigger_condition.description = (
                self.trigger_condition._generate_description()
            )
        if not all(isinstance(e, ValidTriggerEffect) for e in self.trigger_effects):
            raise ValueError(
                "All trigger effects must be valid effect types (ModifierEffect, "
                "IncapacitatingEffect, or DamageOverTimeEffect)."
            )
        if not all(isinstance(dmg, DamageComponent) for dmg in self.damage_bonus):
            raise ValueError("All damage bonuses must be DamageComponent instances.")
        if self.max_triggers is not None and self.max_triggers < 0:
            raise ValueError("Max triggers must be None (unlimited) or non-negative.")

    def can_apply(
        self,
        actor: Any,
        target: Any,
        variables: list[VarInfo],
    ) -> bool:
        """
        Check if the trigger effect can be applied to the target.

        Rules for trigger effect application:
            1. Basic eligibility: Actor and target must be alive Characters
            2. Stacking limit: Target cannot have 3 or more active trigger
               effects

        Args:
            actor (Character):
                The character applying the effect.
            target (Character):
                The character receiving the effect.
            variables (list[VarInfo]):
                List of variable info for dynamic calculations.

        Returns:
            bool:
                True if the effect can be applied, False otherwise.

        """
        from character.main import Character

        # Rule 1: Basic validation from parent class
        if not super().can_apply(actor, target, variables):
            return False

        assert isinstance(actor, Character), "Actor must be a Character."
        assert isinstance(target, Character), "Target must be a Character."

        # Rule 2: Stacking limit - prevent applying if target has 3+ trigger
        # effects
        if sum(1 for _ in target.effects.trigger_effects) >= 3:
            return False

        return True

    def is_type(self, trigger_type: EventType) -> bool:
        """Check if this trigger activates on the specified trigger type."""
        return self.trigger_condition.trigger_type == trigger_type


class ActiveTriggerEffect(ActiveEffect):
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
    def trigger_effect(self) -> "TriggerEffect":
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

    def check_trigger(self, event: "CombatEvent") -> bool:
        """
        Check if the trigger condition is met for the given event.

        Args:
            event (CombatEvent):
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
        return self.trigger_effect.trigger_condition.is_met(event)

    def activate_trigger(
        self,
    ) -> tuple[list[DamageComponent], list["ValidTriggerEffect"]]:
        """
        Activate the trigger and return effects and damage bonuses.

        Returns:
            tuple[list[DamageComponent], list[ValidTriggerEffect]]:
                Damage bonuses and effects with mind levels.

        """
        if not self.trigger_effect.damage_bonus:
            raise ValueError("TriggerEffect must have a damage_bonus defined.")
        if not self.trigger_effect.trigger_effects:
            raise ValueError("TriggerEffect must have trigger_effects defined.")

        # Increment triggers used.
        self.increment_triggers_used()
        # Mark as triggered this turn if applicable.
        self.mark_as_triggered_this_turn()
        # Start the cooldown if applicable.
        self.start_cooldown()

        return self.trigger_effect.damage_bonus, self.trigger_effect.trigger_effects

    def is_in_cooldown(self) -> bool:
        """
        Check if the trigger is currently on cooldown.

        Returns:
            bool:
                True if the trigger is on cooldown, False otherwise.

        """
        if self.trigger_effect.cooldown_turns:
            return self.cooldown_remaining > 0
        return False

    def start_cooldown(self) -> None:
        """
        Start the cooldown of the trigger by setting it to the defined cooldown
        turns.
        """
        if self.trigger_effect.cooldown_turns:
            self.cooldown_remaining = self.trigger_effect.cooldown_turns

    def decrement_cooldown(self) -> None:
        """
        Decrement the cooldown counter by one turn if it's greater than zero.
        """
        if self.trigger_effect.cooldown_turns and self.cooldown_remaining > 0:
            self.cooldown_remaining -= 1

    def is_turn_based_trigger(self) -> bool:
        """
        Check if the trigger is turn-based (i.e., activates on turn start or
        end).

        Returns:
            bool:
                True if the trigger is turn-based, False otherwise.

        """
        return self.trigger_effect.trigger_condition.trigger_type in [
            EventType.ON_TURN_START,
            EventType.ON_TURN_END,
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
        if self.trigger_effect.max_triggers is not None:
            self.triggers_used += 1

    def exceeded_max_triggers(self) -> bool:
        """
        Check if the trigger has exceeded its maximum allowed activations.

        Returns:
            bool:
                True if the maximum number of triggers has been reached, False
                otherwise.

        """
        if self.trigger_effect.max_triggers is None:
            return False
        return self.triggers_used >= self.trigger_effect.max_triggers

    def on_hit(self, event: HitEvent) -> EventResponse | None:
        """
        Handle hit event for trigger effects.

        Args:
            event (HitEvent):
                The hit event.

        Returns:
            EventResponse | None:
                The response to the hit event. If the effect does not respond
                to hits, return None.

        """
        if not self.check_trigger(event):
            return None
        damage_bonus, new_effects = self.activate_trigger()

        return EventResponse(
            effect=self.effect,
            remove_effect=self.trigger_effect.consumes_on_trigger,
            new_effects=new_effects,  # type: ignore[arg-type]
            damage_bonus=damage_bonus,
            message=(
                f"{event.actor.colored_name}'s {self.effect.colored_name} triggered, "
                f"applying {', '.join(e.colored_name for e in new_effects)}!"
            ),
        )

    def on_damage_taken(self, event: DamageTakenEvent) -> EventResponse | None:
        """
        Handle damage taken event for incapacitating effects.

        Args:
            event (DamageTakenEvent):
                The damage taken event.

        Returns:
            EventResponse | None:
                The response to the damage taken event. If the effect does not
                respond to damage, return None.

        """
        if not self.check_trigger(event):
            return None
        damage_bonus, new_effects = self.activate_trigger()
        return EventResponse(
            effect=self.effect,
            remove_effect=self.trigger_effect.consumes_on_trigger,
            new_effects=new_effects,  # type: ignore[arg-type]
            damage_bonus=damage_bonus,
            message=(
                f"{event.actor.colored_name}'s {self.effect.colored_name} triggered, "
                f"applying {', '.join(e.colored_name for e in new_effects)}!"
            ),
        )
