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
from pydantic import BaseModel, Field

from .base_effect import ActiveEffect, Effect


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

    def model_post_init(self, _: Any) -> None:
        from combat.damage import DamageComponent

        if self.bonus_type == BonusType.DAMAGE:
            self.value = DamageComponent(**self.value)
        elif self.bonus_type == BonusType.ATTACK:
            assert isinstance(
                self.value, str
            ), f"Modifier value for '{self.bonus_type}' must be a string expression."
        elif self.bonus_type in [
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
        else:
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

    def get_modifier_strength(
        self,
        bonus_type: BonusType,
        variables: list[VarInfo],
    ) -> int:
        """
        Helper to determine the strength of a modifier for comparison purposes.

        Args:
            ae (ActiveEffect): The active effect to evaluate.
            bonus_type (BonusType): The bonus type to check.

        Returns:
            int: The strength value of the modifier.
        """
        # Find the modifier for the specific bonus type
        modifier = None
        for mod in self.modifiers:
            if mod.bonus_type == bonus_type:
                modifier = mod
                break

        if not modifier:
            return 0

        if bonus_type in [
            BonusType.HP,
            BonusType.MIND,
            BonusType.AC,
            BonusType.INITIATIVE,
        ]:
            if isinstance(modifier.value, int):
                return modifier.value
            if isinstance(modifier.value, str):
                return int(modifier.value)
            return 0
        if bonus_type == BonusType.ATTACK:
            if isinstance(modifier.value, str):
                return get_max_roll(modifier.value, variables)
            return (
                get_max_roll(str(modifier.value), variables)
                if isinstance(modifier.value, int)
                else 0
            )
        if bonus_type == BonusType.DAMAGE:
            if isinstance(modifier.value, DamageComponent):
                return get_max_roll(modifier.value.damage_roll, variables)
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
            self_strength = self.get_modifier_strength(bonus_type, variables)
            other_strength = other.get_modifier_strength(bonus_type, variables)
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
    ) -> None:
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
            ActiveEffect | None:
                The new ActiveEffect if applied successfully, None otherwise.

        """
        from character.main import Character
        from combat.damage import DamageComponent

        if not self.can_apply(actor, target, variables):
            return None

        assert isinstance(actor, Character), "Actor must be a Character."
        assert isinstance(target, Character), "Target must be a Character."

        # Check if this one is stronger than at least one existing effect.
        weaker_found = False

        for modifier in self.modifiers:
            bonus_type = modifier.bonus_type

            # Find existing effect with this bonus_type.
            existing_effects = [
                ae
                for ae in target.effects.modifier_effects
                if any(m.bonus_type == bonus_type for m in ae.modifier_effect.modifiers)
            ]

            # Just check if there is at least one existing effect that is
            # weaker.
            for existing in existing_effects:
                if self.is_stronger_than(existing.modifier_effect, variables):
                    weaker_found = True
                    break

            if weaker_found:
                break

        if not weaker_found:
            log_debug(
                f"Not applying modifier effect '{self.colored_name}' "
                f"from {actor.colored_name} to {target.colored_name}: "
                "No existing weaker effect found."
            )
            return None

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

    def turn_update(self) -> None:
        """
        Update the effect for the current turn by calling the effect's
        turn_update method.
        """
