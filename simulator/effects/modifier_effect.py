"""
Modifier effect module for the simulator.

Defines effects that modify character stats, such as bonuses or penalties to
attributes, AC, or other properties.
"""

from __future__ import annotations

from typing import Any, Literal

from combat.damage import DamageComponent
from core.constants import BonusType
from core.dice_parser import VarInfo, get_max_roll
from core.logging import log_debug
from core.utils import cprint
from effects.event_system import CombatEvent, EventType, TurnEndEvent
from pydantic import BaseModel, Field

from .base_effect import ActiveEffect, Effect, EventResponse


class Modifier(BaseModel):
    """
    Handles different types of modifiers that can be applied to characters.

    Modifiers represent bonuses or penalties to various character attributes
    such as HP, AC, damage, or other stats.
    """

    bonus_type: BonusType = Field(
        description="The type of bonus the modifier applies.",
    )
    value: str | DamageComponent = Field(
        description=(
            "The value of the modifier. Can be an integer, string expression, or DamageComponent."
        ),
    )

    @property
    def stacks(self) -> bool:
        """
        Indicates if the modifier stacks with others of the same type.

        Returns:
            bool:
                True if the modifier stacks, False otherwise.
        """
        if self.bonus_type == BonusType.AC:
            return False
        return True

    def model_post_init(self, _: Any) -> None:
        from combat.damage import DamageComponent

        if self.bonus_type == BonusType.DAMAGE:
            assert isinstance(
                self.value, DamageComponent
            ), "Modifier value for 'DAMAGE' must be a DamageComponent."
        else:
            assert isinstance(
                self.value, str
            ), f"Modifier value for '{self.bonus_type}' must be a string."

    def get_projected_strength(self, variables: list[VarInfo]) -> int:
        """
        Determine the strength of a specific modifier type.

        Args:
            variables (list[VarInfo]):
                List of variable info for dynamic calculations.

        Returns:
            int:
                The strength value of the modifier.
        """
        if isinstance(self.value, DamageComponent):
            return get_max_roll(self.value.damage_roll, variables)
        return get_max_roll(self.value, variables)

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


class ModifierEffect(Effect):
    """
    Base class for effects that apply stat modifiers to characters.

    This includes buffs and debuffs that temporarily modify character attributes
    like HP, AC, damage bonuses, etc.
    """

    effect_type: Literal["ModifierEffect"] = "ModifierEffect"

    modifiers: list[Modifier] = Field(
        description="List of modifiers applied by this effect.",
    )

    @property
    def color(self) -> str:
        """Returns the color string for modifier effects."""
        return "bold yellow"

    @property
    def emoji(self) -> str:
        """Returns the emoji for modifier effects."""
        return "🛡️"

    def model_post_init(self, _: Any) -> None:
        """
        Ensure that the modifiers list is not empty.

        Raises:
            ValueError: If the modifiers list is empty.

        """
        if not self.modifiers:
            raise ValueError("Modifiers list cannot be empty.")
        for modifier in self.modifiers:
            if not isinstance(modifier, Modifier):
                raise ValueError(f"Invalid modifier: {modifier}")

    def get_projected_strength(
        self,
        bonus_type: BonusType,
        variables: list[VarInfo],
    ) -> int:
        """
        Determine the strength of a specific modifier type.

        Args:
            bonus_type (BonusType):
                The bonus type to evaluate.
            variables (list[VarInfo]):
                List of variable info for dynamic calculations.

        Returns:
            int:
                The strength value of the modifier. 0 if not present.
        """
        for mod in self.modifiers:
            if mod.bonus_type == bonus_type:
                return mod.get_projected_strength(variables)
        return 0

    def is_stronger_than(
        self,
        other: ModifierEffect,
        variables: list[VarInfo],
    ) -> bool:
        """
        Compare this ModifierEffect to another to determine if it is stronger.

        Args:
            other (ModifierEffect):
                The other ModifierEffect to compare against.
            variables (list[VarInfo]):
                List of variable info for dynamic calculations.

        Raises:
            TypeError:
                If the other effect is not a ModifierEffect.

        Returns:
            bool:
                True if this effect is stronger than the other, False otherwise.
        """
        if not isinstance(other, ModifierEffect):
            raise TypeError(f"Cannot compare ModifierEffect with {type(other)}")

        # Find at least one modifier that is stronger.
        for modifier in self.modifiers:
            bonus_type = modifier.bonus_type
            self_strength = self.get_projected_strength(bonus_type, variables)
            other_strength = other.get_projected_strength(bonus_type, variables)
            log_debug(
                f"Comparing ModifierEffect strengths for bonus type {bonus_type.name}: "
                f"{self_strength} (self) vs {other_strength} (other)"
            )
            if self_strength > other_strength:
                log_debug(
                    f"ModifierEffect {self.colored_name} is stronger than "
                    f"{other.colored_name} for bonus type {bonus_type.name}: "
                    f"{self_strength} > {other_strength}"
                )
                return True
        return False

    def can_apply(
        self,
        actor: Any,
        target: Any,
        variables: list[VarInfo],
    ) -> bool:
        """
        Check if the modifier effect can be applied to the target.

        Rules for modifier effect application:
            1. Basic eligibility: Actor and target must be alive Characters
            2. Stacking limit: Target cannot have 5 or more active modifier
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

        # Rule 2: Stacking limit - prevent applying if target has 5+ modifier
        # effects.
        if sum(1 for _ in target.effects.modifier_effects) >= 5:
            log_debug(
                f"Cannot apply modifier effect: Target {target.colored_name} "
                "already has 5 or more active modifier effects."
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
        Apply the modifier effect to the target, creating an ActiveEffect if valid.

        Handles merging by comparing modifier strengths and replacing weaker effects.

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
        from combat.damage import DamageComponent

        if not self.can_apply(actor, target, variables):
            return False

        assert isinstance(actor, Character), "Actor must be a Character."
        assert isinstance(target, Character), "Target must be a Character."

        log_debug(
            f"Applying modifier effect '{self.colored_name}' "
            f"from {actor.colored_name} to {target.colored_name}."
        )

        # Add the new effect.
        target.effects.active_effects.append(
            ActiveModifierEffect(
                source=actor,
                target=target,
                effect=self,
                duration=self.duration,
                variables=variables,
            )
        )
        return True


class ActiveModifierEffect(ActiveEffect):
    """
    Represents an active instance of a ModifierEffect applied to a character.
    """

    @property
    def modifier_effect(self) -> ModifierEffect:
        """
        Get the effect as a ModifierEffect (narrowed type for clarity).

        Raises:
            TypeError:
                If the effect is not a ModifierEffect.

        Returns:
            ModifierEffect:
                The effect cast as a ModifierEffect.

        """
        if not isinstance(self.effect, ModifierEffect):
            raise TypeError(f"Expected ModifierEffect, got {type(self.effect)}")
        return self.effect

    def get_projected_strength(self, bonus_type: BonusType) -> int:
        """
        Determine the strength of a specific modifier type.

        Args:
            bonus_type (BonusType):
                The bonus type to evaluate.

        Returns:
            int:
                The strength value of the modifier.
        """
        return self.modifier_effect.get_projected_strength(bonus_type, self.variables)

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
        return None

    def _on_turn_end(self, event: TurnEndEvent) -> EventResponse | None:
        """
        Update the effect for the current turn.
        """
        # Decrement duration and check for expiration
        remove_effect = False
        if self.duration is not None:
            self.duration -= 1
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
            message="",
        )
