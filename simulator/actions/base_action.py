from typing import Any, Union

from combat.damage import DamageComponent, roll_and_describe, roll_damage_components
from core.constants import (
    ActionCategory,
    ActionClass,
    is_oponent,
)
from core.utils import (
    GameException,
    RollBreakdown,
    VarInfo,
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    substitute_variables,
)
from effects import Effect
from effects.damage_over_time_effect import DamageOverTimeEffect
from effects.damage_over_time_effect import DamageOverTimeEffect
from effects.incapacitating_effect import IncapacitatingEffect
from effects.modifier_effect import ModifierEffect
from effects.trigger_effect import TriggerEffect
from pydantic import BaseModel, Field


class BaseAction(BaseModel):
    """Base class for all character actions in the combat system.

    This class provides a foundation for implementing various types of actions,
    such as attacks, spells, and utility abilities. It includes methods for
    validation, targeting, and effect application, as well as utility methods
    for damage calculation and serialization.
    """

    name: str = Field(
        description="Name of the action",
    )
    action_class: ActionClass = Field(
        description="Class of action (e.g., ACTION, BONUS_ACTION)",
    )
    category: ActionCategory = Field(
        description="Category of the action (e.g., OFFENSIVE, HEALING)",
    )
    description: str = Field(
        default="No description.",
        description="Description of the action",
    )
    target_expr: str = Field(
        default="",
        description="Expression defining number of targets.",
    )
    cooldown: int = Field(
        default=-1,
        ge=-1,
        description="Cooldown period in turns (-1 for no cooldown)",
    )
    maximum_uses: int = Field(
        default=-1,
        ge=-1,
        description="Maximum number of uses per encounter/day (-1 for unlimited)",
    )
    target_restrictions: list[str] = Field(
        default_factory=list,
        description="Restrictions on valid targets",
    )
    effect: Union[
        DamageOverTimeEffect,
        ModifierEffect,
        IncapacitatingEffect,
        TriggerEffect,
        None,
    ] = Field(
        default=None,
        description="An optional beneficial effect that this ability applies.",
    )

    def execute(self, actor: Any, target: Any) -> bool:
        """Execute the action against a target character.

        Args:
            actor (Any): The character performing the action.
            target (Any): The character being targeted.

        Returns:
            bool: True if action executed successfully, False otherwise.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.

        """
        raise NotImplementedError("Subclasses must implement the execute method")

    # ===========================================================================
    # GENERIC METHODS
    # ===========================================================================

    def has_limited_uses(self) -> bool:
        """
        Check if the action has limited uses.

        Returns:
            bool:
                True if maximum uses is greater than 0, False if unlimited.

        """
        return self.maximum_uses > 0

    def get_maximum_uses(self) -> int:
        """
        Get the maximum number of uses for this action.

        Returns:
            int:
                Maximum uses per encounter/day (-1 for unlimited).

        """
        return self.maximum_uses

    def target_count(self, variables: list[VarInfo] = []) -> int:
        """
        Calculate the number of targets this ability can affect.

        Args:
            actor (Any):
                The character using the ability.

        Returns:
            int:
                Number of targets (minimum 1, even for invalid expressions).

        """
        from core.utils import evaluate_expression

        if self.target_expr:
            return max(1, int(evaluate_expression(self.target_expr, variables)))
        return 1

    def has_cooldown(self) -> bool:
        """
        Check if the action has a cooldown period.

        Returns:
            bool:
                True if cooldown is greater than 0, False otherwise.

        """
        return self.cooldown > 0

    def get_cooldown(self) -> int:
        """
        Get the cooldown period for this action.

        Returns:
            int:
                Cooldown period in turns (-1 for no cooldown).

        """
        return self.cooldown

    # ============================================================================
    # EFFECT SYSTEM METHODS
    # ============================================================================

    def _common_apply_effect(
        self,
        actor: Any,
        target: Any,
        effect: Effect | None,
        variables: list[VarInfo] = [],
    ) -> bool:
        """
        Apply an effect to a target character.

        Args:
            actor:
                The character applying the effect
            target:
                The character receiving the effect
            effect:
                The effect to apply
            variables:
                List of variable info for effect scaling (not used in this base
                method)

        Returns:
            bool:
                True if effect was successfully applied, False otherwise

        """
        from character.main import Character

        if not isinstance(actor, Character):
            raise ValueError("Actor must be a Character instance")
        if not isinstance(target, Character):
            raise ValueError("Target must be a Character instance")
        if not all(isinstance(var, VarInfo) for var in variables):
            raise ValueError("All items in variables must be VarInfo instances")

        # Ensure both actor and target are alive.
        if not actor.is_alive() or not target.is_alive():
            return False
        # If the effect is None, nothing to apply.
        if effect is None:
            return False

        # Make sure effect is an Effect instance.
        if not isinstance(effect, Effect):
            raise ValueError("Effect must be an Effect instance or None")

        # Check if the effect can be applied.
        if not effect.can_apply(actor, target):
            return False

        # Apply the effect to the target.
        if target.add_effect(actor, effect, variables):
            return True

        return False

    # ============================================================================
    # COMBAT SYSTEM METHODS
    # ============================================================================

    def _roll_attack(
        self,
        actor,
        to_hit_expression: str,
        bonus_list: list[str] | None,
    ) -> RollBreakdown:
        """
        Roll a d20 attack with bonuses and return detailed breakdown.

        Args:
            actor:
                The character making the attack.
            to_hit_expression:
                The attack bonus expression (e.g., "STR + PROF").
            bonus_list:
                Additional bonus expressions to add to the roll.

        Returns:
            RollBreakdown:
                Detailed breakdown of the roll result

        """
        from character.main import Character

        if not isinstance(actor, Character):
            raise GameException("Actor must be a Character instance", actor)

        # Build attack expression.
        expr = "1D20"
        if to_hit_expression:
            expr += f"+{to_hit_expression}"

        # Process bonus list.
        for bonus in bonus_list or []:
            # Only add non-empty bonuses.
            if bonus:
                expr += f"+{bonus}"

        # Get actor variables and ensure it's a dict.
        return roll_and_describe(expr, actor.get_expression_variables())

    def _resolve_attack_roll(
        self,
        actor: Any,
        target: Any,
        attack_bonus: str = "",
        bonus_list: list[str] | None = None,
        target_ac_attr: str = "AC",
        auto_hit_on_crit: bool = True,
        auto_miss_on_fumble: bool = True,
    ) -> dict:
        """
        Perform an attack roll, returning a structured result with crit/fumble/hit info.

        Args:
            actor (Any): The character making the attack.
            target (Any): The character being attacked.
            attack_bonus (str): Attack bonus expression (e.g., "STR + PROF").
            bonus_list (list[str]): Additional bonus expressions.
            target_ac_attr (str): Attribute name for target's AC (default: "AC").
            auto_hit_on_crit (bool): If True, crit always hits.
            auto_miss_on_fumble (bool): If True, fumble always misses.

        Returns:
            dict: {
                'hit': bool,
                'is_critical': bool,
                'is_fumble': bool,
                'attack_total': int,
                'attack_roll_desc': str,
                'msg': str,
                'd20_roll': int,
            }

        """
        if bonus_list is None:
            bonus_list = []
        attack = self._roll_attack(
            actor,
            attack_bonus,
            bonus_list,
        )
        assert attack.rolls, "Rolls should not be empty"
        d20_roll = attack.rolls[0]
        is_critical = d20_roll == 20
        is_fumble = d20_roll == 1
        target_ac = getattr(target, target_ac_attr, 0)
        # Determine hit logic
        if is_fumble and auto_miss_on_fumble:
            hit = False
        elif is_critical and auto_hit_on_crit:
            hit = True
        else:
            hit = attack.value >= target_ac
        msg = f"rolled ({attack.description}) {attack.value} vs AC {target_ac}"
        return {
            "hit": hit,
            "is_critical": is_critical,
            "is_fumble": is_fumble,
            "attack_total": attack.value,
            "attack_roll_desc": attack.description,
            "msg": msg,
            "d20_roll": d20_roll,
        }

    # ============================================================================
    # COMMON UTILITY METHODS (SHARED BY DAMAGE-DEALING ABILITIES)
    # ============================================================================

    def _common_get_damage_expr(
        self,
        actor: Any,
        damage_components: list[DamageComponent],
        variables: list[VarInfo] = [],
    ) -> str:
        """
        Returns the damage expression with variables substituted.

        Args:
            actor:
                The character using the ability
            damage_components:
                List of damage components to build expression from
            variables:
                Additional variables to include in the expression

        Returns:
            str:
                Complete damage expression with variables replaced by values

        """
        from character.main import Character

        if not isinstance(actor, Character):
            raise ValueError("Actor must be a Character instance")
        if not all(isinstance(comp, DamageComponent) for comp in damage_components):
            raise ValueError("All damage_components must be DamageComponent instances")
        if not all(isinstance(var, VarInfo) for var in variables):
            raise ValueError("All variables must be VarInfo instances")

        if not damage_components:
            raise ValueError("damage_components list cannot be empty")

        # Build the full expression by substituting each component's damage roll.
        return " + ".join(
            substitute_variables(component.damage_roll, variables)
            for component in damage_components
        )

    def _common_get_min_damage(
        self,
        actor: Any,
        damage_components: list[DamageComponent],
        variables: list[VarInfo] = [],
    ) -> int:
        """
        Returns the minimum possible damage value for the ability.

        Args:
            actor:
                The character using the ability
            damage_components:
                List of damage components to calculate from
            variables:
                Additional variables to include in the calculation

        Returns:
            int:
                Minimum total damage across all damage components

        """
        from character.main import Character

        if not isinstance(actor, Character):
            raise ValueError("Actor must be a Character instance")
        if not all(isinstance(comp, DamageComponent) for comp in damage_components):
            raise ValueError("All damage_components must be DamageComponent instances")
        if not all(isinstance(var, VarInfo) for var in variables):
            raise ValueError("All variables must be VarInfo instances")

        if not damage_components:
            raise ValueError("damage_components list cannot be empty")

        # Calculate the minimum damage by assuming all dice roll their minimum values.
        return sum(
            parse_expr_and_assume_min_roll(
                substitute_variables(component.damage_roll, variables)
            )
            for component in damage_components
        )

    def _common_get_max_damage(
        self,
        actor: Any,
        damage_components: list[DamageComponent],
        variables: list[VarInfo] = [],
    ) -> int:
        """
        Returns the maximum possible damage value for the ability.

        Args:
            actor:
                The character using the ability
            damage_components:
                List of damage components to calculate from
            variables:
                Additional variables to include in the calculation

        Returns:
            int:
                Maximum total damage across all damage components

        """
        from character.main import Character

        if not isinstance(actor, Character):
            raise ValueError("Actor must be a Character instance")
        if not all(isinstance(comp, DamageComponent) for comp in damage_components):
            raise ValueError("All damage_components must be DamageComponent instances")
        if not all(isinstance(var, VarInfo) for var in variables):
            raise ValueError("All variables must be VarInfo instances")

        if not damage_components:
            raise ValueError("damage_components list cannot be empty")

        # Calculate the maximum damage by assuming all dice roll their maximum values.
        return sum(
            parse_expr_and_assume_max_roll(
                substitute_variables(component.damage_roll, variables)
            )
            for component in damage_components
        )

    # ============================================================================
    # TARGETING SYSTEM METHODS
    # ============================================================================

    def is_valid_target(self, actor: Any, target: Any) -> bool:
        """Check if the target is valid for this action.

        Args:
            actor (Any): The character performing the action.
            target (Any): The potential target character.

        Returns:
            bool: True if the target is valid for this action, False otherwise.

        """
        from core.constants import ActionCategory
        from character.main import Character

        if not isinstance(actor, Character):
            raise ValueError("Actor must be a Character instance")
        if not isinstance(target, Character):
            raise ValueError("Target must be a Character instance")

        # Both must be alive to target.
        if not actor.is_alive() or not target.is_alive():
            return False

        def _is_relationship_valid(actor: Any, target: Any, is_ally: bool) -> bool:
            """Helper to check if actor and target have the correct relationship."""
            are_opponents = is_oponent(actor.char_type, target.char_type)
            if is_ally:
                return not are_opponents
            return are_opponents

        # Check each restriction - return True on first match (OR logic).
        for restriction in self.target_restrictions:
            if restriction == "SELF" and actor == target:
                return True
            if restriction == "ALLY" and _is_relationship_valid(actor, target, True):
                return True
            if restriction == "ENEMY" and _is_relationship_valid(actor, target, False):
                return True
            if restriction == "ANY":
                return True

        # Otherwise, fall back to category-based default targeting.

        # Offensive actions target enemies (not self, must be opponents).
        if self.category == ActionCategory.OFFENSIVE:
            # Offensive actions target enemies (not self, must be opponents)
            return target != actor and is_oponent(actor.char_type, target.char_type)

        # Healing actions target self and allies (not enemies, not at full health for healing)
        if self.category == ActionCategory.HEALING:
            if target == actor:
                return target.hp < target.HP_MAX
            if not is_oponent(actor.char_type, target.char_type):
                return target.hp < target.HP_MAX
            return False

        # Buff actions target self and allies.
        if self.category == ActionCategory.BUFF:
            return target == actor or not is_oponent(actor.char_type, target.char_type)

        # Debuff actions target enemies.
        if self.category == ActionCategory.DEBUFF:
            return target != actor and is_oponent(actor.char_type, target.char_type)

        # Utility actions can target anyone.
        if self.category == ActionCategory.UTILITY:
            return True

        # Debug actions can target anyone.
        if self.category == ActionCategory.DEBUG:
            return True

        # Unknown category - default to no targeting.
        return False
