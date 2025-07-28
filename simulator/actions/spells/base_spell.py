"""Base spell classes for the magical combat system."""

from abc import abstractmethod
from logging import debug
from typing import Any

from actions.base_action import BaseAction
from core.constants import ActionCategory, ActionType
from core.error_handling import (
    log_error,
    log_warning,
    log_critical,
    ensure_non_negative_int,
    ensure_string,
    ensure_list_of_type,
    safe_get_attribute,
    validate_required_object,
)
from core.utils import evaluate_expression
from effects.base_effect import Effect


class Spell(BaseAction):
    """Abstract base class for all magical spells in the combat system.

    This class provides a foundation for implementing various types of spells,
    such as offensive, healing, support, and debuff spells. It includes shared
    functionality like targeting, mind cost validation, and serialization, while
    requiring subclasses to implement specific behavior through abstract methods.
    """

    def __init__(
        self,
        name: str,
        action_type: ActionType,
        description: str,
        cooldown: int,
        maximum_uses: int,
        level: int,
        mind_cost: list[int],
        category: ActionCategory,
        target_expr: str = "",
        requires_concentration: bool = False,
        target_restrictions: list[str] | None = None,
    ):
        """Initialize a new Spell.
        
        Args:
            name (str): Display name of the spell.
            type (ActionType): Action type (ACTION, BONUS_ACTION, REACTION, etc.).
            description (str): Flavor text describing what the spell does.
            cooldown (int): Turns to wait before reusing (0 = no cooldown).
            maximum_uses (int): Max uses per encounter/day (-1 = unlimited).
            level (int): Base spell level (1-9 for most spells, 0 for cantrips).
            mind_cost (list[int]): List of mind point costs per casting level [level1, level2, ...].
            category (ActionCategory): Spell category (OFFENSIVE, HEALING, SUPPORT, DEBUFF).
            target_expr (str): Expression determining number of targets ("" = single target).
            requires_concentration (bool): Whether spell requires ongoing mental focus.
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

            # Validate level using helper
            self.level = ensure_non_negative_int(
                level, "spell level", 0, {"name": name}
            )

            # Validate mind_cost list using helper
            self.mind_cost = ensure_list_of_type(
                mind_cost,
                int,
                "mind cost",
                [0],
                converter=lambda x: (
                    max(0, int(x)) if isinstance(x, (int, float)) else 0
                ),
                validator=lambda x: isinstance(x, int) and x >= 0,
                context={"name": name},
            )

            # Validate target_expr using helper
            self.target_expr = ensure_string(
                target_expr, "target expression", "", {"name": name}
            )

            # Validate requires_concentration
            if not isinstance(requires_concentration, bool):
                log_warning(
                    f"Spell {name} requires_concentration must be boolean, got: {requires_concentration.__class__.__name__}, setting to False",
                    {"name": name, "requires_concentration": requires_concentration},
                )
                requires_concentration = False

            self.requires_concentration = requires_concentration

        except Exception as e:
            log_critical(
                f"Error initializing Spell {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

    # ============================================================================
    # TARGETING SYSTEM METHODS
    # ============================================================================

    def is_single_target(self) -> bool:
        """Check if the spell targets a single entity.
        
        Returns:
            bool: True if spell targets one entity, False for multi-target.
        """
        return not self.target_expr or self.target_expr.strip() == ""

    def target_count(self, actor: Any, mind_level: int) -> int:
        """Calculate the number of targets this spell can affect.
        
        Args:
            actor (Any): The character casting the spell (must have expression variables).
            mind_level (int): The spell level being used for casting.
        
        Returns:
            int: Number of targets (minimum 1, even for invalid expressions).
        """
        if self.target_expr:
            variables = actor.get_expression_variables()
            variables["MIND"] = mind_level
            # Evaluate the multi-target expression to get the number of targets.
            return evaluate_expression(self.target_expr, variables)
        return 1

    # ============================================================================
    # SPELL SYSTEM METHODS
    # ============================================================================

    def execute(self, actor: Any, target: Any) -> bool:
        """Execute spell - delegates to cast_spell method.
        
        Args:
            actor (Any): The character casting the spell.
            target (Any): The target of the spell.
        
        Returns:
            bool: Always False - use cast_spell() instead.
        
        Raises:
            NotImplementedError: Always raised to enforce using cast_spell().
        """
        raise NotImplementedError("Spells must use the cast_spell method.")

    @abstractmethod
    def cast_spell(self, actor: Any, target: Any, mind_level: int) -> bool:
        """Abstract method for casting spells with level-specific behavior.
        
        Args:
            actor (Any): The character casting the spell (must have mind points).
            target (Any): The character targeted by the spell.
            mind_level (int): The spell level to cast at (1-9, affects cost and power).
        
        Returns:
            bool: True if spell was cast successfully, False on failure.
        """
        if not self._validate_actor_and_target(actor, target):
            return False

        # Validate mind cost against the specified level.
        if mind_level not in self.mind_cost:
            log_error(
                f"{actor.name} cannot cast {self.name} at invalid level {mind_level}",
                {
                    "actor": actor.name,
                    "spell": self.name,
                    "mind_level": mind_level,
                    "valid_levels": self.mind_cost,
                },
            )
            return False

        # Check if actor has enough mind points to cast the spell.
        if actor.mind < mind_level:
            log_error(
                f"{actor.name} does not have enough mind to cast {self.name}",
                {
                    "actor": actor.name,
                    "spell": self.name,
                    "mind_level": mind_level,
                    "valid_levels": self.mind_cost,
                },
            )
            return False

        # Check cooldown restrictions.
        if actor.is_on_cooldown(self):
            log_warning(
                f"Cannot cast {self.name} - spell is on cooldown",
                {"actor": actor.name, "spell": self.name},
            )
            return False

        return True

    # ============================================================================
    # SERIALIZATION METHODS
    # ============================================================================

    def to_dict(self) -> dict[str, Any]:
        """Transform this Spell into a dictionary representation.
        
        Returns:
            dict[str, Any]: Dictionary representation of the spell.
        """
        from actions.spells.spell_serializer import SpellSerializer

        return SpellSerializer.serialize(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Any | None":
        """Create a Spell instance from a dictionary.
        
        Args:
            data (dict[str, Any]): Dictionary containing spell configuration data.
        
        Returns:
            Any | None: Spell instance or None if creation fails.
        """
        from actions.spells.spell_serializer import SpellDeserializer

        return SpellDeserializer.deserialize(data)
