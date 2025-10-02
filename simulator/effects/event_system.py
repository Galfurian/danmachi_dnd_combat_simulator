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

    @property
    def color(self) -> str:
        """Returns the color string associated with this character type."""
        return "bold yellow"

    @property
    def colored_name(self) -> str:
        return self.colorize(self.name.lower().replace("_", " ").capitalize())

    def colorize(self, message: str) -> str:
        """Applies character type color formatting to a message."""
        return f"[{self.color}]{message}[/]"


class CombatEvent(BaseModel):
    """Base class for all trigger events."""

    event_type: EventType = Field(
        description="The type of trigger event.",
    )
    source: Any = Field(description="The character or entity that triggered the event.")


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
        return f"HitEvent({self.source.colored_name} on {self.target.colored_name})"


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
        return f"MissEvent({self.source.colored_name} on {self.target.colored_name})"


class CriticalHitEvent(CombatEvent):
    """Event data for ON_CRITICAL_HIT triggers."""

    event_type: EventType = Field(
        default=EventType.ON_CRITICAL_HIT,
        description="The type of trigger event.",
    )
    target: Any = Field(description="The target of the attack.")
    attack_roll: int = Field(description="The attack roll result.")
    damage_dealt: int = Field(description="Amount of damage dealt.")
    damage_type: DamageType = Field(description="Type of damage dealt.")

    def __str__(self) -> str:
        """
        String representation of the CriticalHitEvent.

        Returns:
            str:
                Formatted string representing the CriticalHitEvent.
        """
        return (
            "CriticalHitEvent("
            f"{self.source.colored_name} on {self.target.colored_name}, "
            f"attack={self.attack_roll}, damage={self.damage_dealt}, "
            f"type={self.damage_type})"
        )


class DamageTakenEvent(CombatEvent):
    """Event data for ON_DAMAGE_TAKEN triggers."""

    event_type: EventType = Field(
        default=EventType.ON_DAMAGE_TAKEN,
        description="The type of trigger event.",
    )
    target: Any = Field(description="The target of the damage.")
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
            "DamageTakenEvent("
            f"{self.source.colored_name} on {self.target.colored_name}, "
            f"damage={self.damage_amount}, type={self.damage_type})"
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
        return f"LowHealthEvent({self.source.colored_name}, hp={self.source.stats.hp_ratio():.2f}%)"


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
        return f"TurnStartEvent({self.source.colored_name}, turn={self.turn_number})"


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
        return f"TurnEndEvent({self.source.colored_name}, turn={self.turn_number})"


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
        return f"DeathEvent({self.source.colored_name}, killed_by={self.killer})"


class KillEvent(CombatEvent):
    """Event data for ON_KILL triggers."""

    event_type: EventType = Field(
        default=EventType.ON_KILL,
        description="The type of trigger event.",
    )
    killed: Any = Field(description="The enemy that was defeated.")

    def __str__(self) -> str:
        """
        String representation of the KillEvent.

        Returns:
            str:
                Formatted string representing the KillEvent.
        """
        return f"KillEvent({self.source.colored_name}, defeated={self.killed.colored_name})"


class HealEvent(CombatEvent):
    """Event data for ON_HEAL triggers."""

    event_type: EventType = Field(
        default=EventType.ON_HEAL,
        description="The type of trigger event.",
    )
    amount: int = Field(description="Amount of healing received.")

    def __str__(self) -> str:
        """
        String representation of the HealEvent.

        Returns:
            str:
                Formatted string representing the HealEvent.
        """
        return (
            f"HealEvent({self.source.colored_name}, amount={self.amount}, "
            f"hp={self.source.stats.hp}/{self.source.stats.max_hp})"
        )


class SpellCastEvent(CombatEvent):
    """Event data for ON_SPELL_CAST triggers."""

    event_type: EventType = Field(
        default=EventType.ON_SPELL_CAST,
        description="The type of trigger event.",
    )
    spell_category: ActionCategory = Field(description="Category of the spell.")
    target: Any = Field(default=None, description="Target of the spell.")

    def __str__(self) -> str:
        """
        String representation of the SpellCastEvent.

        Returns:
            str:
                Formatted string representing the SpellCastEvent.
        """
        return (
            f"SpellCastEvent({self.source.colored_name}, category={self.spell_category}, "
            f"target={self.target.colored_name})"
        )
