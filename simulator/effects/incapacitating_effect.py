from typing import Literal

from effects.event_system import DamageTakenEvent
from pydantic import Field

from .base_effect import ActiveEffect, Effect, EventResponse


class IncapacitatingEffect(Effect):
    """
    Effect that prevents a character from taking actions.

    Unlike ModifierEffect which only applies stat penalties, IncapacitatingEffect
    completely prevents the character from acting during their turn.
    """

    effect_type: Literal["IncapacitatingEffect"] = "IncapacitatingEffect"

    incapacitation_type: str = Field(
        description="Type of incapacitation (e.g., 'sleep', 'paralyzed', 'stunned').",
    )
    save_ends: bool = Field(
        False,
        description="Whether the effect can end on a successful saving throw.",
    )
    save_dc: int = Field(
        0,
        description="DC for the saving throw to end the effect.",
    )
    save_stat: str = Field(
        "CON",
        description="Stat used for the saving throw (e.g., 'CON', 'WIS').",
    )
    damage_threshold: int = Field(
        1,
        description="Minimum damage needed to break effect (if applicable).",
    )

    @property
    def color(self) -> str:
        """Returns the color string for incapacitating effects."""
        return "bold red"

    @property
    def emoji(self) -> str:
        """Returns the emoji for incapacitating effects."""
        return "😵‍💫"

    def prevents_actions(self) -> bool:
        """
        Check if this effect prevents the character from taking actions.

        Returns:
            bool: True if actions are prevented, False otherwise.

        """
        return True

    def prevents_movement(self) -> bool:
        """
        Check if this effect prevents movement.

        Returns:
            bool: True if movement is prevented, False otherwise.

        """
        return self.incapacitation_type in ["paralyzed", "stunned", "unconscious"]

    def auto_fails_saves(self) -> bool:
        """
        Check if character automatically fails certain saves.

        Returns:
            bool: True if saves are automatically failed, False otherwise.

        """
        return self.incapacitation_type in ["unconscious"]

    def breaks_on_damage(self, damage_amount: int = 1) -> bool:
        """
        Check if taking damage should break this incapacitation.

        Args:
            damage_amount (int): Amount of damage taken.

        Returns:
            bool: True if damage breaks the effect, False otherwise.

        """
        # First check if this type of incapacitation can break on damage
        if self.incapacitation_type not in ["sleep", "charm"]:
            return False

        # Then check if damage meets the threshold
        return damage_amount >= self.damage_threshold


class ActiveIncapacitatingEffect(ActiveEffect):

    @property
    def incapacitating_effect(self) -> IncapacitatingEffect:
        """
        Get the effect as an IncapacitatingEffect (narrowed type for clarity).

        Raises:
            TypeError:
                If the effect is not an IncapacitatingEffect.

        Returns:
            IncapacitatingEffect:
                The effect cast as an IncapacitatingEffect.

        """
        if not isinstance(self.effect, IncapacitatingEffect):
            raise TypeError(f"Expected IncapacitatingEffect, got {type(self.effect)}")
        return self.effect

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
        from character.main import Character

        if not isinstance(event.actor, Character):
            raise TypeError(f"Expected Character, got {type(event.actor)}")

        return EventResponse(
            effect=self.effect,
            remove_effect=self.incapacitating_effect.breaks_on_damage(
                event.damage_amount
            ),
            new_effects=[],
            damage_bonus=[],
            message=f"{event.actor.colored_name} wakes up from "
            f"{self.incapacitating_effect.colored_name} due to taking damage!",
        )

    def turn_update(self) -> None:
        """
        Update the effect for the current turn by calling the effect's
        turn_update method.
        """
        if not self.duration:
            raise ValueError("Effect duration is not set.")
        if self.duration <= 0:
            raise ValueError("Effect duration is already zero or negative.")
        self.duration -= 1
