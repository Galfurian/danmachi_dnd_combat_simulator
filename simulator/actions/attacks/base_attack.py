from typing import Any

from actions.base_action import BaseAction
from combat.damage import (
    DamageComponent,
    roll_damage_components,
    roll_damage_components_no_mind,
)
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
    ensure_non_negative_int,
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


class BaseAttack(BaseAction):
    """
    Base class for all attack actions in the combat system.

    This class represents physical and weapon-based attacks that deal damage to targets.
    It handles attack rolls, damage calculation, critical hits, fumbles, and optional
    effects that trigger on successful hits.

    Attack Flow:
        1. Validate actor and target
        2. Check cooldowns and restrictions
        3. Roll attack vs target's AC
        4. On hit: Roll damage, apply effects, handle triggers
        5. Display results with appropriate verbosity

    Attributes:
        hands_required (int): Number of hands needed to perform this attack (0+)
        attack_roll (str): Expression for attack bonus (e.g., "STR + PROF")
        damage (list[DamageComponent]): List of damage components to roll
        effect (Effect | None): Optional effect applied on successful hits

    Critical Hit Logic:
        - Natural 20 on d20 = critical hit (double base damage)
        - Natural 1 on d20 = fumble (automatic miss)
        - Crits always hit regardless of AC

    Damage System:
        - Base damage from weapon/attack
        - Bonus damage from effects and modifiers
        - Trigger effects (like smite spells) activate on hit
        - All damage is calculated and applied together

    Note:
        - Inherits targeting logic from BaseAction (category = OFFENSIVE)
        - Supports both weapon attacks and natural attacks
        - Integrates with effect system for buffs/debuffs
        - Handles verbose output for combat logging
    """

    def __init__(
        self,
        name: str,
        type: ActionType,
        description: str,
        cooldown: int,
        maximum_uses: int,
        hands_required: int,
        attack_roll: str,
        damage: list[DamageComponent],
        effect: Effect | None = None,
        target_restrictions: list[str] | None = None,
    ):
        """
        Initialize a new BaseAttack.

        Args:
            name: The display name of the attack
            type: The type of action (usually ActionType.ATTACK)
            description: Description of what the attack does
            cooldown: Turns to wait before reusing (0 = no cooldown)
            maximum_uses: Max uses per encounter/day (-1 = unlimited)
            hands_required: Number of hands needed (0 = no hands, 1 = one-handed, 2 = two-handed)
            attack_roll: Attack bonus expression (e.g., "STR + PROF", "DEX + PROF + 2")
            damage: List of damage components (base weapon damage, stat bonuses, etc.)
            effect: Optional effect applied on successful hits (poison, bleeding, etc.)
            target_restrictions: Override default offensive targeting if needed

        Raises:
            ValueError: If name is empty or type/category are invalid

        Note:
            - Category is automatically set to OFFENSIVE
            - Invalid hands_required values are corrected to 0 with warnings
            - Invalid attack_roll expressions are corrected to empty string
            - Damage list is validated to ensure all components are DamageComponent instances
            - Invalid effects are set to None with warnings

        Example:
            ```python
            # Create a longsword attack
            longsword = BaseAttack(
                name="Longsword",
                type=ActionType.ATTACK,
                description="A versatile steel blade",
                cooldown=0,
                maximum_uses=-1,
                hands_required=1,
                attack_roll="STR + PROF",
                damage=[DamageComponent("1d8", "slashing", "STR")],
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

            # Validate hands_required using helper
            self.hands_required = ensure_non_negative_int(
                hands_required, "hands required", 0, {"name": name}
            )

            # Validate attack_roll using helper
            self.attack_roll = ensure_string(
                attack_roll, "attack roll", "", {"name": name}
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
                    f"Attack {name} effect must be Effect or None, got: {effect.__class__.__name__}, setting to None",
                    {"name": name, "effect": effect},
                )
                effect = None

            self.effect: Effect | None = effect

        except Exception as e:
            log_critical(
                f"Error initializing BaseAttack {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

    # ============================================================================
    # COMBAT EXECUTION METHODS
    # ============================================================================

    def execute(self, actor: Any, target: Any) -> bool:
        """
        Execute this attack against a target.

        This method handles the complete attack sequence from validation through
        damage application. It includes attack rolls, critical hit detection,
        damage calculation, effect application, and result display.

        Attack Sequence:
            1. Validate actor and target objects
            2. Check cooldowns and usage restrictions
            3. Build and roll attack vs target AC
            4. Handle fumbles (natural 1) and misses
            5. On hit: Calculate damage, apply effects, handle triggers
            6. Display results with appropriate verbosity level

        Args:
            actor: The character performing the attack (must have combat methods)
            target: The character being attacked (must have AC and combat methods)

        Returns:
            bool: True if attack was executed successfully, False on validation errors

        Critical Hit System:
            - Natural 20: Critical hit, double base damage, always hits
            - Natural 1: Fumble, automatic miss regardless of bonuses
            - Regular hit: Attack total >= target AC

        Damage System:
            - Base damage: From weapon/attack damage components
            - Bonus damage: From effects, modifiers, and triggered abilities
            - Critical hits: Double base damage only (not bonuses)
            - All damage applied together after calculation

        Effect System:
            - On-hit trigger effects activate (like smite spells)
            - Triggered effects apply to target with proper mind levels
            - Attack's inherent effect applies if successful hit

        Note:
            - Returns True even for misses/fumbles (attack was executed)
            - Returns False only for validation/system errors
            - Uses global verbosity settings for output formatting
            - Integrates with effect manager for damage bonuses

        Example:
            ```python
            # Execute a sword attack
            if sword.execute(fighter, goblin):
                print("Attack completed successfully")
            else:
                print("Attack failed due to system error")
            ```
        """
        try:
            # Validate required objects using helpers
            validate_required_object(
                actor,
                "actor",
                ["name", "type", "is_on_cooldown", "get_expression_variables"],
                {"action": self.name},
            )
            validate_required_object(
                target,
                "target",
                ["name", "type"],
                {
                    "action": self.name,
                    "actor": safe_get_attribute(actor, "name", "Unknown"),
                },
            )

            actor_str = apply_character_type_color(actor.type, actor.name)
            target_str = apply_character_type_color(target.type, target.name)

            debug(f"{actor.name} attempts a {self.name} on {target.name}.")

            # Check cooldown
            if not hasattr(actor, "is_on_cooldown"):
                log_error(
                    f"Actor lacks is_on_cooldown method for {self.name}",
                    {"action": self.name, "actor": actor.name},
                )
                return False

            if actor.is_on_cooldown(self):
                log_warning(
                    f"Action {self.name} is on cooldown",
                    {"action": self.name, "actor": actor.name},
                )
                return False

            # --- Build & resolve attack roll ---

            # Get attack modifier from the actor's effect manager.
            if not hasattr(actor, "effect_manager"):
                log_error(
                    f"Actor lacks effect_manager for {self.name}",
                    {"action": self.name, "actor": actor.name},
                )
                return False

            attack_modifier = actor.effect_manager.get_modifier(BonusType.ATTACK)

            # Roll the attack.
            attack_total, attack_roll_desc, d20_roll = self.roll_attack_with_crit(
                actor, self.attack_roll, attack_modifier
            )

            # Detect crit and fumble.
            is_crit = d20_roll == 20
            is_fumble = d20_roll == 1

            msg = f"    🎯 {actor_str} attacks {target_str} with [bold blue]{self.name}[/]"

            # --- Outcome: MISS ---

            if is_fumble:
                if GLOBAL_VERBOSE_LEVEL >= 1:
                    msg += f" rolled ({attack_roll_desc}) [magenta]{attack_total}[/] vs AC [yellow]{target.AC}[/]"
                msg += " and [magenta]fumble![/]"
                cprint(msg)
                return True

            if attack_total < target.AC and not is_crit:
                if GLOBAL_VERBOSE_LEVEL >= 1:
                    msg += f" rolled ({attack_roll_desc}) [red]{attack_total}[/] vs AC [yellow]{target.AC}[/]"
                msg += " and [red]miss![/]"
                cprint(msg)
                return True

            # --- Outcome: HIT ---

            # First roll the attack damage from the attack.
            base_damage, base_damage_details = roll_damage_components_no_mind(
                actor, target, self.damage
            )

            # If it's a crit, double the base damage.
            if is_crit:
                base_damage *= 2

            # Trigger OnHitTrigger effects (like Searing Smite)
            trigger_damage_bonuses, trigger_effects_with_levels, consumed_triggers = (
                actor.effect_manager.trigger_on_hit_effects(target)
            )

            # Apply trigger effects to target with proper mind levels
            for effect, mind_level in trigger_effects_with_levels:
                if effect.can_apply(actor, target):
                    target.effect_manager.add_effect(actor, effect, mind_level)

            # Then roll any additional damage from effects (including triggered damage bonuses).
            all_damage_modifiers = (
                actor.effect_manager.get_damage_modifiers() + trigger_damage_bonuses
            )
            bonus_damage, bonus_damage_details = roll_damage_components(
                actor, target, all_damage_modifiers
            )

            # Extend the total damage and details with bonus damage.
            total_damage = base_damage + bonus_damage
            damage_details = base_damage_details + bonus_damage_details

            # Is target still alive?
            is_dead = not target.is_alive()

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
                msg += f" rolled ({attack_roll_desc}) {attack_total} vs AC [yellow]{target.AC}[/] and "
                msg += f"[magenta]crit![/]\n" if is_crit else "[green]hit![/]\n"
                msg += f"        Dealing {total_damage} damage to {target_str} → "
                msg += " + ".join(damage_details) + ".\n"
                if is_dead:
                    msg += f"        {target_str} is defeated."
                elif self.effect:
                    if self.apply_effect(actor, target, self.effect):
                        msg += f"        {target_str} is affected by"
                    else:
                        msg += f"        {target_str} is not affected by"
                    msg += f" [{get_effect_color(self.effect)}]{self.effect.name}[/]."

            # Display messages for consumed OnHitTrigger effects
            for trigger in consumed_triggers:
                trigger_msg = f"    ⚡ {actor_str}'s [bold][{get_effect_color(trigger)}]{trigger.name}[/][/] activates!"
                cprint(trigger_msg)

            cprint(msg)

            return True

        except Exception as e:
            log_error(
                f"Error executing attack {self.name}: {str(e)}",
                {
                    "action": self.name,
                    "error": str(e),
                    "actor": getattr(actor, "name", "Unknown"),
                    "target": getattr(target, "name", "Unknown"),
                },
                e,
            )
            return False

    # ============================================================================
    # DAMAGE CALCULATION METHODS
    # ============================================================================

    def get_damage_expr(self, actor: Any) -> str:
        """
        Returns the damage expression with variables substituted.

        This method builds a complete damage expression string by substituting
        all variable placeholders with their actual values from the actor's
        current state. The result is a human-readable representation of the
        total damage calculation.

        Variable Substitution:
            - {STR}, {DEX}, {CON}, {INT}, {WIS}, {CHA}: Ability modifiers
            - {PROF}: Proficiency bonus
            - {LEVEL}: Character level
            - Custom variables from actor's expression_variables method

        Args:
            actor: The character performing the action (must have expression variables)

        Returns:
            str: Complete damage expression with variables replaced by values

        Example:
            ```python
            # For a longsword with STR modifier
            damage_expr = weapon.get_damage_expr(fighter)
            # Returns: "1d8 + 3" (if STR modifier is +3)
            ```
        """
        return " + ".join(
            substitute_variables(component.damage_roll, actor)
            for component in self.damage
        )

    def get_min_damage(self, actor: Any) -> int:
        """
        Returns the minimum possible damage value for the attack.

        Calculates the theoretical minimum damage by assuming all dice
        roll their minimum values (1 for each die). This is useful for
        damage prediction and combat analysis.

        Args:
            actor: The character performing the action

        Returns:
            int: Minimum total damage across all damage components

        Example:
            ```python
            # For "2d6 + 4" damage
            min_dmg = weapon.get_min_damage(fighter)
            # Returns: 6 (2*1 + 4)
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
        Returns the maximum possible damage value for the attack.

        Calculates the theoretical maximum damage by assuming all dice
        roll their maximum values. This is useful for damage prediction,
        combat planning, and threat assessment.

        Args:
            actor: The character performing the action

        Returns:
            int: Maximum total damage across all damage components

        Example:
            ```python
            # For "2d6 + 4" damage
            max_dmg = weapon.get_max_damage(fighter)
            # Returns: 16 (2*6 + 4)
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
        Convert the attack to a dictionary representation.

        Creates a complete serializable representation of the attack including
        all properties from the base class plus attack-specific data like
        damage components and required hands.

        Returns:
            dict: Complete dictionary representation suitable for JSON serialization

        Dictionary Structure:
            - Base properties: name, type, description, cooldown, maximum_uses
            - Attack properties: hands_required, attack_roll, damage components
            - Optional: effect data if an effect is attached

        Example:
            ```python
            attack_data = sword.to_dict()
            # Returns complete serializable dictionary
            ```
        """
        # Get the base dictionary representation.
        data = super().to_dict()
        # Add specific fields for BaseAttack
        data["hands_required"] = self.hands_required
        data["attack_roll"] = self.attack_roll
        data["damage"] = [component.to_dict() for component in self.damage]
        # Include the effect if it exists.
        if self.effect:
            data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "BaseAttack":
        """
        Creates a BaseAttack instance from a dictionary.

        Reconstructs a complete BaseAttack object from its dictionary
        representation, including all damage components and optional effects.
        This enables loading attacks from JSON configuration files.

        Args:
            data: Dictionary containing complete attack specification

        Returns:
            BaseAttack: Fully initialized attack instance

        Required Dictionary Keys:
            - name: Attack name (str)
            - type: ActionType enum value (str)
            - attack_roll: Attack roll expression (str)
            - damage: List of damage component dictionaries

        Optional Dictionary Keys:
            - description: Attack description (str, default: "")
            - cooldown: Turns between uses (int, default: 0)
            - maximum_uses: Max uses per encounter (int, default: -1)
            - hands_required: Required hands (int, default: 0)
            - effect: Effect dictionary (dict, default: None)

        Example:
            ```python
            sword_data = {...}  # From JSON config
            sword = BaseAttack.from_dict(sword_data)
            ```
        """
        return BaseAttack(
            name=data["name"],
            type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            hands_required=data.get("hands_required", 0),
            attack_roll=data["attack_roll"],
            damage=[DamageComponent.from_dict(comp) for comp in data["damage"]],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
        )
