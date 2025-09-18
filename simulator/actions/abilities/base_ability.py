"""Base ability class for all special character abilities."""

from abc import ABC, abstractmethod
from typing import Any

from actions.base_action import BaseAction
from combat.damage import DamageComponent, roll_damage_components_no_mind
from core.constants import (
    ActionCategory,
    ActionType,
    BonusType,
    GLOBAL_VERBOSE_LEVEL,
)
from pydantic import Field
from core.utils import (
    debug,
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    substitute_variables,
    cprint,
    evaluate_expression,
)
from effects.base_effect import Effect, ensure_effect


class BaseAbility(BaseAction, ABC):
    """Abstract base class for all character abilities and special powers.

    This class provides a foundation for implementing various types of abilities,
    such as offensive, healing, buff, and utility abilities. It includes shared
    functionality like targeting and serialization, while requiring subclasses
    to implement specific behavior through abstract methods.
    """

    effect: Effect | None = Field(
        None,
        description="Effect applied by this ability (if any)",
    )
    target_expr: str = Field(
        "",
        description="Expression defining number of targets.",
    )

    # ============================================================================
    # TARGETING SYSTEM METHODS (SHARED BY ALL ABILITIES)
    # ============================================================================

    def is_single_target(self) -> bool:
        """Check if the ability targets a single entity.

        Returns:
            bool: True if ability targets one entity, False for multi-target.
        """
        return not self.target_expr or self.target_expr.strip() == ""

    def target_count(self, actor: Any) -> int:
        """Calculate the number of targets this ability can affect.

        Args:
            actor (Any): The character using the ability.

        Returns:
            int: Number of targets (minimum 1, even for invalid expressions).
        """
        if self.target_expr:
            variables = actor.get_expression_variables()
            return max(1, int(evaluate_expression(self.target_expr, variables)))
        return 1

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
        pass


def deserialze_ability(data: dict[str, Any]) -> BaseAbility | None:
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

    if "class" not in data:
        raise ValueError("Missing 'class' in ability data")

    if data["class"] == "AbilityBuff":
        return AbilityBuff(**data)
    if data["class"] == "AbilityDebuff":
        return AbilityDebuff(**data)
    if data["class"] == "AbilityHeal":
        return AbilityHeal(**data)
    if data["class"] == "AbilityOffensive":
        return AbilityOffensive(**data)

    return None
