"""Base ability class for all special character abilities."""

from abc import ABC, abstractmethod
from typing import Any

from core.utils import (
    evaluate_expression,
)
from pydantic import Field

from actions.base_action import BaseAction


class BaseAbility(BaseAction, ABC):
    """Abstract base class for all character abilities and special powers.

    This class provides a foundation for implementing various types of abilities,
    such as offensive, healing, buff, and utility abilities. It includes shared
    functionality like targeting and serialization, while requiring subclasses
    to implement specific behavior through abstract methods.
    """

    # ============================================================================
    # TARGETING SYSTEM METHODS (SHARED BY ALL ABILITIES)
    # ============================================================================

    def is_single_target(self) -> bool:
        """Check if the ability targets a single entity.

        Returns:
            bool: True if ability targets one entity, False for multi-target.

        """
        return not self.target_expr or self.target_expr.strip() == ""

    # ============================================================================
    # ABSTRACT METHODS (MUST BE IMPLEMENTED BY SUBCLASSES)
    # ============================================================================

    @abstractmethod
    def execute(self, actor: Any, target: Any) -> bool:
        """Execute this ability against a target.

        Args:
            actor (Any): The character using the ability.
            target (Any): The target character.

        Returns:
            bool: True if ability was executed successfully, False on system errors.

        """


def deserialize_ability(data: dict[str, Any]) -> BaseAbility | None:
    """Deserialize a dictionary into a BaseAbility instance.

    Args:
        data (dict[str, Any]): The dictionary representation of the ability.

    Returns:
        BaseAbility | None: The deserialized ability instance, or None if deserialization fails.

    """
    from actions.abilities.ability_buff import AbilityBuff
    from actions.abilities.ability_debuff import AbilityDebuff
    from actions.abilities.ability_heal import AbilityHeal
    from actions.abilities.ability_offensive import AbilityOffensive

    ability_type = data.get("ability_type", None)

    if ability_type == "AbilityBuff":
        return AbilityBuff(**data)
    if ability_type == "AbilityDebuff":
        return AbilityDebuff(**data)
    if ability_type == "AbilityHeal":
        return AbilityHeal(**data)
    if ability_type == "AbilityOffensive":
        return AbilityOffensive(**data)

    return None
