"""
Base spell module for the simulator.

Defines the base classes for spells, including offensive, defensive,
healing, and buff spells, with common functionality for casting and effects.
"""

from typing import TYPE_CHECKING, Any

from actions.base_action import BaseAction, ValidActionEffect
from combat.damage import (
    DamageComponent,
    roll_damage_components,
)
from core.constants import BonusType
from core.dice_parser import (
    RollBreakdown,
    VarInfo,
    roll_and_describe,
    roll_dice_expression,
)
from pydantic import Field

if TYPE_CHECKING:
    from character.main import Character


class BaseSpell(BaseAction):
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

    requires_concentration: bool = Field(
        default=False,
        description="Whether the spell requires concentration to maintain.",
    )

    def model_post_init(self, _: Any) -> None:
        """Validates fields after model initialization."""
        if not self.mind_cost or not isinstance(self.mind_cost, list):
            raise ValueError("mind_cost must be a non-empty list of integers")
        for cost in self.mind_cost:
            if not isinstance(cost, int) or cost < 1:
                raise ValueError("Each mind cost must be a positive integer")

    @property
    def colored_name(self) -> str:
        """
        Returns the colored name of the attack for display purposes.
        """
        return f"[bold magenta]{self.name}[/]"

    # ============================================================================
    # TARGETING SYSTEM METHODS
    # ============================================================================

    def is_single_target(self) -> bool:
        """Check if the spell targets a single entity.

        Returns:
            bool: True if spell targets one entity, False for multi-target.

        """
        return not self.target_expr or self.target_expr.strip() == ""

    # ============================================================================
    # SPELL SYSTEM METHODS
    # ============================================================================

    def execute(
        self,
        actor: "Character",
        target: "Character",
        **kwargs: Any,
    ) -> bool:
        """
        Execute this spell against a target.

        Args:
            actor (Any):
                The character performing the action.
            target (Any):
                The character being targeted.
            **kwargs (Any):
                Additional parameters for action execution.

        Returns:
            bool:
                True if action executed successfully, False otherwise.

        """

        if not super().execute(actor, target, **kwargs):
            return False

        # Get the rank from kwargs, defaulting to None if not provided.
        rank: int | None = kwargs.get("rank", None)
        if not isinstance(rank, int):
            raise ValueError("Rank must be an integer.")
        if rank < 0 or rank >= len(self.mind_cost):
            raise ValueError("Rank is out of bounds for this spell.")
        # Check if actor has enough mind points to cast the spell.
        if actor.stats.mind < self.mind_cost[rank]:
            return False

        # Call the subclass-specific spell execution logic.
        return self._execute_spell(actor, target, self.spell_get_variables(actor, rank))

    def _execute_spell(
        self,
        actor: "Character",
        target: "Character",
        variables: list[VarInfo],
    ) -> bool:
        """
        Common logic for executing a spell after validation.

        Args:
            actor (Any):
                The character casting the spell.
            target (Any):
                The character being targeted.
            variables (list[VarInfo]):
                List of variables for expression evaluation.

        Returns:
            bool:
                True if action executed successfully, False otherwise.

        """
        raise NotImplementedError("execute_spell must be implemented by subclasses")

    # ============================================================================
    # EFFECT ANALYSIS METHODS
    # ============================================================================

    def spell_get_variables(
        self,
        actor: "Character",
        rank: int,
    ) -> list[VarInfo]:
        """
        Get a list of variables used in spell expressions.

        Args:
            actor (Character):
                The character casting the spell.
            rank (int):
                The rank at which the spell is being cast.

        Returns:
            list[VarInfo]: A list of VarInfo objects representing the variables.

        """
        # Get the mind cost for the specified rank.
        mind_level = self.mind_cost[rank]
        # Prepare variables for substitution.
        variables = actor.get_expression_variables()
        variables.append(VarInfo(name="MIND", value=mind_level))
        variables.append(VarInfo(name="RANK", value=rank + 1))
        return variables


def deserialize_spell(data: dict[str, Any]) -> BaseSpell | None:
    """Deserialize a dictionary into a BaseSpell instance.

    Args:
        data (dict[str, Any]): The dictionary representation of the spell.

    Returns:
        BaseSpell | None: The deserialized BaseSpell instance, or None on failure.

    """
    from actions.spells.spell_buff import SpellBuff
    from actions.spells.spell_debuff import SpellDebuff
    from actions.spells.spell_heal import SpellHeal
    from actions.spells.spell_offensive import SpellOffensive

    action_type = data.get("action_type")

    if action_type == "SpellOffensive":
        return SpellOffensive(**data)
    if action_type == "SpellHeal":
        return SpellHeal(**data)
    if action_type == "SpellBuff":
        return SpellBuff(**data)
    if action_type == "SpellDebuff":
        return SpellDebuff(**data)

    return None
