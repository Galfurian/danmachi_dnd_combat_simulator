from typing import Any, Optional

from core.constants import get_effect_emoji, apply_character_type_color, apply_effect_color
from core.utils import cprint, roll_and_describe

from .base_effect import Effect


class HealingOverTimeEffect(Effect):
    """
    Heal over Time effect that heals the target each turn.

    Healing over Time effects continuously heal the target for a specified duration,
    using a heal expression that can include variables like MIND level.
    """

    def __init__(
        self,
        name: str,
        description: str,
        max_duration: int,
        heal_per_turn: str,
    ):
        super().__init__(name, description, max_duration)
        self.heal_per_turn = heal_per_turn

        self.validate()

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
        message = f"    {get_effect_emoji(self)} "
        message += apply_character_type_color(target.type, target.name)
        message += f" heals for {hot_value} ([white]{hot_desc}[/]) hp from "
        message += apply_effect_color(self, self.name) + "."
        cprint(message)

    def validate(self) -> None:
        """
        Validate the HoT effect's properties.

        Raises:
            AssertionError: If validation conditions are not met.
        """
        super().validate()
        assert self.max_duration > 0, "HealingOverTimeEffect duration must be greater than 0."
        assert isinstance(
            self.heal_per_turn, str
        ), "Heal per turn must be a string expression."
