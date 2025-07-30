from logging import debug
from typing import Any, Tuple

from combat.damage import (
    DamageComponent,
    roll_and_describe,
    roll_damage_components_no_mind,
)
from core.utils import (
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    substitute_variables,
)
from core.constants import (
    ActionType,
    ActionCategory,
    apply_character_type_color,
    is_oponent,
)
from catchery import (
    ErrorSeverity,
    log_warning,
    safe_operation,
    validate_object,
    validate_type,
    ensure_string,
    ensure_int_in_range,
    ensure_non_negative_int,
    ensure_list_of_type,
    safe_get_attribute,
)
from effects import Effect


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
        ctx = {
            "name": name,
            "action_type": action_type,
            "category": category,
            "description": description,
            "cooldown": cooldown,
            "maximum_uses": maximum_uses,
            "target_restrictions": target_restrictions or [],
        }

        # === CRITICAL VALIDATIONS ===
        self.name = validate_type(name, "Action name", str, ctx)
        self.action_type = validate_type(action_type, "Action type", ActionType, ctx)
        self.category = validate_type(category, "Action category", ActionCategory, ctx)

        # === NON-CRITICAL VALIDATIONS ===

        self.description = ensure_string(description, "Action description", "", ctx)
        self._cooldown = ensure_int_in_range(
            cooldown,
            "Action cooldown",
            -1,
            None,
            -1,
            ctx,
        )
        self._maximum_uses = ensure_int_in_range(
            maximum_uses,
            "Action maximum_uses",
            -1,
            None,
            -1,
            ctx,
        )
        self.target_restrictions = ensure_list_of_type(
            target_restrictions,
            "Action target restrictions",
            str,
            [],
            lambda x: str(x).strip(),
            None,
            ctx,
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
        """Check if the action has limited uses.

        Returns:
            bool: True if maximum uses is greater than 0, False if unlimited.
        """
        return self._maximum_uses > 0

    def get_maximum_uses(self) -> int:
        """Get the maximum number of uses for this action.

        Returns:
            int: Maximum uses per encounter/day (-1 for unlimited).
        """
        return self._maximum_uses

    def has_cooldown(self) -> bool:
        """Check if the action has a cooldown period.

        Returns:
            bool: True if cooldown is greater than 0, False otherwise.
        """
        return self._cooldown > 0

    def get_cooldown(self) -> int:
        """Get the cooldown period for this action.

        Returns:
            int: Cooldown period in turns (-1 for no cooldown).
        """
        return self._cooldown

    @safe_operation(
        default_value=False,
        error_message="Character validation failed",
        severity=ErrorSeverity.HIGH,
    )
    def _validate_character(
        self, character: Any, context: dict[str, Any] | None = None
    ) -> bool:
        """Validate that a character object has the required attributes.

        Args:
            character (Any): The character object to validate.
            context (dict[str, Any]): Context for error messages.

        Returns:
            bool: True if valid, False otherwise.
        """
        validate_object(
            character,
            "character",
            context or {"action": self.name},
            [
                "name",
                "char_type",
                "mind",
                "MIND_MAX",
                "hp",
                "HP_MAX",
                "is_on_cooldown",
                "get_expression_variables",
                "effects_module",
            ],
        )
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
        mind_level: int = 0,
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
        if not self._validate_character(actor):
            return False
        if not self._validate_character(target):
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
        if not self._validate_character(actor):
            return 1, "1D20: 1 (error)", 1
        # Build attack expression
        expr = "1D20"
        attack_bonus_expr = ensure_string(attack_bonus_expr, "attack bonus expression")
        if attack_bonus_expr:
            expr += f" + {attack_bonus_expr}"

        # Process bonus list
        bonus_list = ensure_list_of_type(bonus_list, "bonus list", str, [])
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

    def _resolve_attack_roll(
        self,
        actor: Any,
        target: Any,
        attack_bonus_expr: str = "",
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
            attack_bonus_expr (str): Attack bonus expression (e.g., "STR + PROF").
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
        attack_total, attack_roll_desc, d20_roll = self._roll_attack_with_crit(
            actor, attack_bonus_expr, bonus_list
        )
        is_critical = d20_roll == 20
        is_fumble = d20_roll == 1
        target_ac = getattr(target, target_ac_attr, 0)
        # Determine hit logic
        if is_fumble and auto_miss_on_fumble:
            hit = False
        elif is_critical and auto_hit_on_crit:
            hit = True
        else:
            hit = attack_total >= target_ac
        msg = f"rolled ({attack_roll_desc}) {attack_total} vs AC {target_ac}"
        return {
            "hit": hit,
            "is_critical": is_critical,
            "is_fumble": is_fumble,
            "attack_total": attack_total,
            "attack_roll_desc": attack_roll_desc,
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
        if not self._validate_character(actor):
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
        if not self._validate_character(actor):
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
        if not self._validate_character(actor):
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
        if not self._validate_character(actor):
            return False
        if not self._validate_character(target):
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


class ActionSerializer:
    """Utility class for serializing and deserializing action instances."""

    @staticmethod
    def serialize(ability: BaseAction) -> dict[str, Any]:
        """Serialize common fields shared by all abilities."""
        data = {
            "class": ability.__class__.__name__,
            "name": ability.name,
            "type": ability.action_type.name,
            "description": ability.description,
            "": ability.target_restrictions or [],
        }
        if ability.has_cooldown():
            data["cooldown"] = ability.get_cooldown()
        if ability.has_limited_uses():
            data["maximum_uses"] = ability.get_maximum_uses()
        if ability.target_restrictions:
            data["target_restrictions"] = ability.target_restrictions
        return data
