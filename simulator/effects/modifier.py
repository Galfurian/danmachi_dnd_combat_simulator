from typing import Any, Union
from core.constants import BonusType
from combat.damage import DamageComponent


class Modifier:
    """Handles different types of modifiers that can be applied to characters."""

    def __init__(self, bonus_type: BonusType, value: Union[str, int, DamageComponent]):
        self.bonus_type = bonus_type
        self.value = value
        self.validate()

    def validate(self):
        """Validate the modifier's properties."""
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
        from .effect_factory import ModifierSerializer
        return ModifierSerializer.to_dict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Modifier":
        """Create a Modifier instance from a dictionary representation."""
        from .effect_factory import ModifierFactory
        return ModifierFactory.from_dict(data)

    def __eq__(self, other) -> bool:
        """Check if two modifiers are equal."""
        if not isinstance(other, Modifier):
            return False
        return self.bonus_type == other.bonus_type and self.value == other.value

    def __hash__(self) -> int:
        """Make the modifier hashable for use in sets and dictionaries."""
        if isinstance(self.value, DamageComponent):
            # For DamageComponent, use its string representation for hashing
            return hash(
                (self.bonus_type, self.value.damage_roll, self.value.damage_type)
            )
        return hash((self.bonus_type, self.value))

    def __repr__(self) -> str:
        """String representation of the modifier."""
        return f"Modifier({self.bonus_type.name}, {self.value})"
