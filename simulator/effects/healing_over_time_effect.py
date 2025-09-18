from typing import Any, Optional

from core.utils import cprint, roll_and_describe
from pydantic import Field, model_validator

from .base_effect import Effect


class HealingOverTimeEffect(Effect):
    """
    Heal over Time effect that heals the target each turn.

    Healing over Time effects continuously heal the target for a specified duration,
    using a heal expression that can include variables like MIND level.
    """

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

    @model_validator(mode="after")
    def check_duration(self) -> Any:
        if self.duration is None or self.duration <= 0:
            raise ValueError(
                "Duration must be a positive integer for HealingOverTimeEffect."
            )
        return self

    @model_validator(mode="after")
    def check_heal_per_turn(self) -> Any:
        if not isinstance(self.heal_per_turn, str):
            raise ValueError("Heal per turn must be a string expression.")
        return self

    def turn_update(
        self, actor: Any, target: Any, mind_level: Optional[int] = 1
    ) -> None:
        """
        Apply healing over time to the target.

        Args:
            actor (Any): The character who applied the HoT effect.
            target (Any): The character receiving the healing.
            mind_level (Optional[int]): The mind level for healing calculation. Defaults to 1.
        """
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        # Calculate the heal amount using the provided expression.
        hot_value, hot_desc, _ = roll_and_describe(self.heal_per_turn, variables)
        # Assert that the heal value is a positive integer.
        assert (
            isinstance(hot_value, int) and hot_value >= 0
        ), f"HealingOverTimeEffect '{self.name}' must have a non-negative integer heal value, got {hot_value}."
        # Apply the heal to the target.
        hot_value = target.heal(hot_value)
        # If the heal value is positive, print the heal message.
        message = f"    {self.emoji} "
        message += target.char_type.colorize(target.name)
        message += f" heals for {hot_value} ([white]{hot_desc}[/]) hp from "
        message += self.colorize(self.name) + "."
        cprint(message)
