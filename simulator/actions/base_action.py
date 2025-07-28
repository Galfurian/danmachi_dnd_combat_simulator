from logging import debug
from typing import Any

from combat.damage import *
from core.utils import *
from core.constants import *
from core.error_handling import (
    log_error,
    log_warning,
    require_non_empty_string,
    require_enum_type,
    ensure_string,
    ensure_non_negative_int,
    ensure_int_in_range,
    ensure_list_of_strings,
    validate_required_object,
    safe_get_attribute,
)
from effects import *


class BaseAction:
    """Base class for all character actions in the combat system.

    This class provides a foundation for implementing various types of actions,
    such as attacks, spells, and utility abilities. It includes methods for
    validation, targeting, and effect application, as well as utility methods
    for damage calculation and serialization.
    """

    def __init__(
        self,
        name: str,
        action_type: ActionType,
        category: ActionCategory,
        description: str = "",
        cooldown: int = 0,
        maximum_uses: int = -1,
        target_restrictions: list[str] | None = None,
    ):
        """Initialize a new BaseAction.

        Args:
            name (str): Name of the action.
            type (ActionType): Type of the action (e.g., ACTION, BONUS_ACTION).
            category (ActionCategory): Category of the action (e.g., OFFENSIVE, HEALING).
            description (str): Description of the action.
            cooldown (int): Cooldown period in turns.
            maximum_uses (int): Maximum number of uses per encounter/day.
            target_restrictions (list[str] | None): Restrictions on valid targets.

        Raises:
            ValueError: If critical validations fail.
        """
        # === CRITICAL VALIDATIONS ===
        # These will raise ValueError if invalid - action cannot be created
        self.name = require_non_empty_string(name, "action name", {"name": name})
        self.action_type = require_enum_type(
            action_type, ActionType, "action type", {"name": name}
        )
        self.category = require_enum_type(
            category, ActionCategory, "action category", {"name": name}
        )

        # === NON-CRITICAL VALIDATIONS ===
        # These will log warnings and auto-correct - action can still be created
        self.description = ensure_string(
            description, "action description", "", {"name": name}
        )
        self.cooldown = ensure_non_negative_int(
            cooldown, "action cooldown", 0, {"name": name}
        )
        self.maximum_uses = ensure_int_in_range(
            maximum_uses, "action maximum_uses", -1, None, -1, {"name": name}
        )
        self.target_restrictions = ensure_list_of_strings(
            target_restrictions, "target restrictions", [], {"name": name}
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

    def _validate_actor_and_target(self, actor: Any, target: Any) -> bool:
        """Validate that actor and target are valid characters with required methods.

        Args:
            actor: The character using the ability
            target: The target character

        Returns:
            bool: True if both actor and target are valid, False otherwise
        """
        try:
            if actor:
                validate_required_object(
                    actor,
                    "actor",
                    [
                        "name",
                        "char_type",
                        "mind",
                        "MIND_MAX",
                        "hp",
                        "HP_MAX",
                        "is_on_cooldown",
                        "get_expression_variables",
                    ],
                    {"action": self.name},
                )
            if target:
                validate_required_object(
                    target,
                    "target",
                    [
                        "name",
                        "char_type",
                        "mind",
                        "MIND_MAX",
                        "hp",
                        "HP_MAX",
                        "is_on_cooldown",
                        "get_expression_variables",
                    ],
                    {"action": self.name},
                )
        except Exception as e:
            log_error(
                f"Error executing {self.name}: {str(e)}",
                {
                    "action": self.name,
                    "error": str(e),
                    "actor": getattr(actor, "name", "Unknown"),
                    "target": getattr(target, "name", "Unknown"),
                },
                e,
            )
            return False
        return True

    def _get_display_strings(self, actor: Any, target: Any) -> tuple[str, str]:
        """Get formatted display strings for actor and target.

        Args:
            actor: The character using the ability
            target: The target character

        Returns:
            tuple[str, str]: (actor_display, target_display)
        """
        actor_str = apply_character_type_color(actor.char_type, actor.name)
        target_str = apply_character_type_color(target.char_type, target.name)
        return actor_str, target_str

    # ============================================================================
    # EFFECT SYSTEM METHODS
    # ============================================================================

    def _common_apply_effect(
        self,
        actor: Any,
        target: Any,
        effect: Effect | None,
        mind_level: int | None = None,
    ) -> bool:
        """Apply an effect to a target character.

        Args:
            actor: The character applying the effect
            target: The character receiving the effect
            effect: The effect to apply, or None to do nothing
            mind_level: The mind cost level for scaling effects

        Returns:
            bool: True if effect was successfully applied, False otherwise
        """
        # Validate actor and target.
        if not self._validate_actor_and_target(actor, target):
            return False
        # Validate effect is provided and is an instance of Effect.
        if not effect or not isinstance(effect, Effect):
            return False
        # Ensure both actor and target are alive.
        if not actor.is_alive() or not target.is_alive():
            return False
        # Validate and correct mind_level.
        mind_level = ensure_non_negative_int(mind_level, "mind level", 0)
        # Try to apply the effect using the target's effects module.
        if target.effects_module.add_effect(actor, effect, mind_level, self):
            return True
        return False

    # ============================================================================
    # COMBAT SYSTEM METHODS
    # ============================================================================

    def _roll_bonus_damage(self, actor: Any, target: Any) -> tuple[int, list[str]]:
        """Roll any bonus damage from effects.

        Args:
            actor: The character using the ability
            target: The target character

        Returns:
            tuple[int, list[str]]: (bonus_damage, damage_descriptions)
        """
        all_damage_modifiers = actor.effects_module.get_damage_modifiers()
        return roll_damage_components_no_mind(actor, target, all_damage_modifiers)

    def _roll_attack_with_crit(
        self, actor, attack_bonus_expr: str, bonus_list: list[str]
    ) -> Tuple[int, str, int]:
        """Roll an attack with critical hit detection.

        Args:
            actor: The character making the attack
            attack_bonus_expr: Base attack bonus expression
            bonus_list: Additional bonus expressions to add to the roll

        Returns:
            Tuple[int, str, int]: (total_result, description, raw_d20_roll)
        """
        if not self._validate_actor_and_target(actor, None):
            return 1, "1D20: 1 (error)", 1
        # Build attack expression
        expr = "1D20"
        attack_bonus_expr = ensure_string(attack_bonus_expr, "attack bonus expression")
        if attack_bonus_expr:
            expr += f" + {attack_bonus_expr}"

        # Process bonus list
        bonus_list = ensure_list_of_strings(bonus_list, "bonus list", [])
        for bonus in bonus_list:
            if bonus:  # Only add non-empty bonuses
                expr += f" + {bonus}"

        # Get actor variables and ensure it's a dict
        variables = actor.get_expression_variables()
        if not isinstance(variables, dict):
            log_warning(
                f"Actor expression variables must be dict, got: {type(variables).__name__}, using empty dict",
                {
                    "variables": variables,
                    "actor": safe_get_attribute(actor, "name", "Unknown"),
                },
            )
            variables = {}

        total, desc, rolls = roll_and_describe(expr, variables)
        return total, desc, rolls[0] if rolls else 0

    # ============================================================================
    # COMMON UTILITY METHODS (SHARED BY DAMAGE-DEALING ABILITIES)
    # ============================================================================

    def _common_get_damage_expr(
        self,
        actor: Any,
        damage_components: list[DamageComponent],
        extra_variables: dict[str, int] = {},
    ) -> str:
        """Returns the damage expression with variables substituted.

        Args:
            actor: The character using the ability
            damage_components: List of damage components to build expression from
            extra_variables: Additional variables to include in the expression

        Returns:
            str: Complete damage expression with variables replaced by values
        """
        # Validate actor.
        if not self._validate_actor_and_target(actor, None):
            return "0"
        # Validate inputs.
        if not isinstance(damage_components, list) or not damage_components:
            log_warning(
                "Damage components must be a non-empty list",
                {"damage_components": damage_components, "actor": actor.name},
            )
            return "0"
        if not isinstance(extra_variables, dict):
            log_warning(
                "Extra variables must be a dictionary",
                {"extra_variables": extra_variables, "actor": actor.name},
            )
            extra_variables = {}
        # Get the base character variables.
        variables = actor.get_expression_variables()
        # Add the extra variables for this action.
        variables.update(extra_variables)
        # Build the full expression by substituting each component's damage roll.
        return " + ".join(
            substitute_variables(component.damage_roll, variables)
            for component in damage_components
        )

    def _common_get_min_damage(
        self,
        actor: Any,
        damage_components: list[DamageComponent],
        extra_variables: dict[str, int] = {},
    ) -> int:
        """Returns the minimum possible damage value for the ability.

        Args:
            actor: The character using the ability
            damage_components: List of damage components to calculate from
            extra_variables: Additional variables to include in the calculation

        Returns:
            int: Minimum total damage across all damage components
        """
        # Validate actor.
        if not self._validate_actor_and_target(actor, None):
            return 0
        # Validate inputs.
        if not isinstance(damage_components, list) or not damage_components:
            log_warning(
                "Damage components must be a non-empty list",
                {"damage_components": damage_components, "actor": actor.name},
            )
            return 0
        if not isinstance(extra_variables, dict):
            log_warning(
                "Extra variables must be a dictionary",
                {"extra_variables": extra_variables, "actor": actor.name},
            )
            extra_variables = {}
        # Get the base character variables.
        variables = actor.get_expression_variables()
        # Add the extra variables for this action.
        variables.update(extra_variables)
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
        extra_variables: dict[str, int] = {},
    ) -> int:
        """Returns the maximum possible damage value for the ability.

        Args:
            actor: The character using the ability
            damage_components: List of damage components to calculate from
            extra_variables: Additional variables to include in the calculation

        Returns:
            int: Maximum total damage across all damage components
        """
        # Validate actor.
        if not self._validate_actor_and_target(actor, None):
            return 0
        # Validate inputs.
        if not isinstance(damage_components, list) or not damage_components:
            log_warning(
                "Damage components must be a non-empty list",
                {"damage_components": damage_components, "actor": actor.name},
            )
            return 0
        if not isinstance(extra_variables, dict):
            log_warning(
                "Extra variables must be a dictionary",
                {"extra_variables": extra_variables, "actor": actor.name},
            )
            extra_variables = {}
        # Get the base character variables.
        variables = actor.get_expression_variables()
        # Add the extra variables for this action.
        variables.update(extra_variables)
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

        # Validate actor and target.
        if not self._validate_actor_and_target(actor, target):
            return False

        # Both must be alive to target.
        if not actor.is_alive() or not target.is_alive():
            return False

        def _is_relationship_valid(actor: Any, target: Any, is_ally: bool) -> bool:
            """Helper to check if actor and target have the correct relationship."""
            are_opponents = is_oponent(actor.char_type, target.char_type)
            if is_ally:
                return not are_opponents
            else:
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

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def to_dict(self) -> dict[str, Any]:
        """Convert the action to a dictionary representation for serialization.

        Returns:
            dict[str, Any]: Dictionary containing all action data.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError("Subclasses must implement the to_dict")

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Any":
        """Create an action instance from a dictionary representation.

        Args:
            data (dict[str, Any]): Dictionary containing action data.

        Returns:
            Any: An instance of the action class represented by the data.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError("Subclasses must implement the from_dict method")
