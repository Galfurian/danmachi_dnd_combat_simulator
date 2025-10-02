"""
Incapacitating effect module for the simulator.

Defines effects that incapacitate characters, preventing them from
taking actions or participating in combat.
"""

from typing import Any, Literal

from core.dice_parser import VarInfo
from core.logging import log_debug
from core.utils import cprint
from pydantic import Field

from .base_effect import ActiveEffect, Effect, EventResponse
from .event_system import CombatEvent, DamageTakenEvent, EventType, TurnEndEvent


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

    def can_apply(
        self,
        actor: Any,
        target: Any,
        variables: list[VarInfo],
    ) -> bool:
        """
        Check if the incapacitating effect can be applied to the target.

        Rules for incapacitating effect application:
            1. Basic eligibility: Actor and target must be alive Characters
            2. Self-targeting: Cannot apply incapacitating effects to self
            3. No stacking: Target cannot already have an incapacitating effect

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

        # Rule 2: Self-targeting restriction
        if actor == target:
            log_debug(
                "Cannot apply incapacitating effect: Self-targeting is not allowed."
            )
            return False

        # Rule 3: No stacking - prevent applying if target already has
        # incapacitating effect.
        if sum(1 for _ in target.effects.incapacitating_effects) >= 1:
            log_debug(
                f"Cannot apply incapacitating effect: Target "
                f"{target.colored_name} already has an active "
                "incapacitating effect."
            )
            return False

        return True

    def apply_effect(
        self,
        actor: Any,
        target: Any,
        variables: list[VarInfo],
    ) -> bool:
        """
        Apply the incapacitating effect to the target, creating an
        ActiveEffect if valid.

        Args:
            actor (Character):
                The character applying the effect.
            target (Character):
                The character receiving the effect.
            variables (list[VarInfo]):
                List of variable info for dynamic calculations.

        Returns:
            bool:
                True if the effect was applied successfully, False otherwise.

        """
        from character.main import Character

        if not self.can_apply(actor, target, variables):
            return False

        assert isinstance(actor, Character), "Actor must be a Character."
        assert isinstance(target, Character), "Target must be a Character."

        log_debug(
            f"Applying incapacitating effect {self.colored_name} "
            f"from {actor.colored_name} to {target.colored_name}."
        )

        # Create new ActiveIncapacitatingEffect.
        target.effects.active_effects.append(
            ActiveIncapacitatingEffect(
                source=actor,
                target=target,
                effect=self,
                duration=self.duration,
                variables=variables,
            )
        )
        return True


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

    def on_event(self, event: CombatEvent) -> EventResponse | None:
        """
        Handle a generic event for the effect.

        Args:
            event (Any):
                The event to handle.
        Returns:
            EventResponse | None:
                The response to the event. If the effect does not
                respond to this event type, return None.
        """
        if isinstance(event, TurnEndEvent):
            return self._on_turn_end(event)
        if isinstance(event, DamageTakenEvent):
            return self._on_damage_taken(event)
        return None

    def _on_damage_taken(self, event: DamageTakenEvent) -> EventResponse | None:
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

        if not isinstance(event.source, Character):
            raise TypeError(f"Expected Character, got {type(event.source)}")

        return EventResponse(
            effect=self.effect,
            remove_effect=self.incapacitating_effect.breaks_on_damage(event.amount),
            new_effects=[],
            damage_bonus=[],
            message=f"{event.source.colored_name} wakes up from "
            f"{self.incapacitating_effect.colored_name} due to taking damage!",
        )

    def _on_turn_end(self, event: TurnEndEvent) -> EventResponse | None:
        """
        Update the effect for the current turn by decrementing duration at the
        end of the turn.
        """
        if not self.duration:
            raise ValueError("Effect duration is not set.")
        if self.duration <= 0:
            raise ValueError("Effect duration is already zero or negative.")
        self.duration -= 1
        remove_effect = False
        if self.duration <= 0:
            cprint(
                f"    :hourglass_done: {self.effect.colored_name} "
                f"has expired on {self.target.colored_name}."
            )
            remove_effect = True
        return EventResponse(
            effect=self.effect,
            remove_effect=remove_effect,
            new_effects=[],
            damage_bonus=[],
            message=f"{self.target.colored_name} is no longer "
            f"affected by {self.incapacitating_effect.colored_name}.",
        )
