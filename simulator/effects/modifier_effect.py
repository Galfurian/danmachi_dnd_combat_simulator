"""
Modifier effect module for the simulator.

Defines effects that modify character stats, such as bonuses or penalties to
attributes, AC, or other properties.
"""

from typing import Any, Literal

from core.constants import BonusType
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

    def model_post_init(self, _) -> None:
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

    def model_post_init(self, _) -> None:
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
