"""
Event system module for the simulator.

Handles combat-related triggers and events, including event types,
event dispatching, and event-based effect resolution.
"""

from enum import Enum
from typing import Any

from core.constants import ActionCategory, DamageType
from pydantic import BaseModel, Field


class EventType(Enum):
    """Enumeration of available event types."""

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


class CombatEvent(BaseModel):
    """Base class for all trigger events."""

    event_type: EventType = Field(
        description="The type of trigger event.",
    )
    actor: Any = Field(description="The character or entity that triggered the event.")


class HitEvent(CombatEvent):
    """Event data for ON_HIT triggers."""

    event_type: EventType = Field(
        default=EventType.ON_HIT,
        description="The type of trigger event.",
    )
    target: Any = Field(description="The target of the attack.")

    def __str__(self) -> str:
        """
        String representation of the HitEvent.

        Returns:
            str:
                Formatted string representing the HitEvent.
        """
        return f"HitEvent({self.actor.colored_name} on {self.target.colored_name})"


class MissEvent(CombatEvent):
    """Event data for ON_MISS triggers."""

    event_type: EventType = Field(
        default=EventType.ON_MISS,
        description="The type of trigger event.",
    )
    target: Any = Field(description="The target of the attack.")

    def __str__(self) -> str:
        """
        String representation of the MissEvent.

        Returns:
            str:
                Formatted string representing the MissEvent.
        """
        return f"MissEvent({self.actor.colored_name} on {self.target.colored_name})"


class CriticalHitEvent(CombatEvent):
    """Event data for ON_CRITICAL_HIT triggers."""

    event_type: EventType = Field(
        default=EventType.ON_CRITICAL_HIT,
        description="The type of trigger event.",
    )
    attack_roll: int = Field(description="The attack roll result.")
    damage_dealt: int = Field(description="Amount of damage dealt.")
    damage_type: DamageType = Field(description="Type of damage dealt.")
    target: Any = Field(description="The target of the attack.")

    def __str__(self) -> str:
        """
        String representation of the CriticalHitEvent.

        Returns:
            str:
                Formatted string representing the CriticalHitEvent.
        """
        return (
            f"CriticalHitEvent({self.actor.colored_name} on {self.target.colored_name}, "
            f"attack={self.attack_roll}, damage={self.damage_dealt}, "
            f"type={self.damage_type})"
        )


class DamageTakenEvent(CombatEvent):
    """Event data for ON_DAMAGE_TAKEN triggers."""

    event_type: EventType = Field(
        default=EventType.ON_DAMAGE_TAKEN,
        description="The type of trigger event.",
    )
    damage_amount: int = Field(description="Amount of damage taken.")
    damage_type: DamageType = Field(description="Type of damage taken.")

    def __str__(self) -> str:
        """
        String representation of the DamageTakenEvent.

        Returns:
            str:
                Formatted string representing the DamageTakenEvent.
        """
        return (
            f"DamageTakenEvent({self.actor.colored_name}, damage={self.damage_amount}, "
            f"type={self.damage_type})"
        )


class LowHealthEvent(CombatEvent):
    """Event data for ON_LOW_HEALTH triggers."""

    event_type: EventType = Field(
        default=EventType.ON_LOW_HEALTH,
        description="The type of trigger event.",
    )

    def __str__(self) -> str:
        """
        String representation of the LowHealthEvent.

        Returns:
            str:
                Formatted string representing the LowHealthEvent.
        """
        return f"LowHealthEvent({self.actor.colored_name}, hp={self.actor.stats.hp_ratio():.2f}%)"


class TurnStartEvent(CombatEvent):
    """Event data for ON_TURN_START triggers."""

    event_type: EventType = Field(
        default=EventType.ON_TURN_START,
        description="The type of trigger event.",
    )
    turn_number: int = Field(description="Current turn number.")

    def __str__(self) -> str:
        """
        String representation of the TurnStartEvent.

        Returns:
            str:
                Formatted string representing the TurnStartEvent.
        """
        return f"TurnStartEvent({self.actor.colored_name}, turn={self.turn_number})"


class TurnEndEvent(CombatEvent):
    """Event data for ON_TURN_END triggers."""

    event_type: EventType = Field(
        default=EventType.ON_TURN_END,
        description="The type of trigger event.",
    )
    turn_number: int = Field(description="Current turn number.")

    def __str__(self) -> str:
        """
        String representation of the TurnEndEvent.

        Returns:
            str:
                Formatted string representing the TurnEndEvent.
        """
        return f"TurnEndEvent({self.actor.colored_name}, turn={self.turn_number})"


class DeathEvent(CombatEvent):
    """Event data for ON_DEATH triggers."""

    event_type: EventType = Field(
        default=EventType.ON_DEATH,
        description="The type of trigger event.",
    )
    killer: Any | None = Field(
        default=None, description="Entity that caused the death."
    )

    def __str__(self) -> str:
        """
        String representation of the DeathEvent.

        Returns:
            str:
                Formatted string representing the DeathEvent.
        """
        return f"DeathEvent({self.actor.colored_name}, killed_by={self.killer})"


class KillEvent(CombatEvent):
    """Event data for ON_KILL triggers."""

    event_type: EventType = Field(
        default=EventType.ON_KILL,
        description="The type of trigger event.",
    )
    defeated_enemy: Any = Field(description="The enemy that was defeated.")
    damage_dealt: int = Field(
        default=0, description="Damage dealt in the killing blow."
    )

    def __str__(self) -> str:
        """
        String representation of the KillEvent.

        Returns:
            str:
                Formatted string representing the KillEvent.
        """
        return f"KillEvent({self.actor.colored_name}, defeated={self.defeated_enemy})"


class HealEvent(CombatEvent):
    """Event data for ON_HEAL triggers."""

    event_type: EventType = Field(
        default=EventType.ON_HEAL,
        description="The type of trigger event.",
    )
    heal_amount: int = Field(description="Amount of healing received.")
    source: Any | None = Field(default=None, description="Source of the healing.")
    new_hp: int = Field(default=0, description="HP value after healing.")
    max_hp: int = Field(default=0, description="Maximum HP value.")

    def __str__(self) -> str:
        """
        String representation of the HealEvent.

        Returns:
            str:
                Formatted string representing the HealEvent.
        """
        return (
            f"HealEvent({self.actor.colored_name}, heal={self.heal_amount}, "
            f"source={self.source}, new_hp={self.new_hp}/{self.max_hp})"
        )


class SpellCastEvent(CombatEvent):
    """Event data for ON_SPELL_CAST triggers."""

    event_type: EventType = Field(
        default=EventType.ON_SPELL_CAST,
        description="The type of trigger event.",
    )
    spell_category: ActionCategory = Field(description="Category of the spell.")
    target: Any | None = Field(default=None, description="Target of the spell.")

    def __str__(self) -> str:
        """
        String representation of the SpellCastEvent.

        Returns:
            str:
                Formatted string representing the SpellCastEvent.
        """
        return (
            f"SpellCastEvent({self.actor.colored_name}, category={self.spell_category}, "
            f"target={self.target.colored_name})"
        )
