from typing import Any, Optional

from core.constants import BonusType
from core.error_handling import log_error, log_warning, log_critical


class Effect:
    """
    Base class for all game effects that can be applied to characters.

    Effects can modify character stats, deal damage over time, provide healing,
    or trigger special behaviors under certain conditions.
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        max_duration: int = 0,
    ):
        # Validate inputs
        if not name or not isinstance(name, str):
            log_error(
                f"Effect name must be a non-empty string, got: {name}",
                {"name": name, "type": type(name).__name__},
            )
            raise ValueError(f"Invalid effect name: {name}")

        if not isinstance(description, str):
            log_warning(
                f"Effect description must be a string, got: {type(description).__name__}",
                {"name": name, "description": description},
            )
            description = str(description) if description is not None else ""

        if not isinstance(max_duration, int) or max_duration < 0:
            log_error(
                f"Effect max_duration must be a non-negative integer, got: {max_duration}",
                {"name": name, "max_duration": max_duration},
            )
            max_duration = max(
                0, int(max_duration) if isinstance(max_duration, (int, float)) else 0
            )

        self.name: str = name
        self.description: str = description
        self.max_duration: int = max_duration

    def turn_update(self, actor: Any, target: Any, mind_level: int = 0) -> None:
        """Update the effect for the current turn.

        Args:
            actor (Any): The character applying the effect.
            target (Any): The character receiving the effect.
            mind_level (int, optional): The mind level of the actor. Defaults to 0.
        """
        try:
            if not actor:
                log_error(
                    f"Actor cannot be None for effect {self.name}",
                    {"effect": self.name},
                )
                return

            if not target:
                log_error(
                    f"Target cannot be None for effect {self.name}",
                    {"effect": self.name},
                )
                return

            if not isinstance(mind_level, int) or mind_level < 0:
                log_warning(
                    f"Mind level must be non-negative integer for effect {self.name}, got: {mind_level}",
                    {"effect": self.name, "mind_level": mind_level},
                )
                mind_level = max(
                    0, int(mind_level) if isinstance(mind_level, (int, float)) else 0
                )

        except Exception as e:
            log_critical(
                f"Error during turn_update validation for effect {self.name}: {str(e)}",
                {
                    "effect": self.name,
                    "actor": getattr(actor, "name", "unknown"),
                    "target": getattr(target, "name", "unknown"),
                },
                e,
            )

    def is_permanent(self) -> bool:
        """Check if the effect is permanent (i.e., has no duration).

        Returns:
            bool: True if the effect is permanent, False otherwise.
        """
        return self.max_duration <= 0

    def validate(self) -> None:
        """
        Validate the effect's properties.

        Raises:
            ValueError: If any property validation fails.
        """
        try:
            if not self.name:
                log_error("Effect name must not be empty", {"name": self.name})
                raise ValueError("Effect name must not be empty")

            if not isinstance(self.description, str):
                log_warning(
                    f"Effect description must be a string, got {type(self.description).__name__}",
                    {"name": self.name, "description": self.description},
                )
                raise ValueError("Effect description must be a string")

        except Exception as e:
            if not isinstance(e, ValueError):
                log_critical(
                    f"Unexpected error during effect validation: {str(e)}",
                    {"effect": self.name},
                    e,
                )
            raise

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
                log_warning(
                    f"Actor cannot be None when checking if effect {self.name} can be applied",
                    {"effect": self.name},
                )
                return False

            if not target:
                log_warning(
                    f"Target cannot be None when checking if effect {self.name} can be applied",
                    {"effect": self.name},
                )
                return False

            return False  # Base implementation

        except Exception as e:
            log_error(
                f"Error checking if effect {self.name} can be applied: {str(e)}",
                {"effect": self.name},
                e,
            )
            return False

    def to_dict(self) -> dict[str, Any]:
        """Convert the effect to a dictionary representation."""
        # Import here to avoid circular imports
        from .effect_serialization import EffectSerializer
        return EffectSerializer.serialize(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Effect | None":
        """Creates an Effect instance from a dictionary representation.

        Args:
            data (dict[str, Any]): The dictionary representation of the effect.

        Returns:
            Effect: An instance of the Effect class.
        """
        # Import here to avoid circular imports
        from .effect_serialization import EffectDeserializer
        return EffectDeserializer.deserialize(data)


class Modifier:
    """
    Handles different types of modifiers that can be applied to characters.

    Modifiers represent bonuses or penalties to various character attributes
    such as HP, AC, damage, or other stats.
    """

    def __init__(self, bonus_type: BonusType, value: Any):
        self.bonus_type = bonus_type
        self.value = value
        self.validate()

    def validate(self) -> None:
        """
        Validate the modifier's properties.

        Raises:
            ValueError: If the bonus type or value is invalid.
            AssertionError: If validation conditions are not met.
        """
        from combat.damage import DamageComponent
        
        assert isinstance(
            self.bonus_type, BonusType
        ), f"Bonus type '{self.bonus_type}' must be of type BonusType."

        if self.bonus_type == BonusType.DAMAGE:
            assert isinstance(
                self.value, DamageComponent
            ), f"Modifier value for '{self.bonus_type}' must be a DamageComponent."
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

    def to_dict(self) -> dict[str, Any]:
        """Convert the modifier to a dictionary representation."""
        # Import here to avoid circular imports
        from .effect_serialization import ModifierSerializer
        return ModifierSerializer.serialize(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Modifier | None":
        """Create a Modifier instance from a dictionary representation."""
        # Import here to avoid circular imports
        from .effect_serialization import ModifierDeserializer
        return ModifierDeserializer.deserialize(data)

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
