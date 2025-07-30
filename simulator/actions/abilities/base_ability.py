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
    apply_character_type_color,
    get_effect_color,
)
from catchery import *
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

    def __init__(
        self,
        name: str,
        action_type: ActionType,
        category: ActionCategory,
        description: str,
        cooldown: int,
        maximum_uses: int,
        effect: Effect | None = None,
        target_expr: str = "",
        target_restrictions: list[str] | None = None,
    ):
        """Initialize a new BaseAbility.

        Args:
            name (str): Display name of the ability.
            action_type (ActionType): Action type (STANDARD, BONUS, REACTION, etc.).
            category (ActionCategory): Action category (OFFENSIVE, HEALING, BUFF, UTILITY, etc.).
            description (str): Flavor text describing what the ability does.
            cooldown (int): Turns to wait before reusing (0 = no cooldown).
            maximum_uses (int): Max uses per encounter/day (-1 = unlimited).
            effect (Effect | None): Optional effect applied to targets on use.
            target_expr (str): Expression determining number of targets ("" = single target).
            target_restrictions (list[str] | None): Override default targeting if needed.

        Raises:
            ValueError: If name is empty or type/category are invalid.
        """
        try:
            super().__init__(
                name,
                action_type,
                category,
                description,
                cooldown,
                maximum_uses,
                target_restrictions,
            )

            # Validate the effect.
            self.effect: Effect | None = ensure_effect(
                effect,
                "BaseAbility effect",
                None,
                {"name": name},
            )
            # Validate the target expression.
            self.target_expr = ensure_string(
                target_expr, "target expression", "", {"name": name}
            )

        except Exception as e:
            log_critical(
                f"Error initializing BaseAbility {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
                True,
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

    # ============================================================================
    # SERIALIZATION METHODS
    # ============================================================================

    def to_dict(self) -> dict[str, Any]:
        """Convert this ability to a dictionary representation.

        Returns:
            dict[str, Any]: Dictionary representation of the ability.
        """
        from actions.abilities.ability_serializer import AbilitySerializer

        return AbilitySerializer.serialize(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Any | None":
        """Create an ability instance from dictionary data.

        Args:
            data (dict[str, Any]): Dictionary containing ability configuration data.

        Returns:
            Any | None: Ability instance or None if creation fails.
        """
        from actions.abilities.ability_serializer import AbilityDeserializer

        return AbilityDeserializer.deserialize(data)
