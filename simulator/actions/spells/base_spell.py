"""
Base spell module for the simulator.

Defines the base classes for spells, including offensive, defensive,
healing, and buff spells, with common functionality for casting and effects.
"""

from abc import abstractmethod
from typing import Any

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
    def cast_spell(
        self,
        actor: Any,
        target: Any,
        rank: int,
    ) -> bool:
        """
        Abstract method for casting spells with level-specific behavior.

        Args:
            actor (Any):
                The character casting the spell (must have mind points).
            target (Any):
                The character targeted by the spell.
            rank (int):
                The rank at which the spell is being cast.

        Returns:
            bool:
                True if spell was cast successfully, False on failure.

        """
        from character.main import Character

        if not isinstance(actor, Character):
            raise ValueError("The actor must be a Character instance.")
        if not isinstance(target, Character):
            raise ValueError("The target must be a Character instance.")
        if rank < 0 or rank >= len(self.mind_cost):
            raise ValueError("Rank is out of bounds for this spell.")

        # Check if the ability is on cooldown.
        if actor.actions.is_on_cooldown(self):
            return False

        # Check if actor has enough mind points to cast the spell.
        if actor.stats.mind < self.mind_cost[rank]:
            return False

        return True

    # ============================================================================
    # EFFECT ANALYSIS METHODS
    # ============================================================================

    def spell_get_variables(self, actor: Any, rank: int) -> list[VarInfo]:
        """
        Get a list of variables used in spell expressions.

        Args:
            actor (Any): The character casting the spell.
            rank (int): The rank at which the spell is being cast.

        Returns:
            list[VarInfo]: A list of VarInfo objects representing the variables.

        """
        from character.main import Character

        assert isinstance(actor, Character), "Actor must be an object"
        assert rank >= 0, "Rank must be non-negative"
        assert rank < len(self.mind_cost), "Rank exceeds available mind cost levels"

        # Get the mind cost for the specified rank.
        mind_level = self.mind_cost[rank]
        # Prepare variables for substitution.
        variables = actor.get_expression_variables()
        variables.append(VarInfo(name="MIND", value=mind_level))
        variables.append(VarInfo(name="RANK", value=rank + 1))
        return variables

    def get_modifier_expressions(
        self,
        actor: Any,
        rank: int = 0,
    ) -> dict[BonusType, str]:
        """
        Get modifier expressions with variables substituted for display.

        Args:
            actor (Any):
                The character casting the spell.
            rank (int):
                The rank at which the spell is being cast.

        Returns:
            dict[BonusType, str]:
                Dictionary mapping bonus types to their expressions.

        """
        from combat.damage import DamageComponent
        from effects.modifier_effect import ModifierEffect

        # Find the first ModifierEffect in the effects list
        modifier_effect = None
        for effect in self.effects:
            if isinstance(effect, ModifierEffect):
                modifier_effect = effect
                break

        if modifier_effect is None:
            raise ValueError("BaseSpell must have at least one ModifierEffect")

        expressions: dict[BonusType, str] = {}

        for modifier in modifier_effect.modifiers:
            bonus_type = modifier.bonus_type
            value = modifier.value
            if isinstance(value, DamageComponent):
                expressions[bonus_type] = self._spell_substitute_variables(
                    value.damage_roll,
                    actor,
                    rank,
                )
            elif isinstance(value, str):
                expressions[bonus_type] = self._spell_substitute_variables(
                    value,
                    actor,
                    rank,
                )
            else:
                expressions[bonus_type] = str(value)

        return expressions

    def _spell_apply_effects(
        self,
        actor: Any,
        target: Any,
        effects: list[ValidActionEffect],
        rank: int,
    ) -> tuple[list[ValidActionEffect], list[ValidActionEffect]]:
        """
        Apply the spell's effects to the target.

        Args:
            actor (Any):
                The character casting the spell.
            target (Any):
                The character targeted by the spell.
            rank (int):
                The rank at which the spell is being cast.

        Returns:
            tuple[list[ValidActionEffect], list[ValidActionEffect]]:
                A tuple containing two lists:
                - First list: effects that were successfully applied.
                - Second list: effects that were not applied (e.g., resisted).

        """
        return self._common_apply_effects(
            actor=actor,
            target=target,
            effects=effects,
            variables=self.spell_get_variables(
                actor,
                rank,
            ),
        )

    def _spell_roll_damage_components(
        self,
        actor: Any,
        target: Any,
        rank: int,
        components: list[DamageComponent],
    ) -> tuple[int, list[str]]:
        """
        Roll and describe a list of damage components for spell calculations.

        Args:
            actor (Any):
                The character casting the spell.
            target (Any):
                The character being attacked.
            rank (int):
                The rank at which the spell is being cast.
            components (list[DamageComponent]):
                The list of damage components to roll.

        Returns:
            tuple[int, str]:
                A tuple containing the total damage and a detailed description string.

        """
        return roll_damage_components(
            actor,
            target,
            components,
            self.spell_get_variables(
                actor,
                rank,
            ),
        )

    def _spell_roll_and_describe(
        self,
        expression: str,
        actor: Any,
        rank: int,
    ) -> RollBreakdown:
        """
        Evaluate, roll, and describe an expression for spell calculations.

        Args:
            expression (str):
                The expression to evaluate.
            actor (Any):
                The character casting the spell.
            rank (int):
                The rank at which the spell is being cast.

        Returns:
            RollBreakdown:
                The result and breakdown of the rolled expression.

        """
        return roll_and_describe(
            self._spell_substitute_variables(
                expression,
                actor,
                rank,
            )
        )

    def _spell_roll_dice_expression(
        self,
        expression: str,
        actor: Any,
        rank: int,
    ) -> int:
        """
        Evaluate and roll an expression for spell calculations.

        Args:
            expression (str):
                The expression to evaluate.
            actor (Any):
                The character casting the spell.
            rank (int):
                The rank at which the spell is being cast.

        Returns:
            int:
                The result of the rolled expression.

        """
        return roll_dice_expression(
            self._spell_substitute_variables(
                expression,
                actor,
                rank,
            ),
        )

    def _spell_substitute_variables(
        self,
        expression: str,
        actor: Any,
        rank: int,
    ) -> str:
        """
        Substitute variables in an expression for spell calculations.

        Args:
            expression (str): The expression to modify.
            actor (Any): The character casting the spell.
            rank (int): The rank at which the spell is being cast.

        Returns:
            str: The modified expression with substituted variables.

        """
        from core.dice_parser import substitute_variables

        # Evaluate and roll the expression.
        return substitute_variables(
            expression,
            self.spell_get_variables(
                actor,
                rank,
            ),
        )


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
