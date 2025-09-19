"""Base spell classes for the magical combat system."""

from abc import abstractmethod
from typing import Any

from core.constants import BonusType
from core.utils import evaluate_expression
from pydantic import Field, model_validator

from actions.base_action import BaseAction


class Spell(BaseAction):
    """Abstract base class for all magical spells in the combat system.

    This class provides a foundation for implementing various types of spells,
    such as offensive, healing, support, and debuff spells. It includes shared
    functionality like targeting, mind cost validation, and serialization, while
    requiring subclasses to implement specific behavior through abstract methods.
    """

    level: int = Field(
        default=0,
        description="The level of the spell.",
        ge=0,
    )

    mind_cost: list[int] = Field(
        default_factory=list,
        description="List of mind costs for casting the spell at different levels.",
    )

    target_expr: str = Field(
        default="",
        description=(
            "Expression defining the number of targets the spell can affect. "
            "If empty, the spell targets a single entity. "
            "Expressions can use variables like 'MIND' for the caster's spell level."
        ),
    )

    requires_concentration: bool = Field(
        default=False,
        description="Whether the spell requires concentration to maintain.",
    )

    @model_validator(mode="after")
    def validate_fields(self) -> "Spell":
        """Validates fields after model initialization."""
        if not self.mind_cost or not isinstance(self.mind_cost, list):
            raise ValueError("mind_cost must be a non-empty list of integers")
        for cost in self.mind_cost:
            if not isinstance(cost, int) or cost < 1:
                raise ValueError("Each mind cost must be a positive integer")
        return self

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
        from character.main import Character

        assert actor is not None, "Actor is required"
        assert isinstance(actor, Character), "Actor must be an object"
        assert target is not None, "Target is required"
        assert isinstance(target, Character), "Target must be an object"

        # Validate mind cost against the specified level.
        if mind_level not in self.mind_cost:
            print(
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
            print(
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
            print(
                f"Cannot cast {self.name} - spell is on cooldown",
                {"actor": actor.name, "spell": self.name},
            )
            return False

        return True

    # ============================================================================
    # EFFECT ANALYSIS METHODS
    # ============================================================================

    def get_modifier_expressions(
        self,
        actor: Any,
        mind_level: int = 1,
    ) -> dict[BonusType, str]:
        """
        Get modifier expressions with variables substituted for display.

        Args:
            actor (Any):
                The character casting the spell.
            mind_level (int):
                The spell level to use for MIND variable substitution.

        Returns:
            dict[BonusType, str]:
                Dictionary mapping bonus types to their expressions.

        """
        from effects.modifier_effect import ModifierEffect
        from combat.damage import DamageComponent
        from core.utils import substitute_variables

        assert isinstance(self.effect, ModifierEffect)
        assert mind_level >= 1

        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        expressions: dict[BonusType, str] = {}

        for modifier in self.effect.modifiers:
            bonus_type = modifier.bonus_type
            value = modifier.value
            if isinstance(value, DamageComponent):
                expressions[bonus_type] = substitute_variables(
                    value.damage_roll, variables
                )
            elif isinstance(value, str):
                expressions[bonus_type] = substitute_variables(value, variables)
            else:
                expressions[bonus_type] = str(value)

        return expressions


def deserialize_spell(data: dict[str, Any]) -> Spell | None:
    """Deserialize a dictionary into a Spell instance.

    Args:
        data (dict[str, Any]): The dictionary representation of the spell.

    Returns:
        Spell | None: The deserialized Spell instance, or None on failure.

    """
    from actions.spells.spell_buff import SpellBuff
    from actions.spells.spell_debuff import SpellDebuff
    from actions.spells.spell_heal import SpellHeal
    from actions.spells.spell_offensive import SpellOffensive

    ability_type = data.get("ability_type", None)

    if ability_type == "SpellOffensive":
        return SpellOffensive(**data)
    if ability_type == "SpellHeal":
        return SpellHeal(**data)
    if ability_type == "SpellBuff":
        return SpellBuff(**data)
    if ability_type == "SpellDebuff":
        return SpellDebuff(**data)

    return None
