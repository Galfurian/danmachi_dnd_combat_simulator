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
from effects.effect import *


class BaseAction:
    """
    Base class for all character actions in the combat system.

    This class provides the foundation for all actions that characters can perform,
    including attacks, spells, abilities, and utility actions. It handles common
    functionality like validation, targeting, and effect application.

    Attributes:
        name (str): The display name of the action
        type (ActionType): The type of action (ATTACK, SPELL, ABILITY, etc.)
        category (ActionCategory): The category for targeting logic (OFFENSIVE, HEALING, BUFF, etc.)
        description (str): Human-readable description of the action
        cooldown (int): Number of turns before action can be used again (0 = no cooldown)
        maximum_uses (int): Max times action can be used (-1 = unlimited)
        target_restrictions (list[str]): List of targeting restrictions ("SELF", "ALLY", "ENEMY", "ANY")

    Note:
        - This is an abstract base class. Subclasses must implement the execute() method.
        - Targeting logic is automatically handled based on category unless target_restrictions are specified.
        - All inputs are validated during initialization with helpful error messages.
    """

    def __init__(
        self,
        name: str,
        type: ActionType,
        category: ActionCategory,
        description: str = "",
        cooldown: int = 0,
        maximum_uses: int = -1,
        target_restrictions: list[str] | None = None,
    ):
        """Initialize a new BaseAction."""
        # === CRITICAL VALIDATIONS ===
        # These will raise ValueError if invalid - action cannot be created
        self.name = require_non_empty_string(name, "action name", {"type": str(type)})
        self.type = require_enum_type(type, ActionType, "action type", {"name": name})
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
            actor (Any): The character performing the action (must have is_alive method)
            target (Any): The character being targeted (must have is_alive method and effects_module)

        Raises:
            NotImplementedError: This method must be implemented by subclasses.

        Returns:
            bool: True if action executed successfully, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement the execute method")

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
        """
        Apply an effect to a target character.

        Args:
            actor: The character applying the effect (must have is_alive method)
            target: The character receiving the effect (must have is_alive and effects_module)
            effect: The effect to apply, or None to do nothing
            mind_level: The mind cost level for scaling effects (0+ integer)
            spell: The spell or action reference for concentration handling

        Returns:
            bool: True if effect was successfully applied, False otherwise
        """
        try:
            if not effect:
                return False

            # Validate required objects using helpers
            validate_required_object(
                actor,
                "actor",
                ["is_alive"],
                {"effect": safe_get_attribute(effect, "name", "Unknown")},
            )
            validate_required_object(
                target,
                "target",
                ["is_alive", "effects_module"],
                {
                    "effect": safe_get_attribute(effect, "name", "Unknown"),
                    "actor": safe_get_attribute(actor, "name", "Unknown"),
                },
            )

            # Check if actors are alive
            if not actor.is_alive() or not target.is_alive():
                return False

            # Validate and correct mind_level using helper
            mind_level = ensure_non_negative_int(
                mind_level,
                "mind level",
                0,
                {
                    "effect": safe_get_attribute(effect, "name", "Unknown"),
                    "actor": safe_get_attribute(actor, "name", "Unknown"),
                    "target": safe_get_attribute(target, "name", "Unknown"),
                },
            )

            if target.effects_module.add_effect(actor, effect, mind_level, self):
                debug(
                    f"Applied effect {effect.name} from {actor.name} to {target.name}."
                )
                return True
            debug(
                f"Not applied effect {effect.name} from {actor.name} to {target.name}."
            )
            return False

        except Exception as e:
            log_error(
                f"Error applying effect {safe_get_attribute(effect, 'name', 'Unknown')}: {str(e)}",
                {
                    "effect": safe_get_attribute(effect, "name", "Unknown"),
                    "error": str(e),
                    "actor": safe_get_attribute(actor, "name", "Unknown"),
                    "target": safe_get_attribute(target, "name", "Unknown"),
                },
                e,
            )
            return False

    # ============================================================================
    # COMBAT SYSTEM METHODS
    # ============================================================================

    def roll_attack_with_crit(
        self, actor, attack_bonus_expr: str, bonus_list: list[str]
    ) -> Tuple[int, str, int]:
        """
        Roll an attack with critical hit detection.

        This method handles the complete attack roll process, including building
        the dice expression, applying bonuses, and detecting critical hits.
        It's primarily used by attack actions and spell attack actions.

        Args:
            actor: The character making the attack (must have get_expression_variables method)
            attack_bonus_expr: Base attack bonus expression (e.g., "STR + PROF")
            bonus_list: Additional bonus expressions to add to the roll

        Returns:
            Tuple[int, str, int]: (total_result, description, raw_d20_roll)
            - total_result: Final attack roll total
            - description: Human-readable description of the roll
            - raw_d20_roll: The natural d20 result (for crit detection)
        """
        try:
            # Validate required actor object
            validate_required_object(actor, "actor", ["get_expression_variables"])

            # Build attack expression
            expr = "1D20"
            attack_bonus_expr = ensure_string(
                attack_bonus_expr, "attack bonus expression", ""
            )
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

        except Exception as e:
            log_error(
                f"Error rolling attack: {str(e)}",
                {
                    "error": str(e),
                    "actor": safe_get_attribute(actor, "name", "Unknown"),
                    "attack_bonus_expr": attack_bonus_expr,
                    "bonus_list": bonus_list,
                },
                e,
            )
            return 1, "1D20: 1 (error)", 1  # Return safe fallback

    # ============================================================================
    # COMMON UTILITY METHODS (SHARED BY DAMAGE-DEALING ABILITIES)
    # ============================================================================

    def _common_get_damage_expr(
        self,
        actor: Any,
        damage_components: list[DamageComponent],
        extra_variables: dict[str, int] = {},
    ) -> str:
        """
        Returns the damage expression with variables substituted.

        Args:
            actor: The character using the ability (must have expression variables)
            damage_components: List of damage components to build expression from
            extra_variables: Additional variables to include in the expression

        Returns:
            str: Complete damage expression with variables replaced by values
        """
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
        """
        Returns the minimum possible damage value for the ability.

        Args:
            actor: The character using the ability
            damage_components: List of damage components to calculate from
            extra_variables: Additional variables to include in the calculation

        Returns:
            int: Minimum total damage across all damage components
        """
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
        """
        Returns the maximum possible damage value for the ability.

        Args:
            actor: The character using the ability
            damage_components: List of damage components to calculate from
            extra_variables: Additional variables to include in the calculation

        Returns:
            int: Maximum total damage across all damage components
        """
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
        """
        Check if the target is valid for this action.

        This method determines whether an action can target a specific character
        based on the action's category and any custom target restrictions.
        It handles both automatic targeting rules and explicit restrictions.

        Args:
            actor: The character performing the action (must have is_alive method)
            target: The potential target character (must have is_alive method)

        Returns:
            bool: True if the target is valid for this action, False otherwise
        """
        try:
            # Validate required objects have is_alive method
            validate_required_object(
                actor, "actor", ["is_alive"], {"action": self.name}
            )
            validate_required_object(
                target,
                "target",
                ["is_alive"],
                {
                    "action": self.name,
                    "actor": safe_get_attribute(actor, "name", "Unknown"),
                },
            )

            # If target_restrictions are defined, use the generic targeting system
            if self.target_restrictions:
                return self._check_target_restrictions(actor, target)

            # Otherwise, fall back to category-based default targeting
            return self._is_valid_target_default(actor, target)

        except ValueError:
            # If validation fails, target is invalid
            return False

    def _check_target_restrictions(self, actor: Any, target: Any) -> bool:
        """
        Check if target is valid based on explicit target_restrictions.

        This method processes explicit targeting rules when target_restrictions
        are defined, rather than using category-based defaults.

        Args:
            actor: The character performing the action
            target: The potential target character

        Returns:
            bool: True if target matches any of the restrictions, False otherwise
        """
        # Basic validation - both must be alive
        if not actor.is_alive() or not target.is_alive():
            return False

        # Check each restriction - return True on first match (OR logic)
        for restriction in self.target_restrictions:
            if restriction == "SELF" and actor == target:
                return True
            if restriction == "ALLY" and self._is_relationship_valid(
                actor, target, is_ally=True
            ):
                return True
            if restriction == "ENEMY" and self._is_relationship_valid(
                actor, target, is_ally=False
            ):
                return True
            if restriction == "ANY":
                return True

        # No restrictions matched - target is invalid
        return False

    def _is_valid_target_default(self, actor: Any, target: Any) -> bool:
        """Provide sensible default targeting based on action category.

        Args:
            actor (Any): The character performing the action.
            target (Any): The potential target character.

        Returns:
            bool: True if the target is valid for the action, False otherwise.
        """
        try:
            # Basic validation - both must be alive
            if not actor.is_alive() or not target.is_alive():
                return False

            from core.constants import ActionCategory

            if self.category == ActionCategory.OFFENSIVE:
                # Offensive actions target enemies (not self, must be opponents)
                return target != actor and is_oponent(
                    safe_get_attribute(actor, "type", "UNKNOWN"),
                    safe_get_attribute(target, "type", "UNKNOWN"),
                )

            if self.category == ActionCategory.HEALING:
                # Healing actions target self and allies (not enemies, not at full health for healing)
                if target == actor:
                    return safe_get_attribute(target, "hp", 0) < safe_get_attribute(
                        target, "HP_MAX", 1
                    )  # Can heal self if not at full health
                if not is_oponent(
                    safe_get_attribute(actor, "type", "UNKNOWN"),
                    safe_get_attribute(target, "type", "UNKNOWN"),
                ):
                    return safe_get_attribute(target, "hp", 0) < safe_get_attribute(
                        target, "HP_MAX", 1
                    )  # Can heal allies if not at full health
                return False

            if self.category == ActionCategory.BUFF:
                # Buff actions target self and allies
                return target == actor or not is_oponent(
                    safe_get_attribute(actor, "type", "UNKNOWN"),
                    safe_get_attribute(target, "type", "UNKNOWN"),
                )

            if self.category == ActionCategory.DEBUFF:
                # Debuff actions target enemies
                return target != actor and is_oponent(
                    safe_get_attribute(actor, "type", "UNKNOWN"),
                    safe_get_attribute(target, "type", "UNKNOWN"),
                )

            if self.category == ActionCategory.UTILITY:
                # Utility actions can target anyone
                return True

            if self.category == ActionCategory.DEBUG:
                # Debug actions can target anyone
                return True

            # Unknown category - default to no targeting
            return False

        except Exception as e:
            log_warning(
                f"Error in default targeting for action {self.name}: {str(e)}",
                {
                    "action": self.name,
                    "category": (
                        self.category.name
                        if hasattr(self.category, "name")
                        else str(self.category)
                    ),
                    "actor": safe_get_attribute(actor, "name", "Unknown"),
                    "target": safe_get_attribute(target, "name", "Unknown"),
                    "error": str(e),
                },
                e,
            )
            return False

    def _is_relationship_valid(self, actor: Any, target: Any, is_ally: bool) -> bool:
        """
        Helper to check if actor and target have the correct relationship.

        This method determines whether two characters are allies or enemies
        based on their character types. It's used by the targeting system
        to validate relationship-based restrictions.

        Args:
            actor: The character performing the action
            target: The potential target character
            is_ally: True to check for ally relationship, False for enemy

        Returns:
            bool: True if the relationship matches the requested type
        """
        try:
            if actor == target:  # Self is neither ally nor enemy in this context
                return False

            # Check if they are opponents (enemies to each other)
            actor_type = safe_get_attribute(actor, "type", "UNKNOWN")
            target_type = safe_get_attribute(target, "type", "UNKNOWN")
            are_opponents = is_oponent(actor_type, target_type)

            if is_ally:
                return not are_opponents  # Allies are not opponents
            else:
                return are_opponents  # Enemies are opponents

        except Exception as e:
            log_warning(
                f"Error checking relationship for action {self.name}: {str(e)}",
                {
                    "action": self.name,
                    "actor": safe_get_attribute(actor, "name", "Unknown"),
                    "target": safe_get_attribute(target, "name", "Unknown"),
                    "is_ally": is_ally,
                    "error": str(e),
                },
                e,
            )
            return False

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the action to a dictionary representation for serialization.

        This method creates a JSON-serializable dictionary containing all the
        action's data. It's used for saving actions to files, network transmission,
        or debugging purposes.

        Returns:
            dict[str, Any]: Dictionary containing all action data
        """
        data = {
            "class": self.__class__.__name__,
            "name": self.name,
            "type": self.type.name,
            "category": self.category.name,
            "description": self.description,
            "cooldown": self.cooldown,
            "maximum_uses": self.maximum_uses,
        }
        if self.target_restrictions:
            data["target_restrictions"] = self.target_restrictions
        return data
