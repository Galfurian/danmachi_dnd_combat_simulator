from enum import Enum
from typing import Any, Literal, TypeAlias, Union

from combat.damage import DamageComponent
from pydantic import BaseModel, Field

from .base_effect import Effect
from .damage_over_time_effect import DamageOverTimeEffect
from .modifier_effect import ModifierEffect
from .incapacitating_effect import IncapacitatingEffect

ValidTriggerEffect: TypeAlias = Union[
    DamageOverTimeEffect,
    ModifierEffect,
    IncapacitatingEffect,
]


class TriggerType(Enum):
    """Enumeration of available trigger types for OnTrigger effects."""

    ON_HIT = "on_hit"  # When character hits with an attack
    ON_MISS = "on_miss"  # When character misses an attack
    ON_CRITICAL_HIT = "on_critical_hit"  # When character scores a critical hit
    ON_DAMAGE_TAKEN = "on_damage_taken"  # When character takes damage

    ON_LOW_HEALTH = "on_low_health"  # When HP drops below threshold
    ON_HIGH_HEALTH = "on_high_health"  # When HP rises above threshold

    ON_TURN_START = "on_turn_start"  # At the beginning of character's turn
    ON_TURN_END = "on_turn_end"  # At the end of character's turn

    ON_DEATH = "on_death"  # When character reaches 0 HP
    ON_KILL = "on_kill"  # When character defeats an enemy

    ON_HEAL = "on_heal"  # When character is healed
    ON_SPELL_CAST = "on_spell_cast"  # When character casts a spell


class TriggerEvent(BaseModel):
    """Base class for all trigger events."""

    trigger_type: TriggerType = Field(
        description="The type of trigger event.",
    )
    actor: Any = Field(description="The character or entity that triggered the event.")


class HitTriggerEvent(TriggerEvent):
    """Event data for ON_HIT triggers."""

    trigger_type: TriggerType = Field(
        default=TriggerType.ON_HIT,
        description="The type of trigger event.",
    )
    target: Any = Field(description="The target of the attack.")


class MissTriggerEvent(TriggerEvent):
    """Event data for ON_MISS triggers."""

    trigger_type: TriggerType = Field(
        default=TriggerType.ON_MISS,
        description="The type of trigger event.",
    )
    attack_roll: int = Field(description="The attack roll result.")
    target: Any = Field(description="The target of the attack.")
    weapon_used: Any | None = Field(
        default=None, description="Weapon used in the attack."
    )


class CriticalHitTriggerEvent(TriggerEvent):
    """Event data for ON_CRITICAL_HIT triggers."""

    trigger_type: TriggerType = Field(
        default=TriggerType.ON_CRITICAL_HIT,
        description="The type of trigger event.",
    )
    attack_roll: int = Field(description="The attack roll result.")
    damage_dealt: int = Field(description="Amount of damage dealt.")
    target: Any = Field(description="The target of the attack.")
    weapon_used: Any | None = Field(
        default=None, description="Weapon used in the attack."
    )


class DamageTakenTriggerEvent(TriggerEvent):
    """Event data for ON_DAMAGE_TAKEN triggers."""

    trigger_type: TriggerType = Field(
        default=TriggerType.ON_DAMAGE_TAKEN,
        description="The type of trigger event.",
    )
    damage_amount: int = Field(description="Amount of damage taken.")
    damage_type: Any = Field(description="Type of damage taken.")
    source: Any | None = Field(default=None, description="Source of the damage.")
    remaining_hp: int = Field(default=0, description="HP remaining after damage.")
    total_damage_taken: int = Field(
        default=0, description="Total damage taken in this event."
    )


class LowHealthTriggerEvent(TriggerEvent):
    """Event data for ON_LOW_HEALTH triggers."""

    trigger_type: TriggerType = Field(
        default=TriggerType.ON_LOW_HEALTH,
        description="The type of trigger event.",
    )
    current_hp: int = Field(description="Current HP value.")
    max_hp: int = Field(description="Maximum HP value.")
    threshold: float = Field(
        description="HP threshold percentage that triggered this event."
    )
    previous_hp: int = Field(default=0, description="HP value before this event.")


class HighHealthTriggerEvent(TriggerEvent):
    """Event data for ON_HIGH_HEALTH triggers."""

    trigger_type: TriggerType = Field(
        default=TriggerType.ON_HIGH_HEALTH,
        description="The type of trigger event.",
    )
    current_hp: int = Field(description="Current HP value.")
    max_hp: int = Field(description="Maximum HP value.")
    threshold: float = Field(
        description="HP threshold percentage that triggered this event."
    )
    previous_hp: int = Field(default=0, description="HP value before this event.")


class TurnStartTriggerEvent(TriggerEvent):
    """Event data for ON_TURN_START triggers."""

    trigger_type: TriggerType = Field(
        default=TriggerType.ON_TURN_START,
        description="The type of trigger event.",
    )
    turn_number: int = Field(description="Current turn number.")
    round_number: int = Field(default=1, description="Current round number.")


class TurnEndTriggerEvent(TriggerEvent):
    """Event data for ON_TURN_END triggers."""

    trigger_type: TriggerType = Field(
        default=TriggerType.ON_TURN_END,
        description="The type of trigger event.",
    )
    turn_number: int = Field(description="Current turn number.")
    round_number: int = Field(default=1, description="Current round number.")


class DeathTriggerEvent(TriggerEvent):
    """Event data for ON_DEATH triggers."""

    trigger_type: TriggerType = Field(
        default=TriggerType.ON_DEATH,
        description="The type of trigger event.",
    )
    cause: str = Field(default="unknown", description="Cause of death.")
    final_hp: int = Field(default=0, description="Final HP value.")
    killer: Any | None = Field(
        default=None, description="Entity that caused the death."
    )


class KillTriggerEvent(TriggerEvent):
    """Event data for ON_KILL triggers."""

    trigger_type: TriggerType = Field(
        default=TriggerType.ON_KILL,
        description="The type of trigger event.",
    )
    defeated_enemy: Any = Field(description="The enemy that was defeated.")
    damage_dealt: int = Field(
        default=0, description="Damage dealt in the killing blow."
    )
    kill_method: str = Field(
        default="unknown", description="Method used to defeat the enemy."
    )


class HealTriggerEvent(TriggerEvent):
    """Event data for ON_HEAL triggers."""

    trigger_type: TriggerType = Field(
        default=TriggerType.ON_HEAL,
        description="The type of trigger event.",
    )
    heal_amount: int = Field(description="Amount of healing received.")
    source: Any | None = Field(default=None, description="Source of the healing.")
    new_hp: int = Field(default=0, description="HP value after healing.")
    max_hp: int = Field(default=0, description="Maximum HP value.")


class SpellCastTriggerEvent(TriggerEvent):
    """Event data for ON_SPELL_CAST triggers."""

    trigger_type: TriggerType = Field(
        default=TriggerType.ON_SPELL_CAST,
        description="The type of trigger event.",
    )
    spell_category: Any = Field(description="Category of the spell.")
    target: Any | None = Field(default=None, description="Target of the spell.")


class TriggerCondition(BaseModel):
    """
    Defines the condition that must be met for a trigger to activate.

    This class provides a flexible way to define various trigger conditions
    with parameters, thresholds, and custom validation logic.
    """

    trigger_type: TriggerType = Field(
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
        """Generate a human-readable description of the trigger condition."""
        if self.trigger_type == TriggerType.ON_LOW_HEALTH:
            return f"when HP drops below {(self.threshold or 0.25) * 100:.0f}%"
        if self.trigger_type == TriggerType.ON_HIGH_HEALTH:
            return f"when HP rises above {(self.threshold or 0.75) * 100:.0f}%"
        if self.trigger_type == TriggerType.ON_DAMAGE_TAKEN and self.damage_type:
            return f"when taking {self.damage_type.name.lower()} damage"
        if self.trigger_type == TriggerType.ON_SPELL_CAST and self.spell_category:
            return f"when casting {self.spell_category.name.lower()} spells"
        return self.trigger_type.value.replace("_", " ")

    def is_met(self, event: TriggerEvent) -> bool:
        """
        Check if the trigger condition is met.

        Args:
            event (TriggerEvent):
                The event to evaluate the condition for.

        Returns:
            bool:
                True if the condition is met, False otherwise.

        """
        from character.main import Character

        if self.trigger_type != event.trigger_type:
            raise ValueError("Event type does not match trigger condition type.")

        # There are some trigger types that always activate when the event
        # occurs.
        if event.trigger_type in [
            TriggerType.ON_HIT,
            TriggerType.ON_MISS,
            TriggerType.ON_CRITICAL_HIT,
            TriggerType.ON_TURN_START,
            TriggerType.ON_TURN_END,
            TriggerType.ON_DEATH,
            TriggerType.ON_HEAL,
            TriggerType.ON_KILL,
        ]:
            return True

        # If the event is DamageTakenTriggerEvent, check damage type and amount.
        if isinstance(event, DamageTakenTriggerEvent):
            if self.damage_type:
                return event.damage_type == self.damage_type
            return event.damage_amount > 0
        # If the event is LowHealthTriggerEvent, check HP ratio against threshold.
        if isinstance(event, LowHealthTriggerEvent):
            return self._get_hp_ratio(event) <= (self.threshold or 0.25)
        # If the event is HighHealthTriggerEvent, check HP ratio against threshold.
        if isinstance(event, HighHealthTriggerEvent):
            return self._get_hp_ratio(event) >= (self.threshold or 0.75)
        # If the event is SpellCastTriggerEvent, check spell category if specified.
        if isinstance(event, SpellCastTriggerEvent):
            if self.spell_category:
                return event.spell_category == self.spell_category
            return True

        return False

    def _get_hp_ratio(self, event: TriggerEvent) -> float:
        """
        Get the HP ratio (current HP / max HP) of the actor involved in the event.

        Args:
            event (TriggerEvent):
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
        return event.actor.hp / event.actor.HP_MAX if event.actor.HP_MAX > 0 else 0


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
    cooldown_turns: int = Field(
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
        return "bold white"

    @property
    def emoji(self) -> str:
        """Returns the emoji for trigger effects."""
        return "⚡"

    def model_post_init(self, _) -> None:
        if not isinstance(self.trigger_condition, TriggerCondition):
            raise ValueError("Trigger condition must be a TriggerCondition instance.")
        if not self.trigger_condition.description:
            self.trigger_condition.description = (
                self.trigger_condition._generate_description()
            )
        for effect in self.trigger_effects or []:
            if not isinstance(effect, Effect):
                raise ValueError(
                    f"Each trigger effect must be an Effect instance, got {type(effect)}"
                )
        if self.damage_bonus is None:
            self.damage_bonus = []
        elif not isinstance(self.damage_bonus, list):
            raise ValueError(
                "Damage bonus must be a list of DamageComponent instances."
            )
        else:
            for dmg in self.damage_bonus:
                if not isinstance(dmg, DamageComponent):
                    raise ValueError(
                        f"Each damage bonus must be a DamageComponent instance, got {type(dmg)}"
                    )
        if self.cooldown_turns < 0:
            raise ValueError("Cooldown turns must be non-negative.")
        if self.max_triggers is not None and self.max_triggers < 0:
            raise ValueError("Max triggers must be None (unlimited) or non-negative.")

    def is_type(self, trigger_type: TriggerType) -> bool:
        """Check if this trigger activates on the specified trigger type."""
        return self.trigger_condition.trigger_type == trigger_type
