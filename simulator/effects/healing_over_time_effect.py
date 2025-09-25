from typing import Any, Literal

from core.utils import VarInfo, cprint, roll_and_describe
from pydantic import Field

from .base_effect import ActiveEffect, Effect


class HealingOverTimeEffect(Effect):
    """
    Heal over Time effect that heals the target each turn.

    Healing over Time effects continuously heal the target for a specified duration,
    using a heal expression that can include variables like MIND level.
    """

    effect_type: Literal["HealingOverTimeEffect"] = "HealingOverTimeEffect"

    heal_per_turn: str = Field(
        description="Heal expression defining the heal amount per turn.",
    )

    @property
    def color(self) -> str:
        """Returns the color string for healing over time effects."""
        return "bold green"

    @property
    def emoji(self) -> str:
        """Returns the emoji for healing over time effects."""
        return "💚"

    def model_post_init(self, _) -> None:
        if self.duration is None or self.duration <= 0:
            raise ValueError(
                "Duration must be a positive integer for HealingOverTimeEffect."
            )
        if not isinstance(self.heal_per_turn, str):
            raise ValueError("Heal per turn must be a string expression.")
