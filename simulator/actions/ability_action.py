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
    is_oponent,
)
from core.error_handling import (
    log_error,
    log_warning,
    log_critical,
    ensure_string,
    ensure_list_of_type,
    safe_get_attribute,
    validate_required_object,
)
from core.utils import (
    debug,
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    substitute_variables,
    cprint,
)
from effects.effect import Effect


class BaseAbility(BaseAction):
    """
    Base class for creature abilities and special attacks.

    BaseAbility represents special powers, racial abilities, monster attacks, and
    other unique actions that don't fall into standard weapon attacks or spells.
    These abilities typically have limited uses per encounter or cooldown periods
    rather than consuming spell slots or mind points.

    Key Characteristics:
        - No resource costs (no mind points or spell slots)
        - Often have uses per day/encounter or cooldown restrictions
        - Can affect single or multiple targets based on target_expr
        - May deal damage and/or apply special effects
        - Represent inherent powers rather than learned techniques

    Target System:
        - Single target: Empty or blank target_expr (default)
        - Multi-target: target_expr evaluates to number of targets
        - Example: target_expr="LEVEL//2" affects half character level targets

    Damage System:
        - Direct damage application (no attack rolls by default)
        - Multiple damage components supported
        - Integrates with effect manager for bonus damage
        - Automatic critical hit detection not included

    Usage Context:
        - Dragon breath weapons
        - Racial abilities (tiefling hellish rebuke, dragonborn breath)
        - Monster special attacks (mind flayer mind blast)
        - Environmental hazards as abilities
        - Magical item activated powers

    Example:
        ```python
        # Dragon breath ability
        fire_breath = BaseAbility(
            name="Fire Breath",
            type=ActionType.ACTION,
            description="Exhale destructive flame in a cone",
            cooldown=2,  # Recharge on 5-6
            maximum_uses=-1,
            damage=[DamageComponent("fire", "3d8")],
            effect=None,
            target_expr="3"  # Affects up to 3 targets
        )
        ```
    """

    def __init__(
        self,
        name: str,
        type: ActionType,
        description: str,
        cooldown: int,
        maximum_uses: int,
        damage: list[DamageComponent],
        effect: Effect | None = None,
        target_expr: str = "",
        target_restrictions: list[str] | None = None,
    ):
        """
        Initialize a new BaseAbility.

        Args:
            name: Display name of the ability
            type: Action type (ACTION, BONUS_ACTION, REACTION, etc.)
            description: Flavor text describing what the ability does
            cooldown: Turns to wait before reusing (0 = no cooldown)
            maximum_uses: Max uses per encounter/day (-1 = unlimited)
            damage: List of damage components to roll when used
            effect: Optional effect applied to targets on use
            target_expr: Expression determining number of targets ("" = single target)
            target_restrictions: Override default targeting if needed

        Target Expression Examples:
            - "": Single target (default)
            - "3": Always affects 3 targets
            - "LEVEL//2": Affects half character level targets (minimum 1)
            - "CON": Affects targets equal to CON modifier

        Raises:
            ValueError: If name is empty or type/category are invalid

        Note:
            - Category is automatically set to OFFENSIVE
            - Invalid damage components are filtered out with warnings
            - Invalid effects are set to None with warnings
            - Invalid target_expr is corrected to empty string
            - Uses enhanced validation helpers for robust error handling

        Example:
            ```python
            # Create a multi-target breath weapon
            breath = BaseAbility(
                name="Acid Breath",
                type=ActionType.ACTION,
                description="Spray corrosive acid in a line",
                cooldown=1,  # Recharge next turn
                maximum_uses=-1,
                damage=[
                    DamageComponent("acid", "4d6"),
                    DamageComponent("acid", "CON")  # CON modifier bonus
                ],
                effect=acid_burn_effect,
                target_expr="2 + LEVEL//3"  # Scales with level
            )
            ```
        """
        try:
            super().__init__(
                name,
                type,
                ActionCategory.OFFENSIVE,
                description,
                cooldown,
                maximum_uses,
                target_restrictions,
            )

            # Validate damage list using helper
            self.damage = ensure_list_of_type(
                damage,
                DamageComponent,
                "damage components",
                [],
                validator=lambda x: isinstance(x, DamageComponent),
                context={"name": name},
            )

            # Validate effect
            if effect is not None and not isinstance(effect, Effect):
                log_warning(
                    f"Ability {name} effect must be Effect or None, got: {effect.__class__.__name__}, setting to None",
                    {"name": name, "effect": effect},
                )
                effect = None

            # Validate target_expr using helper
            self.target_expr = ensure_string(
                target_expr, "target expression", "", {"name": name}
            )

            self.effect: Effect | None = effect

        except Exception as e:
            log_critical(
                f"Error initializing BaseAbility {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

    # ============================================================================
    # TARGETING SYSTEM METHODS
    # ============================================================================

    def is_single_target(self) -> bool:
        """
        Check if the ability targets a single entity.

        Determines targeting mode based on the target_expr property. Empty or
        whitespace-only expressions indicate single-target abilities, while
        any meaningful expression indicates multi-target abilities.

        Returns:
            bool: True if ability targets one entity, False for multi-target

        Examples:
            ```python
            # Single target examples
            single_ability.target_expr = ""        # True
            single_ability.target_expr = "   "     # True

            # Multi-target examples
            multi_ability.target_expr = "3"        # False
            multi_ability.target_expr = "LEVEL"    # False
            ```
        """
        return not self.target_expr or self.target_expr.strip() == ""

    def target_count(self, actor: Any) -> int:
        """
        Calculate the number of targets this ability can affect.

        Evaluates the target_expr with the actor's current variables to determine
        the actual number of targets. This supports dynamic scaling based on
        character level, ability scores, or other factors.

        Args:
            actor: The character using the ability (must have expression variables)

        Returns:
            int: Number of targets (minimum 1, even for invalid expressions)

        Variable Substitution:
            - {LEVEL}: Character level
            - {STR}, {DEX}, {CON}, {INT}, {WIS}, {CHA}: Ability modifiers
            - {PROF}: Proficiency bonus
            - Custom variables from actor's get_expression_variables method

        Examples:
            ```python
            # Static target count
            ability.target_expr = "3"           # Always 3 targets

            # Level-scaled targeting
            ability.target_expr = "1 + LEVEL//4"  # 1 + (level / 4)

            # Ability score based
            ability.target_expr = "max(1, CHA)"   # CHA modifier minimum 1
            ```

        Error Handling:
            Returns 1 if target_expr is empty, invalid, or evaluates to 0 or less.
        """
        if self.target_expr:
            from core.utils import evaluate_expression

            variables = actor.get_expression_variables()
            return max(1, int(evaluate_expression(self.target_expr, variables)))
        return 1

    # ============================================================================
    # COMBAT EXECUTION METHODS
    # ============================================================================

    def execute(self, actor: Any, target: Any) -> bool:
        """
        Execute this ability against a target.

        This method handles the complete ability activation sequence from validation
        through damage application. Unlike weapon attacks, abilities typically deal
        damage directly without requiring attack rolls.

        Ability Sequence:
            1. Validate actor and target objects
            2. Check cooldowns and usage restrictions
            3. Calculate base damage from ability components
            4. Apply damage modifiers from effects
            5. Apply optional effect to target
            6. Display results with appropriate verbosity

        Args:
            actor: The character using the ability (must have combat methods)
            target: The character being affected (must have combat methods)

        Returns:
            bool: True if ability was executed successfully, False on system errors

        Damage System:
            - Direct damage: No attack rolls, damage is automatically applied
            - Base damage: From ability's damage components
            - Bonus damage: From effects and modifiers
            - All damage calculated and applied together

        Effect System:
            - Ability's inherent effect applies if successful
            - Effect application uses standard resistance/immunity rules
            - Some effects may have their own success conditions

        Note:
            - Uses assertion for cooldown check (should be validated before calling)
            - Integrates with effect manager for damage bonuses
            - Uses global verbosity settings for output formatting
            - Returns True even if target resists effects (ability still executed)

        Example:
            ```python
            # Execute a dragon breath ability
            if breath.execute(dragon, adventurer):
                print("Breath weapon activated successfully")
            else:
                print("System error during ability execution")
            ```
        """
        actor_str = apply_character_type_color(actor.type, actor.name)
        target_str = apply_character_type_color(target.type, target.name)

        debug(f"{actor.name} attempts to use {self.name} on {target.name}.")

        # Check cooldown and uses
        assert not actor.is_on_cooldown(self), f"Action {self.name} is on cooldown."

        # Roll damage directly (no spell attack roll needed for most abilities)
        base_damage, base_damage_details = roll_damage_components_no_mind(
            actor, target, self.damage
        )

        # Get any damage modifiers from effects
        all_damage_modifiers = actor.effect_manager.get_damage_modifiers()
        bonus_damage, bonus_damage_details = roll_damage_components_no_mind(
            actor, target, all_damage_modifiers
        )

        # Calculate total damage
        total_damage = base_damage + bonus_damage
        damage_details = base_damage_details + bonus_damage_details

        # Check if target is defeated
        is_dead = not target.is_alive()

        # Display message
        msg = f"    🔥 {actor_str} uses [bold blue]{self.name}[/] on {target_str}"

        if GLOBAL_VERBOSE_LEVEL == 0:
            msg += f" dealing {total_damage} damage"
            if is_dead:
                msg += f" defeating {target_str}"
            elif self.effect:
                if self.apply_effect(actor, target, self.effect):
                    msg += f" and applying"
                else:
                    msg += f" and failing to apply"
                msg += f" [{get_effect_color(self.effect)}]{self.effect.name}[/]"
            msg += "."
        elif GLOBAL_VERBOSE_LEVEL >= 1:
            msg += f" dealing {total_damage} damage to {target_str} → "
            msg += " + ".join(damage_details) + ".\n"
            if is_dead:
                msg += f"        {target_str} is defeated."
            elif self.effect:
                if self.apply_effect(actor, target, self.effect):
                    msg += f"        {target_str} is affected by"
                else:
                    msg += f"        {target_str} is not affected by"
                msg += f" [{get_effect_color(self.effect)}]{self.effect.name}[/]."

        cprint(msg)

        return True

    # ============================================================================
    # DAMAGE CALCULATION METHODS
    # ============================================================================

    def get_damage_expr(self, actor: Any) -> str:
        """
        Returns the damage expression with variables substituted.

        This method builds a complete damage expression string by substituting
        all variable placeholders with their actual values from the actor's
        current state. Useful for displaying potential damage or tooltips.

        Variable Substitution:
            - {STR}, {DEX}, {CON}, {INT}, {WIS}, {CHA}: Ability modifiers
            - {PROF}: Proficiency bonus
            - {LEVEL}: Character level
            - Custom variables from actor's expression_variables method

        Args:
            actor: The character using the ability (must have expression variables)

        Returns:
            str: Complete damage expression with variables replaced by values

        Example:
            ```python
            # For breath weapon with CON scaling
            damage_expr = breath.get_damage_expr(dragon)
            # Returns: "4d6 + 5" (if CON modifier is +5)
            ```
        """
        return " + ".join(
            substitute_variables(component.damage_roll, actor)
            for component in self.damage
        )

    def get_min_damage(self, actor: Any) -> int:
        """
        Returns the minimum possible damage value for the ability.

        Calculates the theoretical minimum damage by assuming all dice
        roll their minimum values (1 for each die). This is useful for
        damage prediction and threat assessment.

        Args:
            actor: The character using the ability

        Returns:
            int: Minimum total damage across all damage components

        Example:
            ```python
            # For "3d8 + 4" damage
            min_dmg = ability.get_min_damage(character)
            # Returns: 7 (3*1 + 4)
            ```
        """
        return sum(
            parse_expr_and_assume_min_roll(
                substitute_variables(component.damage_roll, actor)
            )
            for component in self.damage
        )

    def get_max_damage(self, actor: Any) -> int:
        """
        Returns the maximum possible damage value for the ability.

        Calculates the theoretical maximum damage by assuming all dice
        roll their maximum values. This is useful for damage prediction,
        encounter balancing, and tactical planning.

        Args:
            actor: The character using the ability

        Returns:
            int: Maximum total damage across all damage components

        Example:
            ```python
            # For "3d8 + 4" damage
            max_dmg = ability.get_max_damage(character)
            # Returns: 28 (3*8 + 4)
            ```
        """
        return sum(
            parse_expr_and_assume_max_roll(
                substitute_variables(component.damage_roll, actor)
            )
            for component in self.damage
        )

    # ============================================================================
    # SERIALIZATION METHODS
    # ============================================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the ability to a dictionary representation.

        Creates a complete serializable representation of the ability including
        all properties from the base class plus ability-specific data like
        damage components, effects, and targeting expressions.

        Returns:
            dict: Complete dictionary representation suitable for JSON serialization

        Dictionary Structure:
            - Base properties: name, type, description, cooldown, maximum_uses
            - Ability properties: damage components, target_expr
            - Optional: effect data if an effect is attached

        Example:
            ```python
            ability_data = breath.to_dict()
            # Returns complete serializable dictionary
            ```
        """
        data = super().to_dict()
        # Add specific fields for BaseAbility
        data["damage"] = [component.to_dict() for component in self.damage]
        if self.target_expr:
            data["target_expr"] = self.target_expr
        if self.effect:
            data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "BaseAbility":
        """
        Creates a BaseAbility instance from a dictionary.

        Reconstructs a complete BaseAbility object from its dictionary
        representation, including all damage components, effects, and targeting
        configuration. This enables loading abilities from JSON configuration files.

        Args:
            data: Dictionary containing complete ability specification

        Returns:
            BaseAbility: Fully initialized ability instance

        Required Dictionary Keys:
            - name: Ability name (str)
            - type: ActionType enum value (str)
            - damage: List of damage component dictionaries

        Optional Dictionary Keys:
            - description: Ability description (str, default: "")
            - cooldown: Turns between uses (int, default: 0)
            - maximum_uses: Max uses per encounter (int, default: -1)
            - effect: Effect dictionary (dict, default: None)
            - target_expr: Target count expression (str, default: "")
            - target_restrictions: Custom targeting rules (list, default: None)

        Example:
            ```python
            ability_data = {...}  # From JSON config
            breath = BaseAbility.from_dict(ability_data)
            ```
        """
        return BaseAbility(
            name=data["name"],
            type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            damage=[DamageComponent.from_dict(comp) for comp in data["damage"]],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
            target_expr=data.get("target_expr", ""),
            target_restrictions=data.get("target_restrictions"),
        )


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================


def from_dict_ability(data: dict[str, Any]) -> BaseAbility | None:
    """
    Creates a BaseAbility instance from a dictionary using the factory pattern.

    This factory function automatically determines the correct ability class
    based on the 'class' field in the data dictionary and creates an
    appropriate instance. Currently only supports BaseAbility, but designed
    to be extensible for future ability subtypes.

    Supported Ability Classes:
        - "BaseAbility": Standard ability (default and currently only option)

    Args:
        data: Dictionary containing ability specification with optional 'class' field

    Returns:
        BaseAbility | None: BaseAbility instance, or None if class is not recognized

    Dictionary Requirements:
        - Must contain all required fields for BaseAbility class
        - Optional 'class' field to specify ability type (defaults to "BaseAbility")
        - Field names must match the class constructor parameters

    Example:
        ```python
        # Load ability polymorphically (future-ready)
        ability_data = {"class": "BaseAbility", "name": "Dragon Breath", ...}

        breath = from_dict_ability(ability_data)  # Returns BaseAbility
        ```

    Error Handling:
        Returns None for unrecognized class names rather than raising
        exceptions, allowing graceful handling of invalid data.

    Future Extensions:
        This function is designed to support future ability subtypes like
        BreathWeapon, SpellLikeAbility, or other specialized ability classes.
    """
    ability_class = data.get("class", "BaseAbility")

    if ability_class == "BaseAbility":
        return BaseAbility.from_dict(data)

    return None
