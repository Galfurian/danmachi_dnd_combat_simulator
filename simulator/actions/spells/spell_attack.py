"""
Offensive spell attack implementation.

This module contains the SpellAttack class for damage-dealing magical spells
that require attack rolls and can apply additional effects on successful hits.
"""

from logging import debug
from typing import Any

from actions.spells.base_spell import Spell
from combat.damage import DamageComponent, roll_damage_components
from core.constants import (
    ActionCategory,
    ActionType,
    BonusType,
    GLOBAL_VERBOSE_LEVEL,
    get_character_type_color,
    get_effect_color,
)
from core.error_handling import (
    log_error,
    log_warning,
    log_critical,
    ensure_list_of_type,
)
from core.utils import (
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    substitute_variables,
    cprint,
)
from effects.effect import Effect


class SpellAttack(Spell):
    """
    Offensive spell that deals damage through magical attacks.
    
    SpellAttack represents damage-dealing spells that require spell attack rolls
    against the target's Armor Class (AC). These spells combine the targeting
    mechanics of weapon attacks with the level scaling and mind cost system
    of magical spells.
    
    Core Mechanics:
        - Spell Attack Rolls: Uses caster's spell attack bonus vs target AC
        - Critical Hits: Natural 20 always hits and triggers critical damage
        - Fumbles: Natural 1 always misses regardless of bonuses
        - Level Scaling: Damage expressions can use MIND variable for scaling
        - Optional Effects: Can apply additional effects on successful hits
        
    Damage System:
        Each spell has a list of DamageComponent objects that define:
        - Damage type (fire, cold, force, etc.)
        - Damage expression with level scaling support
        - Critical hit behavior
        
    Attack Resolution:
        1. Check mind point availability and cooldowns
        2. Roll 1d20 + spell attack bonus + modifiers
        3. Compare against target's AC (nat 20 always hits)
        4. On hit: Roll damage components and apply effects
        5. Display detailed combat feedback
        
    Level Scaling Examples:
        - "3d6": Static damage regardless of spell level
        - "2d6 + MIND": Adds spell level to damage
        - "MIND d6": Number of dice scales with spell level
        - "3d6 + MIND * 2": Damage increases by 2 per level
        
    Multi-Target Support:
        SpellAttack supports multi-target spells through target_expr:
        - Single target: target_expr = "" (default)
        - Multiple targets: target_expr = "3" or "MIND"
        - Each target gets separate attack rolls and damage
        
    Effect Integration:
        Optional effects can be applied on successful hits:
        - Damage over time effects
        - Status conditions (paralyzed, stunned, etc.)
        - Temporary debuffs or ongoing damage
        
    Example Usage:
        ```python
        # Single-target damage spell
        magic_missile = SpellAttack(
            name="Magic Missile",
            type=ActionType.ACTION,
            description="Unerring bolts of magical force",
            level=1,
            mind_cost=[2, 4, 6],
            damage=[DamageComponent("force", "1d4 + 1 + MIND")],
            requires_concentration=False
        )
        
        # Multi-target area spell with effect
        fireball = SpellAttack(
            name="Fireball", 
            type=ActionType.ACTION,
            description="A bright flash followed by explosive flame",
            level=3,
            mind_cost=[6, 8, 10, 12],
            damage=[DamageComponent("fire", "8d6 + MIND")],
            effect=BurnEffect(duration=3),
            target_expr="MIND + 2",  # Affects spell level + 2 targets
            requires_concentration=False
        )
        ```
        
    Attributes:
        damage: List of damage components defining damage dice and types
        effect: Optional effect applied on successful spell attacks
        
    Note:
        SpellAttack inherits all spell mechanics (mind costs, concentration,
        targeting) from the base Spell class while adding attack roll logic
        and damage application specific to offensive magic.
    """
    def __init__(
        self,
        name: str,
        type: ActionType,
        description: str,
        cooldown: int,
        maximum_uses: int,
        level: int,
        mind_cost: list[int],
        damage: list[DamageComponent],
        effect: Effect | None = None,
        target_expr: str = "",
        requires_concentration: bool = False,
        target_restrictions: list[str] | None = None,
    ):
        """
        Initialize a new SpellAttack.
        
        Creates an offensive spell that combines spell attack mechanics with
        level-scaling damage components. The spell uses mind points for casting
        and can optionally apply effects on successful hits.
        
        Args:
            name: Display name of the spell
            type: Action type (ACTION, BONUS_ACTION, REACTION, etc.)
            description: Flavor text describing the spell's appearance/effects
            cooldown: Turns to wait before reusing (0 = no cooldown)
            maximum_uses: Max uses per encounter/day (-1 = unlimited)
            level: Base spell level determining scaling and prerequisites
            mind_cost: List of mind point costs per casting level
            damage: List of damage components with scaling expressions
            effect: Optional effect applied on successful spell attacks
            target_expr: Expression for multi-target spells ("" = single target)
            requires_concentration: Whether spell needs ongoing mental focus
            target_restrictions: Override default targeting restrictions
            
        Damage Components:
            Each DamageComponent defines a damage type and scaling expression:
            - damage_type: "fire", "cold", "force", "necrotic", etc.
            - damage_roll: Expression supporting MIND variable scaling
            
        Examples:
            ```python
            # Single-target spell with static damage
            magic_missile = SpellAttack(
                name="Magic Missile",
                type=ActionType.ACTION,
                description="Unerring bolts of force",
                level=1,
                mind_cost=[2, 4, 6],
                damage=[DamageComponent("force", "1d4 + 1")]
            )
            
            # Multi-target spell with level scaling
            fireball = SpellAttack(
                name="Fireball",
                type=ActionType.ACTION, 
                description="Explosive blast of flame",
                level=3,
                mind_cost=[6, 8, 10, 12],
                damage=[DamageComponent("fire", "8d6 + MIND")],
                target_expr="MIND + 1",  # Extra targets per level
                effect=BurnEffect(duration=2)
            )
            
            # Mixed damage spell with concentration effect
            chromatic_orb = SpellAttack(
                name="Chromatic Orb",
                type=ActionType.ACTION,
                description="Sphere of crackling energy",
                level=1,
                mind_cost=[3, 5, 7],
                damage=[
                    DamageComponent("fire", "2d8"),
                    DamageComponent("cold", "1d4 + MIND//2")
                ],
                effect=SlowEffect(duration=3),
                requires_concentration=True
            )
            ```
            
        Raises:
            ValueError: If name is empty, damage list is empty, or invalid types
            AssertionError: If damage components are malformed
            
        Note:
            - Automatically sets category to ActionCategory.OFFENSIVE
            - Validates all damage components during initialization
            - Empty damage list raises an error as attack spells must deal damage
            - Effect is optional but commonly used for status conditions
        """
        try:
            super().__init__(
                name,
                type,
                description,
                cooldown,
                maximum_uses,
                level,
                mind_cost,
                ActionCategory.OFFENSIVE,
                target_expr,
                requires_concentration,
                target_restrictions,
            )

            # Validate damage components using helper
            if not damage or not isinstance(damage, list) or len(damage) == 0:
                log_critical(
                    f"SpellAttack {name} must have at least one damage component",
                    {"name": name, "damage": damage}
                )
                raise ValueError(f"SpellAttack {name} must have at least one damage component")
                
            self.damage = ensure_list_of_type(
                damage,
                DamageComponent,
                "damage components",
                context={"name": name},
            )

            # Validate optional effect
            if effect is not None and not isinstance(effect, Effect):
                log_warning(
                    f"SpellAttack {name} effect must be Effect or None, got: {type(effect).__name__}, setting to None",
                    {"name": name, "effect_type": type(effect).__name__},
                )
                effect = None

            self.effect = effect

        except Exception as e:
            log_critical(
                f"Error initializing SpellAttack {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

    # ============================================================================
    # SPELL ATTACK METHODS
    # ============================================================================

    def cast_spell(self, actor: Any, target: Any, mind_level: int) -> bool:
        """
        Execute an offensive spell attack with complete combat resolution.
        
        Performs a full spell attack sequence including mind cost validation,
        spell attack rolls, damage calculation, and effect application. This
        method handles all aspects of offensive spell casting from resource
        management to combat feedback.
        
        Args:
            actor: The character casting the spell (must have mind points)
            target: The character being attacked
            mind_level: The spell level to cast at (affects cost and damage)
            
        Returns:
            bool: True if spell was successfully cast (regardless of hit/miss)
            
        Attack Resolution Process:
            1. Validate mind cost and cooldowns
            2. Calculate spell attack bonus and modifiers
            3. Roll 1d20 + spell attack bonus vs target AC
            4. Handle special cases (critical hits, fumbles)
            5. Calculate and apply damage on successful hits
            6. Apply optional effects if damage dealt
            7. Display detailed combat feedback
            
        Mind Cost System:
            Uses the mind_cost list to determine resource consumption:
            - mind_level=1 uses mind_cost[0]
            - mind_level=2 uses mind_cost[1]
            - Higher levels increase both cost and damage potential
            
        Critical Hit Mechanics:
            - Natural 20: Always hits, triggers critical damage
            - Natural 1: Always misses (fumble)
            - Critical damage: All damage dice are maximized
            
        Damage Scaling:
            Each damage component can use the MIND variable for level scaling:
            - "3d6": Static damage
            - "3d6 + MIND": Adds spell level to damage
            - "MIND d6": Dice count scales with level
            
        Multi-Target Support:
            For spells with target_expr, this method is called once per target
            with separate attack rolls and damage calculations for each.
            
        Error Handling:
            - Returns False if insufficient mind points
            - Raises AssertionError if spell is on cooldown
            - Logs all failures with detailed context
            
        Example:
            ```python
            # Cast fireball at level 3 (costs mind_cost[2])
            success = fireball.cast_spell(wizard, enemy, mind_level=3)
            ```
        """
        debug(f"{actor.name} attempts to cast {self.name} on {target.name}.")

        # Validate mind cost against the specified level
        if mind_level < 1 or mind_level > len(self.mind_cost):
            log_error(
                f"{actor.name} cannot cast {self.name} at invalid level {mind_level}",
                {"actor": actor.name, "spell": self.name, "mind_level": mind_level, "max_levels": len(self.mind_cost)}
            )
            return False
            
        required_mind = self.mind_cost[mind_level - 1]
        if actor.mind < required_mind:
            log_error(
                f"{actor.name} does not have enough mind to cast {self.name}",
                {"actor": actor.name, "spell": self.name, "mind_required": required_mind, "mind_current": actor.mind}
            )
            return False

        # Check cooldown restrictions
        if actor.is_on_cooldown(self):
            log_warning(
                f"Cannot cast {self.name} - spell is on cooldown",
                {"actor": actor.name, "spell": self.name}
            )
            return False

        # Handle concentration requirements
        if self.requires_concentration:
            actor.effect_manager.break_concentration(actor)

        # Deduct mind cost
        actor.mind -= required_mind

        # Format character strings for output
        actor_str = f"[{get_character_type_color(actor.type)}]{actor.name}[/]"
        target_str = f"[{get_character_type_color(target.type)}]{target.name}[/]"

        # Calculate spell attack components
        spell_attack_bonus = actor.get_spell_attack_bonus(self.level)
        attack_modifier = actor.effect_manager.get_modifier(BonusType.ATTACK)

        # Roll spell attack vs target AC
        attack_total, attack_roll_desc, d20_roll = self.roll_attack_with_crit(
            actor, spell_attack_bonus, attack_modifier
        )

        # Determine special outcomes
        is_crit = d20_roll == 20
        is_fumble = d20_roll == 1

        msg = f"    🎯 {actor_str} casts [bold]{self.name}[/] on {target_str}"

        # Handle fumble (always misses)
        if is_fumble:
            if GLOBAL_VERBOSE_LEVEL >= 1:
                msg += f" rolled ({attack_roll_desc}) [magenta]{attack_total}[/] vs AC [yellow]{target.AC}[/]"
            msg += " and [magenta]fumble![/]"
            cprint(msg)
            return True

        # Handle miss (unless critical hit)
        if attack_total < target.AC and not is_crit:
            if GLOBAL_VERBOSE_LEVEL >= 1:
                msg += f" rolled ({attack_roll_desc}) [red]{attack_total}[/] vs AC [yellow]{target.AC}[/]"
            msg += " and [red]miss![/]"
            cprint(msg)
            return True

        # Handle successful hit - calculate and apply damage
        damage_components = [(component, mind_level) for component in self.damage]
        total_damage, damage_details = roll_damage_components(
            actor, target, damage_components
        )

        # Check if target was defeated
        is_dead = not target.is_alive()

        # Apply optional effect on successful hit
        effect_applied = False
        if self.effect:
            effect_applied = self.apply_effect(actor, target, self.effect, mind_level)

        # Display combat results with appropriate detail level
        if GLOBAL_VERBOSE_LEVEL == 0:
            msg += f" dealing {total_damage} damage"
            if is_dead:
                msg += f" defeating {target_str}"
            elif effect_applied and self.effect:
                msg += f" and applying [{get_effect_color(self.effect)}]{self.effect.name}[/]"
            msg += "."
        elif GLOBAL_VERBOSE_LEVEL >= 1:
            msg += f" rolled ({attack_roll_desc}) {attack_total} vs AC [yellow]{target.AC}[/] → "
            msg += "[magenta]crit![/]\n" if is_crit else "[green]hit![/]\n"
            msg += f"        Dealing {total_damage} damage to {target_str} → "
            msg += " + ".join(damage_details) + ".\n"
            if is_dead:
                msg += f"        {target_str} is defeated."
            elif effect_applied and self.effect:
                msg += f"        {target_str} is affected by "
                msg += f"[{get_effect_color(self.effect)}]{self.effect.name}[/]."
        cprint(msg)

        return True

    # ============================================================================
    # DAMAGE CALCULATION METHODS  
    # ============================================================================

    def get_damage_expr(self, actor: Any, mind_level: int | None = 1) -> str:
        """
        Get damage expression with variables substituted for display.
        
        Returns the complete damage expression string with all variables
        (MIND, character stats, etc.) substituted with their actual values.
        This is primarily used for UI display and damage preview.
        
        Args:
            actor: The character casting the spell
            mind_level: The spell level to use for MIND variable substitution
            
        Returns:
            str: Complete damage expression with variables substituted
            
        Example:
            ```python
            # For spell with damage "3d6 + MIND + STR"
            expr = spell.get_damage_expr(wizard, mind_level=3)
            # Returns: "3d6 + 3 + 2" (if wizard has STR modifier of +2)
            ```
        """
        if mind_level is None:
            mind_level = 1
            
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return " + ".join(
            substitute_variables(component.damage_roll, variables)
            for component in self.damage
        )

    def get_min_damage(self, actor: Any, mind_level: int | None = 1) -> int:
        """
        Calculate the minimum possible damage for the spell.
        
        Computes the lowest possible damage by assuming minimum rolls on all
        dice expressions. This is useful for damage range displays and AI
        decision making.
        
        Args:
            actor: The character casting the spell
            mind_level: The spell level to use for scaling calculations
            
        Returns:
            int: Minimum possible damage (sum of all components' minimums)
            
        Example:
            ```python
            # For "2d6 + 3" damage, returns 5 (2*1 + 3)
            min_dmg = spell.get_min_damage(wizard, mind_level=2)
            ```
        """
        if mind_level is None:
            mind_level = 1
            
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return sum(
            parse_expr_and_assume_min_roll(
                substitute_variables(component.damage_roll, variables)
            )
            for component in self.damage
        )

    def get_max_damage(self, actor: Any, mind_level: int | None = 1) -> int:
        """
        Calculate the maximum possible damage for the spell.
        
        Computes the highest possible damage by assuming maximum rolls on all
        dice expressions. This represents the spell's damage ceiling and is
        useful for damage range displays and tactical planning.
        
        Args:
            actor: The character casting the spell
            mind_level: The spell level to use for scaling calculations
            
        Returns:
            int: Maximum possible damage (sum of all components' maximums)
            
        Example:
            ```python
            # For "2d6 + 3" damage, returns 15 (2*6 + 3)
            max_dmg = spell.get_max_damage(wizard, mind_level=2)
            ```
        """
        if mind_level is None:
            mind_level = 1
            
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return sum(
            parse_expr_and_assume_max_roll(
                substitute_variables(component.damage_roll, variables)
            )
            for component in self.damage
        )

    # ============================================================================
    # SERIALIZATION METHODS
    # ============================================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the spell attack to a dictionary representation.
        
        Creates a complete serializable representation including all base spell
        properties plus damage components and optional effects. This supports
        saving/loading spells and data exchange.
        
        Returns:
            dict: Complete dictionary suitable for JSON serialization
            
        Dictionary Structure:
            - Base properties: name, type, description, cooldown, etc.
            - Spell properties: level, mind_cost, requires_concentration
            - Attack properties: damage components list, optional effect
            - Optional: target_expr if multi-target
            
        Example:
            ```python
            data = fireball.to_dict()
            # Contains all spell data for reconstruction
            rebuilt = SpellAttack.from_dict(data)
            ```
        """
        data = super().to_dict()
        # Add SpellAttack-specific properties
        data["damage"] = [component.to_dict() for component in self.damage]
        # Include optional effect if present
        if self.effect:
            data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SpellAttack":
        """
        Create a SpellAttack instance from a dictionary.
        
        Factory method that reconstructs a SpellAttack from its dictionary
        representation. Handles all validation and type conversion needed
        for safe deserialization.
        
        Args:
            data: Dictionary containing spell attack data
            
        Returns:
            SpellAttack: Fully initialized spell attack instance
            
        Raises:
            KeyError: If required fields are missing
            ValueError: If data types are invalid
            
        Example:
            ```python
            spell_data = {
                "name": "Fireball",
                "type": "ACTION",
                "level": 3,
                "mind_cost": [6, 8, 10],
                "damage": [{"damage_type": "fire", "damage_roll": "8d6"}]
            }
            fireball = SpellAttack.from_dict(spell_data)
            ```
        """
        return SpellAttack(
            name=data["name"],
            type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            level=data["level"],
            mind_cost=data["mind_cost"],
            damage=[
                DamageComponent.from_dict(component) for component in data["damage"]
            ],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
            target_expr=data.get("target_expr", ""),
            requires_concentration=data.get("requires_concentration", False),
            target_restrictions=data.get("target_restrictions"),
        )
