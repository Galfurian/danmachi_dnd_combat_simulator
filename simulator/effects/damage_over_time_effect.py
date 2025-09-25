from typing import Any, Literal

from combat.damage import DamageComponent
from core.utils import VarInfo, cprint, roll_and_describe
from pydantic import Field

from .base_effect import ActiveEffect, Effect


class DamageOverTimeEffect(Effect):
    """
    Damage over Time effect that deals damage each turn.

    Damage over Time effects continuously damage the target for a specified duration,
    using a damage roll expression that can include variables like MIND level.
    """

    effect_type: Literal["DamageOverTimeEffect"] = "DamageOverTimeEffect"

    damage: DamageComponent = Field(
        description="Damage component defining the damage roll and type.",
    )

    @property
    def color(self) -> str:
        """Returns the color string for damage over time effects."""
        return "bold magenta"

    @property
    def emoji(self) -> str:
        """Returns the emoji for damage over time effects."""
        return "❣️"

    def model_post_init(self, _) -> None:
        if self.duration is None or self.duration <= 0:
            raise ValueError(
                "Duration must be a positive integer for DamageOverTimeEffect."
            )
        if not isinstance(self.damage, DamageComponent):
            raise ValueError("Damage must be of type DamageComponent.")
