from typing import Any, Optional

from core.constants import BonusType
from pydantic import BaseModel, Field, model_validator


class Effect(BaseModel):
    """
    Base class for all game effects that can be applied to characters.

    Effects can modify character stats, deal damage over time, provide healing,
    or trigger special behaviors under certain conditions.
    """

    name: str = Field(
        description="The name of the effect.",
    )
    description: str = Field(
        "",
        description="A brief description of the effect.",
    )
    duration: int | None = Field(
        default=None,
        description=(
            "The duration of the effect in turns. "
            "None for permanent effects, 0 for instant effects."
        ),
    )

    def turn_update(self, actor: Any, target: Any, mind_level: int = 0) -> None:
        """Update the effect for the current turn.

        Args:
            actor (Any): The character applying the effect.
            target (Any): The character receiving the effect.
            mind_level (int, optional): The mind level of the actor. Defaults to 0.
        """
        try:
            if not actor:
                print(
                    f"Actor cannot be None for effect {self.name}",
                    {"effect": self.name},
                )
                return

            if not target:
                print(
                    f"Target cannot be None for effect {self.name}",
                    {"effect": self.name},
                )
                return

            if not isinstance(mind_level, int) or mind_level < 0:
                print(
                    f"Mind level must be non-negative integer for effect {self.name}, got: {mind_level}",
                    {"effect": self.name, "mind_level": mind_level},
                )
                mind_level = max(
                    0, int(mind_level) if isinstance(mind_level, (int, float)) else 0
                )

        except Exception as e:
            print(
                f"Error during turn_update validation for effect {self.name}: {str(e)}",
                {
                    "effect": self.name,
                    "actor": getattr(actor, "name", "unknown"),
                    "target": getattr(target, "name", "unknown"),
                },
                e,
            )

    def is_permanent(self) -> bool:
        """Check if the effect is permanent (i.e., has no duration limit).

        Returns:
            bool: True if the effect is permanent (None duration) or instant (0 duration), False otherwise.
        """
        return self.duration is None or self.duration <= 0

    def can_apply(self, actor: Any, target: Any) -> bool:
        """Check if the effect can be applied to the target.

        Args:
            actor (Any): The character applying the effect.
            target (Any): The character receiving the effect.

        Returns:
            bool: True if the effect can be applied, False otherwise.
        """
        try:
            if not actor:
                print(
                    f"Actor cannot be None when checking if effect {self.name} can be applied",
                    {"effect": self.name},
                )
                return False

            if not target:
                print(
                    f"Target cannot be None when checking if effect {self.name} can be applied",
                    {"effect": self.name},
                )
                return False

            return False  # Base implementation

        except Exception as e:
            print(
                f"Error checking if effect {self.name} can be applied: {str(e)}",
                {"effect": self.name},
                e,
            )
            return False


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

    @model_validator(mode="after")
    def check_bonus_type(self) -> Any:
        from combat.damage import DamageComponent

        if self.bonus_type == BonusType.DAMAGE:
            assert isinstance(
                self.value, DamageComponent
            ), f"Modifier value for '{self.bonus_type}' must be a DamageComponent."
            return self

        if self.bonus_type == BonusType.ATTACK:
            assert isinstance(
                self.value, str
            ), f"Modifier value for '{self.bonus_type}' must be a string expression."
            return self

        if self.bonus_type in [
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
            return self

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


def ensure_effect(
    effect: Any,
    name: str,
    default: Effect | None = None,
    context: dict[str, Any] | None = None,
) -> Any:
    if effect is not None and not isinstance(effect, Effect):
        print(
            f"{name} must be either Effect or None, got: {type(effect).__name__}, setting to {default}",
            {
                **(context or {}),
                "effect_type": type(effect).__name__,
            },
        )
        effect = default
    return effect
