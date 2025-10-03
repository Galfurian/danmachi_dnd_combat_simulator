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
from core.constants import IncapacitationType

from .base_effect import ActiveEffect, Effect, EventResponse
from .event_system import CombatEvent, DamageTakenEvent, TurnEndEvent


class IncapacitatingEffect(Effect):
    """
    Effect that prevents a character from taking actions.

    Unlike ModifierEffect which only applies stat penalties, IncapacitatingEffect
    completely prevents the character from acting during their turn.
    """

    effect_type: Literal["IncapacitatingEffect"] = "IncapacitatingEffect"

    incapacitation_type: IncapacitationType = Field(
        description="Type of incapacitation (e.g., 'sleep', 'paralyzed', 'stunned').",
    )

    @property
    def color(self) -> str:
        """
        Returns the color for incapacitating effects.

        Returns:
            str:
                The color associated with the incapacitation type.
        """

        return self.incapacitation_type.color

    @property
    def emoji(self) -> str:
        """
        Returns the emoji for incapacitating effects.

        Returns:
            str:
                The emoji associated with the incapacitation type.
        """
        return self.incapacitation_type.emoji

    def prevents_actions(self) -> bool:
        """
        Check if this effect prevents the character from taking actions.

        Returns:
            bool:
                True if actions are prevented, False otherwise.

        """
        return True

    def prevents_movement(self) -> bool:
        """
        Check if this effect prevents movement.

        Returns:
            bool:
                True if movement is prevented, False otherwise.

        """
        return self.incapacitation_type in [
            IncapacitationType.PARALYZED,
            IncapacitationType.STUNNED,
            IncapacitationType.SLEEP,
        ]

    def breaks_on_damage(self) -> bool:
        """
        Check if taking damage should break this incapacitation.

        Returns:
            bool:
                True if damage breaks the effect, False otherwise.

        """
        return self.incapacitation_type in [
            IncapacitationType.SLEEP,
            IncapacitationType.CHARMED,
        ]

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
            remove_effect=self.incapacitating_effect.breaks_on_damage(),
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
