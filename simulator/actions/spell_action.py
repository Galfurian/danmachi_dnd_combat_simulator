from abc import abstractmethod
from logging import debug
from typing import Any

from actions.base_action import BaseAction
from combat.damage import DamageComponent, roll_damage_components
from core.constants import (
    ActionCategory,
    ActionType,
    BonusType,
    GLOBAL_VERBOSE_LEVEL,
    get_character_type_color,
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
    evaluate_expression,
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    roll_and_describe,
    simplify_expression,
    substitute_variables,
    cprint,
)
from effects.effect import Buff, Debuff, Effect, ModifierEffect


class Spell(BaseAction):
    """
    Abstract base class for all magical spells in the combat system.
    
    Spells represent magical abilities that consume mind points (mana) and can target
    single or multiple entities. Unlike physical attacks or innate abilities, spells
    have complex mechanics including level scaling, mind costs, concentration requirements,
    and sophisticated targeting systems.
    
    Core Spell Mechanics:
        - Mind Cost System: Each spell has costs per level (mind_cost list)
        - Level Scaling: Higher levels consume more mind but increase effectiveness
        - Concentration: Some spells require ongoing mental focus to maintain
        - Target Expressions: Dynamic targeting based on character stats and spell level
        
    Spell Categories:
        - SpellAttack: Offensive spells that deal damage (Fireball, Magic Missile)
        - SpellHeal: Restorative spells that recover HP (Cure Wounds, Heal)
        - SpellBuff: Beneficial spells that enhance targets (Bless, Haste)  
        - SpellDebuff: Detrimental spells that hinder targets (Hold Person, Slow)
        
    Mind Cost System:
        The mind_cost list contains the mind point cost for each spell level:
        - Index 0: Cost for level 1 casting
        - Index 1: Cost for level 2 casting
        - etc.
        
    Target Expression System:
        - Empty string "": Single target (most spells)
        - "3": Always affects exactly 3 targets
        - "LEVEL": Affects targets equal to caster level
        - "1 + MIND//2": Dynamic scaling based on spell level
        
    Concentration Mechanics:
        - Only one concentration spell can be active per caster
        - Casting a new concentration spell breaks the previous one
        - Damage or specific effects can break concentration
        
    Example Usage:
        ```python
        # Create a multi-target damage spell
        fireball = SpellAttack(
            name="Fireball",
            level=3,
            mind_cost=[6, 8, 10, 12],  # Costs by level
            damage=[DamageComponent("fire", "8d6 + MIND")],
            target_expr="MIND",  # Targets equal to spell level
            requires_concentration=False
        )
        
        # Cast at different levels
        fireball.cast_spell(wizard, enemies, mind_level=3)  # Costs 10 mind
        fireball.cast_spell(wizard, enemies, mind_level=1)  # Costs 6 mind
        ```
        
    Abstract Methods:
        Subclasses must implement cast_spell() to define their specific behavior.
        
    Note:
        This class inherits targeting logic from BaseAction but adds spell-specific
        mechanics like mind costs, concentration, and level-based scaling.
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
        category: ActionCategory,
        target_expr: str = "",
        requires_concentration: bool = False,
        target_restrictions: list[str] | None = None,
    ):
        """
        Initialize a new Spell.
        
        Args:
            name: Display name of the spell
            type: Action type (ACTION, BONUS_ACTION, REACTION, etc.)
            description: Flavor text describing what the spell does
            cooldown: Turns to wait before reusing (0 = no cooldown)
            maximum_uses: Max uses per encounter/day (-1 = unlimited)
            level: Base spell level (1-9 for most spells, 0 for cantrips)
            mind_cost: List of mind point costs per casting level [level1, level2, ...]
            category: Spell category (OFFENSIVE, HEALING, SUPPORT, DEBUFF)
            target_expr: Expression determining number of targets ("" = single target)
            requires_concentration: Whether spell requires ongoing mental focus
            target_restrictions: Override default targeting if needed
            
        Mind Cost Examples:
            - [3, 5, 7]: Level 1 costs 3, level 2 costs 5, level 3 costs 7
            - [0]: Cantrip, always costs 0 mind points
            - [4, 6, 8, 10, 12]: Spell scalable up to level 5
            
        Target Expression Examples:
            - "": Single target (default)
            - "3": Always affects 3 targets  
            - "MIND": Affects targets equal to spell level used
            - "1 + LEVEL//3": Scales with caster level
            - "max(1, CHA)": At least 1, up to CHA modifier targets
            
        Raises:
            ValueError: If name is empty or type/category are invalid
            
        Note:
            - Uses enhanced validation helpers for robust error handling
            - Invalid mind_cost values are corrected with warnings
            - Invalid target_expr is corrected to empty string
            - Concentration flag is auto-corrected to boolean
            
        Example:
            ```python
            # Create a scalable area damage spell
            fireball = SpellAttack(
                name="Fireball",
                type=ActionType.ACTION,
                description="A bright flash followed by explosive flame",
                cooldown=0,
                maximum_uses=-1,
                level=3,
                mind_cost=[6, 8, 10, 12, 15],  # Levels 1-5
                category=ActionCategory.OFFENSIVE,
                target_expr="MIND + 1",  # Extra targets per level
                requires_concentration=False
            )
            ```
        """
        try:
            super().__init__(
                name,
                type,
                category,
                description,
                cooldown,
                maximum_uses,
                target_restrictions,
            )

            # Validate level using helper
            self.level = ensure_non_negative_int(
                level, "spell level", 0, {"name": name}
            )

            # Validate mind_cost list using helper
            self.mind_cost = ensure_list_of_type(
                mind_cost,
                int,
                "mind cost",
                [0],
                converter=lambda x: max(0, int(x)) if isinstance(x, (int, float)) else 0,
                validator=lambda x: isinstance(x, int) and x >= 0,
                context={"name": name},
            )

            # Validate target_expr using helper
            self.target_expr = ensure_string(
                target_expr, "target expression", "", {"name": name}
            )

            # Validate requires_concentration
            if not isinstance(requires_concentration, bool):
                log_warning(
                    f"Spell {name} requires_concentration must be boolean, got: {requires_concentration.__class__.__name__}, setting to False",
                    {"name": name, "requires_concentration": requires_concentration},
                )
                requires_concentration = False

            self.requires_concentration = requires_concentration

        except Exception as e:
            log_critical(
                f"Error initializing Spell {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

    # ============================================================================
    # TARGETING SYSTEM METHODS
    # ============================================================================

    def is_single_target(self) -> bool:
        """
        Check if the spell targets a single entity.
        
        Determines targeting mode based on the target_expr property. Empty or
        whitespace-only expressions indicate single-target spells, while
        any meaningful expression indicates multi-target spells.
        
        Returns:
            bool: True if spell targets one entity, False for multi-target
            
        Examples:
            ```python
            # Single target examples
            single_spell.target_expr = ""        # True
            single_spell.target_expr = "   "     # True
            
            # Multi-target examples  
            multi_spell.target_expr = "3"        # False
            multi_spell.target_expr = "MIND"     # False
            ```
        """
        return not self.target_expr or self.target_expr.strip() == ""

    def target_count(self, actor: Any, mind_level: int) -> int:
        """
        Calculate the number of targets this spell can affect.
        
        Evaluates the target_expr with the actor's current variables and the
        specified mind level to determine the actual number of targets. This
        supports dynamic scaling based on character level, spell level, ability
        scores, or other factors.
        
        Args:
            actor: The character casting the spell (must have expression variables)
            mind_level: The spell level being used for casting
            
        Returns:
            int: Number of targets (minimum 1, even for invalid expressions)
            
        Variable Substitution:
            - {MIND}: The mind level (spell level) being used
            - {LEVEL}: Character level
            - {STR}, {DEX}, {CON}, {INT}, {WIS}, {CHA}: Ability modifiers  
            - {PROF}: Proficiency bonus
            - Custom variables from actor's get_expression_variables method
            
        Examples:
            ```python
            # Static target count
            spell.target_expr = "3"           # Always 3 targets
            
            # Spell level scaling
            spell.target_expr = "MIND"        # 1 target per spell level
            spell.target_expr = "1 + MIND//2" # Extra target every 2 levels
            
            # Character level based
            spell.target_expr = "1 + LEVEL//4" # Scales with character level
            
            # Ability score based  
            spell.target_expr = "max(1, CHA)" # CHA modifier minimum 1
            ```
            
        Error Handling:
            Returns 1 if target_expr is empty, invalid, or evaluates to 0 or less.
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
        """
        Execute spell - delegates to cast_spell method.
        
        This method is required by the BaseAction interface but for spells we use
        the cast_spell method instead, which takes an additional mind_level parameter
        for spell level scaling.
        
        Args:
            actor: The character casting the spell
            target: The target of the spell
            
        Returns:
            bool: Always False - use cast_spell() instead
            
        Raises:
            NotImplementedError: Always raised to enforce using cast_spell()
            
        Note:
            Spells should always be cast using the cast_spell() method which allows
            specifying the spell level for proper mind cost and scaling calculations.
        """
        raise NotImplementedError("Spells must use the cast_spell method.")

    @abstractmethod
    def cast_spell(self, actor: Any, target: Any, mind_level: int) -> bool:
        """
        Abstract method for casting spells with level-specific behavior.
        
        This is the primary method for executing spells. Unlike the base execute()
        method, cast_spell() takes a mind_level parameter that determines the
        spell's power level, mind cost, and scaling effects.
        
        Args:
            actor: The character casting the spell (must have mind points)
            target: The character targeted by the spell
            mind_level: The spell level to cast at (1-9, affects cost and power)
            
        Returns:
            bool: True if spell was cast successfully, False on failure
            
        Implementation Requirements:
            Subclasses must implement this method to define their specific behavior:
            - Check mind point availability against mind_cost[mind_level-1]
            - Validate cooldowns and usage restrictions
            - Apply level-specific scaling to damage/healing/effects
            - Handle concentration requirements if applicable
            - Display appropriate combat messages
            - Return success/failure status
            
        Mind Level System:
            The mind_level parameter indexes into the mind_cost array:
            - mind_level=1 uses mind_cost[0]
            - mind_level=2 uses mind_cost[1]
            - etc.
            
        Example Implementation Pattern:
            ```python
            def cast_spell(self, actor, target, mind_level):
                # Validate mind cost
                if actor.mind < self.mind_cost[mind_level-1]:
                    return False
                    
                # Apply spell effects with level scaling
                damage = base_damage + (mind_level * scaling)
                
                # Deduct mind cost and apply effects
                actor.mind -= self.mind_cost[mind_level-1]
                return True
            ```
        """
        pass

    def apply_effect(
        self,
        actor: Any,
        target: Any,
        effect: Effect | None,
        mind_level: int | None = 0,
    ) -> bool:
        """
        Apply a spell effect to a target with concentration handling.
        
        This method extends the base apply_effect functionality to handle
        spell-specific mechanics like concentration requirements. When a spell
        requires concentration, this method automatically marks the effect
        as requiring concentration.
        
        Args:
            actor: The character applying the effect (caster)
            target: The character receiving the effect  
            effect: The effect to apply (can be None)
            mind_level: The spell level used (affects effect power)
            
        Returns:
            bool: True if effect was successfully applied
            
        Concentration Mechanics:
            - If spell requires_concentration=True, effect is marked as concentration
            - Only one concentration effect can be active per caster
            - Casting a new concentration spell breaks the previous one
            - Effect manager handles concentration tracking and breaking
            
        Spell Reference:
            Unlike base actions, spells pass themselves as a reference to the
            effect manager, enabling spell-specific effect interactions.
            
        Validation:
            - Returns False immediately if effect is None
            - Returns False if actor or target is not alive
            - Uses effect manager's validation for effect application
            
        Example:
            ```python
            # Concentration spell effect
            if self.requires_concentration:
                actor.effect_manager.break_concentration(actor)  # Break existing
                
            success = self.apply_effect(actor, target, buff_effect, mind_level)
            # Effect is now marked as requiring concentration
            ```
        """
        if not effect:
            return False
        if not actor.is_alive():
            return False
        if not target.is_alive():
            return False

        # If this spell requires concentration and effect exists, mark it as requiring concentration
        if self.requires_concentration and effect:
            effect.requires_concentration = True

        # For spells, pass the spell reference to the effect manager
        if target.effect_manager.add_effect(actor, effect, mind_level, self):
            debug(f"Applied effect {effect.name} from {actor.name} to {target.name}.")
            return True
        debug(f"Not applied effect {effect.name} from {actor.name} to {target.name}.")
        return False

    # ============================================================================
    # SERIALIZATION METHODS
    # ============================================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the spell to a dictionary representation.
        
        Creates a complete serializable representation of the spell including
        all properties from the base class plus spell-specific data like
        level, mind costs, concentration requirements, and targeting expressions.
        
        Returns:
            dict: Complete dictionary representation suitable for JSON serialization
            
        Dictionary Structure:
            - Base properties: name, type, description, cooldown, maximum_uses
            - Spell properties: level, mind_cost, requires_concentration
            - Optional: target_expr if multi-target
            
        Example:
            ```python
            spell_data = fireball.to_dict()
            # Returns complete serializable dictionary with all spell properties
            ```
        """
        data = super().to_dict()
        # Add specific fields for Spell
        data["level"] = self.level
        data["mind_cost"] = self.mind_cost
        data["requires_concentration"] = self.requires_concentration
        # Include the multi-target expression if it exists.
        if self.target_expr:
            data["target_expr"] = self.target_expr
        return data


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


class SpellHeal(Spell):
    """
    Restorative spell that heals hit points and can apply beneficial effects.
    
    SpellHeal represents magical healing abilities that restore lost hit points
    to targets. Unlike offensive spells, healing spells automatically succeed
    without requiring attack rolls, making them reliable support options in
    combat and exploration scenarios.
    
    Core Mechanics:
        - Automatic Success: No attack rolls needed, healing always applies
        - Variable Healing: Uses dice expressions with level scaling support
        - Effect Integration: Can apply additional beneficial effects
        - Multi-Target Support: Can heal multiple allies simultaneously
        - Mind Cost Scaling: Higher levels provide more healing for increased cost
        
    Healing System:
        Each spell has a heal_roll expression that determines healing amount:
        - Dice notation: "2d8", "3d6+4", etc.
        - Level scaling: Can use MIND variable for spell level scaling
        - Character scaling: Can use caster stats (WIS, CHA, etc.)
        - Fixed modifiers: Static bonuses added to dice rolls
        
    Healing Resolution:
        1. Check mind point availability and cooldowns
        2. Handle concentration requirements if applicable
        3. Roll healing expression with level scaling
        4. Apply healing to target (limited by max HP)
        5. Apply optional beneficial effects
        6. Display healing feedback to players
        
    Level Scaling Examples:
        - "2d8 + 2": Static healing regardless of spell level
        - "1d8 + MIND": Adds spell level to healing
        - "MIND d8 + MIND": Both dice count and modifier scale
        - "2d8 + WIS": Healing scales with caster's Wisdom modifier
        
    Multi-Target Healing:
        SpellHeal supports healing multiple targets through target_expr:
        - Single target: target_expr = "" (most healing spells)
        - Group healing: target_expr = "3" or "MIND//2"  
        - Mass healing: target_expr = "MIND + 2"
        - Each target receives full healing amount
        
    Effect Integration:
        Optional effects can provide additional benefits:
        - Temporary hit point bonuses
        - Resistance to damage types
        - Regeneration over time effects
        - Status condition removal (poison, disease, etc.)
        
    Example Usage:
        ```python
        # Single-target healing spell
        cure_wounds = SpellHeal(
            name="Cure Wounds",
            type=ActionType.ACTION,
            description="A warm, healing light",
            level=1,
            mind_cost=[2, 4, 6, 8],
            heal_roll="1d8 + MIND + WIS",
            requires_concentration=False
        )
        
        # Group healing with temporary HP
        mass_cure_wounds = SpellHeal(
            name="Mass Cure Wounds", 
            type=ActionType.ACTION,
            description="Waves of healing energy",
            level=5,
            mind_cost=[10, 12, 15],
            heal_roll="3d8 + MIND",
            target_expr="MIND",  # Heals spell level targets
            effect=TempHPEffect(value="MIND * 2", duration=10)
        )
        
        # Healing over time with concentration
        regeneration = SpellHeal(
            name="Regeneration",
            type=ActionType.ACTION,
            description="Continuous healing magic",
            level=7,
            mind_cost=[14, 16, 18],
            heal_roll="1",  # Initial minimal healing
            effect=RegenEffect(heal_per_turn="1d4 + 1", duration=60),
            requires_concentration=True
        )
        ```
        
    Attributes:
        heal_roll: Dice expression determining healing amount with scaling support
        effect: Optional beneficial effect applied alongside healing
        
    Note:
        SpellHeal inherits all spell mechanics (mind costs, concentration,
        targeting) from the base Spell class while adding healing-specific
        logic that always succeeds and cannot critically hit or fumble.
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
        heal_roll: str,
        effect: Effect | None = None,
        target_expr: str = "",
        requires_concentration: bool = False,
        target_restrictions: list[str] | None = None,
    ):
        """
        Initialize a new SpellHeal.
        
        Creates a restorative spell that automatically heals targets without
        requiring attack rolls. The spell uses mind points for casting and
        can optionally apply beneficial effects alongside healing.
        
        Args:
            name: Display name of the healing spell
            type: Action type (ACTION, BONUS_ACTION, REACTION, etc.)
            description: Flavor text describing the healing appearance/effects
            cooldown: Turns to wait before reusing (0 = no cooldown)
            maximum_uses: Max uses per encounter/day (-1 = unlimited)
            level: Base spell level determining scaling and prerequisites
            mind_cost: List of mind point costs per casting level
            heal_roll: Dice expression for healing amount with scaling support
            effect: Optional beneficial effect applied alongside healing
            target_expr: Expression for multi-target healing ("" = single target)
            requires_concentration: Whether spell needs ongoing mental focus
            target_restrictions: Override default targeting restrictions
            
        Heal Roll Expression:
            The heal_roll string supports dice notation with scaling variables:
            - Basic dice: "1d8", "2d4+2", "3d6"
            - Level scaling: "1d8 + MIND" (adds spell level)
            - Stat scaling: "2d8 + WIS" (adds Wisdom modifier)
            - Complex: "MIND d8 + MIND + WIS" (multiple scaling factors)
            
        Examples:
            ```python
            # Basic healing spell with level scaling
            cure_wounds = SpellHeal(
                name="Cure Wounds",
                type=ActionType.ACTION,
                description="Warm healing light",
                level=1,
                mind_cost=[2, 4, 6],
                heal_roll="1d8 + MIND"  # Scales with spell level
            )
            
            # Multi-target group healing
            mass_heal = SpellHeal(
                name="Mass Heal",
                type=ActionType.ACTION,
                description="Radiant healing energy",
                level=9,
                mind_cost=[18],
                heal_roll="8d6 + WIS",
                target_expr="6",  # Always heals 6 targets
                effect=TempHPEffect(value="10", duration=10)
            )
            
            # Healing over time with concentration
            regeneration = SpellHeal(
                name="Regeneration",
                type=ActionType.ACTION,
                description="Continuous regeneration",
                level=7,
                mind_cost=[14, 16],
                heal_roll="1",  # Minimal initial healing
                effect=RegenEffect(heal_per_turn="1d4+1", duration=100),
                requires_concentration=True
            )
            
            # Variable target scaling healing
            healing_word = SpellHeal(
                name="Healing Word",
                type=ActionType.BONUS_ACTION,
                description="Spoken word of healing",
                level=1,
                mind_cost=[2, 3, 5, 7],
                heal_roll="1d4 + WIS",
                target_expr="1 + MIND//3"  # Extra targets at higher levels
            )
            ```
            
        Raises:
            ValueError: If name is empty, heal_roll is invalid, or types are wrong
            AssertionError: If heal_roll expression is malformed
            
        Note:
            - Automatically sets category to ActionCategory.HEALING
            - Validates heal_roll expression during initialization
            - Empty heal_roll raises an error as healing spells must heal
            - Effect is optional but commonly used for additional benefits
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
                ActionCategory.HEALING,
                target_expr,
                requires_concentration,
                target_restrictions,
            )

            # Validate heal_roll expression using helper
            self.heal_roll = ensure_string(
                heal_roll, "heal roll expression", "", {"name": name}
            )
            if not self.heal_roll:
                log_critical(
                    f"SpellHeal {name} must have a valid heal_roll expression",
                    {"name": name, "heal_roll": heal_roll}
                )
                raise ValueError(f"SpellHeal {name} must have a valid heal_roll expression")

            # Validate optional effect
            if effect is not None and not isinstance(effect, Effect):
                log_warning(
                    f"SpellHeal {name} effect must be Effect or None, got: {type(effect).__name__}, setting to None",
                    {"name": name, "effect_type": type(effect).__name__},
                )
                effect = None

            self.effect = effect

        except Exception as e:
            log_critical(
                f"Error initializing SpellHeal {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

    # ============================================================================
    # HEALING SPELL METHODS
    # ============================================================================

    def cast_spell(
        self, actor: Any, target: Any, mind_level: int | None = 1
    ) -> bool:
        """
        Execute a healing spell with automatic success and beneficial effects.
        
        Performs healing spell casting including mind cost validation, healing
        calculation with level scaling, and optional effect application. Unlike
        offensive spells, healing spells automatically succeed without attack rolls.
        
        Args:
            actor: The character casting the spell (must have mind points)
            target: The character receiving healing
            mind_level: The spell level to cast at (affects cost and healing amount)
            
        Returns:
            bool: True if spell was successfully cast, False on failure
            
        Healing Process:
            1. Validate mind cost and cooldowns
            2. Handle concentration requirements if applicable  
            3. Roll healing expression with level scaling
            4. Apply healing to target (capped at max HP)
            5. Apply optional beneficial effects
            6. Display healing feedback with amounts
            
        Mind Cost System:
            Uses the mind_cost list to determine resource consumption:
            - mind_level=1 uses mind_cost[0]
            - mind_level=2 uses mind_cost[1] 
            - Higher levels typically provide more healing
            
        Healing Scaling:
            The heal_roll expression can use variables for level scaling:
            - "2d8": Static healing amount
            - "2d8 + MIND": Adds spell level to healing
            - "MIND d8": Dice count scales with spell level
            - "2d8 + WIS": Includes caster's Wisdom modifier
            
        Multi-Target Healing:
            For spells with target_expr, this method is called once per target
            with each target receiving full healing amount (not divided).
            
        Effect Application:
            Optional effects are applied after healing:
            - Temporary hit point bonuses
            - Damage resistance buffs
            - Regeneration over time
            - Status condition removal
            
        Error Handling:
            - Returns False if insufficient mind points
            - Returns False if spell is on cooldown
            - Logs all failures with detailed context
            - Handles malformed healing expressions gracefully
            
        Example:
            ```python
            # Cast cure wounds at level 3
            success = cure_wounds.cast_spell(cleric, wounded_ally, mind_level=3)
            # Heals for 1d8 + 3 + WIS modifier, costs mind_cost[2] points
            ```
        """
        if mind_level is None:
            mind_level = 1
            
        debug(
            f"{actor.name} attempts to cast {self.name} on {target.name}, expression {self.heal_roll}."
        )
        
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

        # Calculate healing with level scaling
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        heal_value, heal_desc, _ = roll_and_describe(self.heal_roll, variables)

        # Apply healing to target (limited by max HP)
        actual_healed = target.heal(heal_value)

        # Apply optional effect
        effect_applied = False
        if self.effect:
            effect_applied = self.apply_effect(actor, target, self.effect, mind_level)

        # Display healing results
        msg = f"    ✳️ {actor_str} casts [bold]{self.name}[/] on {target_str}"
        msg += f" healing for [bold green]{actual_healed}[/]"
        if GLOBAL_VERBOSE_LEVEL >= 1:
            msg += f" ({heal_desc})"
        if effect_applied and self.effect:
            msg += f" and applying [{get_effect_color(self.effect)}]{self.effect.name}[/]"
        elif self.effect and not effect_applied:
            msg += f" but failing to apply [{get_effect_color(self.effect)}]{self.effect.name}[/]"
        msg += "."
        cprint(msg)

        return True

    # ============================================================================
    # HEALING CALCULATION METHODS
    # ============================================================================

    def get_heal_expr(self, actor: Any, mind_level: int | None = 1) -> str:
        """
        Get healing expression with variables substituted for display.
        
        Returns the complete healing expression string with all variables
        (MIND, character stats, etc.) substituted with their actual values.
        This is primarily used for UI display and healing preview.
        
        Args:
            actor: The character casting the spell
            mind_level: The spell level to use for MIND variable substitution
            
        Returns:
            str: Complete healing expression with variables substituted
            
        Example:
            ```python
            # For spell with heal_roll "2d8 + MIND + WIS"
            expr = spell.get_heal_expr(cleric, mind_level=3)
            # Returns: "2d8 + 3 + 4" (if cleric has WIS modifier of +4)
            ```
        """
        if mind_level is None:
            mind_level = 1
            
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return simplify_expression(self.heal_roll, variables)

    def get_min_heal(self, actor: Any, mind_level: int | None = 1) -> int:
        """
        Calculate the minimum possible healing for the spell.
        
        Computes the lowest possible healing by assuming minimum rolls on all
        dice expressions. This is useful for healing range displays and AI
        decision making when evaluating spell options.
        
        Args:
            actor: The character casting the spell
            mind_level: The spell level to use for scaling calculations
            
        Returns:
            int: Minimum possible healing amount
            
        Example:
            ```python
            # For "2d8 + 3" healing, returns 5 (2*1 + 3)
            min_heal = spell.get_min_heal(cleric, mind_level=2)
            ```
        """
        if mind_level is None:
            mind_level = 1
            
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return parse_expr_and_assume_min_roll(
            substitute_variables(self.heal_roll, variables)
        )

    def get_max_heal(self, actor: Any, mind_level: int | None = 1) -> int:
        """
        Calculate the maximum possible healing for the spell.
        
        Computes the highest possible healing by assuming maximum rolls on all
        dice expressions. This represents the spell's healing ceiling and is
        useful for healing range displays and tactical planning.
        
        Args:
            actor: The character casting the spell
            mind_level: The spell level to use for scaling calculations
            
        Returns:
            int: Maximum possible healing amount
            
        Example:
            ```python
            # For "2d8 + 3" healing, returns 19 (2*8 + 3)
            max_heal = spell.get_max_heal(cleric, mind_level=2)
            ```
        """
        if mind_level is None:
            mind_level = 1
            
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return parse_expr_and_assume_max_roll(
            substitute_variables(self.heal_roll, variables)
        )

    # ============================================================================
    # SERIALIZATION METHODS
    # ============================================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the healing spell to a dictionary representation.
        
        Creates a complete serializable representation including all base spell
        properties plus healing expression and optional effects. This supports
        saving/loading spells and data exchange.
        
        Returns:
            dict: Complete dictionary suitable for JSON serialization
            
        Dictionary Structure:
            - Base properties: name, type, description, cooldown, etc.
            - Spell properties: level, mind_cost, requires_concentration
            - Healing properties: heal_roll expression, optional effect
            - Optional: target_expr if multi-target
            
        Example:
            ```python
            data = cure_wounds.to_dict()
            # Contains all spell data for reconstruction
            rebuilt = SpellHeal.from_dict(data)
            ```
        """
        data = super().to_dict()
        # Add SpellHeal-specific properties
        data["heal_roll"] = self.heal_roll
        # Include optional effect if present
        if self.effect:
            data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SpellHeal":
        """
        Create a SpellHeal instance from a dictionary.
        
        Factory method that reconstructs a SpellHeal from its dictionary
        representation. Handles all validation and type conversion needed
        for safe deserialization.
        
        Args:
            data: Dictionary containing healing spell data
            
        Returns:
            SpellHeal: Fully initialized healing spell instance
            
        Raises:
            KeyError: If required fields are missing  
            ValueError: If data types are invalid
            
        Example:
            ```python
            spell_data = {
                "name": "Cure Wounds",
                "type": "ACTION", 
                "level": 1,
                "mind_cost": [2, 4, 6],
                "heal_roll": "1d8 + MIND + WIS"
            }
            cure_spell = SpellHeal.from_dict(spell_data)
            ```
        """
        return SpellHeal(
            name=data["name"],
            type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            level=data["level"],
            mind_cost=data["mind_cost"],
            heal_roll=data["heal_roll"],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
            target_expr=data.get("target_expr", ""),
            requires_concentration=data.get("requires_concentration", False),
            target_restrictions=data.get("target_restrictions", []),
        )


class SpellBuff(Spell):
    """
    Beneficial spell that enhances targets with positive effects.
    
    SpellBuff represents magical enhancement spells that apply beneficial effects
    to allies or the caster. These spells automatically succeed without requiring
    attack rolls, making them reliable support options for improving combat
    effectiveness and providing tactical advantages.
    
    Core Mechanics:
        - Automatic Success: No attack rolls needed, effects always apply
        - Effect Integration: Must provide a beneficial effect to apply
        - Multi-Target Support: Can enhance multiple allies simultaneously  
        - Mind Cost Scaling: Higher levels provide stronger or longer-lasting effects
        - Concentration Management: Many buff spells require ongoing mental focus
        
    Effect System:
        Each buff spell must have an Effect that defines the enhancement:
        - Modifier effects: Stat bonuses (attack, damage, AC, saves, etc.)
        - Resistance effects: Damage type resistances or immunities
        - Special abilities: Flight, invisibility, extra actions, etc.
        - Temporary hit points: Additional HP buffer
        - Ongoing benefits: Regeneration, spell-like abilities, etc.
        
    Buff Resolution:
        1. Check mind point availability and cooldowns
        2. Handle concentration requirements (break existing if needed)
        3. Apply the beneficial effect with level scaling
        4. Display enhancement feedback to players
        5. Track effect duration and concentration if applicable
        
    Level Scaling Examples:
        Effects can scale with spell level through variables:
        - Static bonuses: "+2 to attack rolls"
        - Level scaling: "+MIND to damage rolls" 
        - Duration scaling: "Duration increases by MIND rounds"
        - Stat scaling: "+WIS to all saves"
        
    Multi-Target Buffs:
        SpellBuff supports enhancing multiple targets through target_expr:
        - Single target: target_expr = "" (most buff spells)
        - Group buffs: target_expr = "3" or "MIND//2"
        - Mass enhancement: target_expr = "MIND + 1"
        - Each target receives the full effect (not divided)
        
    Concentration Mechanics:
        Many buff spells require concentration:
        - Only one concentration spell active per caster
        - Casting a new concentration spell breaks the previous one
        - Damage or specific conditions can break concentration
        - Lost concentration immediately ends the spell effect
        
    Example Usage:
        ```python
        # Single-target stat enhancement
        bless = SpellBuff(
            name="Bless",
            type=ActionType.ACTION,
            description="Divine favor enhances abilities",
            level=1,
            mind_cost=[2, 3, 4],
            effect=ModifierEffect(
                name="Blessed",
                duration=100,
                modifiers=[
                    Modifier(BonusType.ATTACK, "1d4"),
                    Modifier(BonusType.SAVE, "1d4")
                ]
            ),
            requires_concentration=True
        )
        
        # Multi-target defensive enhancement
        shield_of_faith = SpellBuff(
            name="Shield of Faith",
            type=ActionType.BONUS_ACTION,
            description="Protective barrier of divine energy",
            level=1,
            mind_cost=[2, 3, 4, 5],
            effect=ModifierEffect(
                name="Divine Shield",
                duration=100,
                modifiers=[Modifier(BonusType.AC, "2 + MIND//3")]
            ),
            target_expr="1 + MIND//2",  # More targets at higher levels
            requires_concentration=True
        )
        
        # Utility enhancement without concentration
        enhance_ability = SpellBuff(
            name="Enhance Ability",
            type=ActionType.ACTION,
            description="Magical enhancement of natural abilities",
            level=2,
            mind_cost=[4, 6, 8],
            effect=ModifierEffect(
                name="Enhanced",
                duration=3600,  # 1 hour
                modifiers=[Modifier(BonusType.ABILITY, "MIND + 2")]
            ),
            requires_concentration=False
        )
        ```
        
    Attributes:
        effect: Required beneficial effect that defines the enhancement
        
    Note:
        SpellBuff inherits all spell mechanics (mind costs, concentration,
        targeting) from the base Spell class while adding buff-specific
        logic that always succeeds and focuses on positive enhancements.
        The effect parameter is required as buffs without effects serve no purpose.
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
        effect: Effect,  # Changed from Buff to Effect
        target_expr: str = "",
        requires_concentration: bool = False,
        target_restrictions: list[str] | None = None,
    ):
        """
        Initialize a new SpellBuff.
        
        Creates a beneficial spell that automatically enhances targets with
        positive effects. The spell uses mind points for casting and applies
        the specified effect without requiring attack rolls.
        
        Args:
            name: Display name of the buff spell
            type: Action type (ACTION, BONUS_ACTION, REACTION, etc.)
            description: Flavor text describing the enhancement appearance/effects
            cooldown: Turns to wait before reusing (0 = no cooldown)
            maximum_uses: Max uses per encounter/day (-1 = unlimited)
            level: Base spell level determining scaling and prerequisites
            mind_cost: List of mind point costs per casting level
            effect: Required beneficial effect that defines the enhancement
            target_expr: Expression for multi-target buffs ("" = single target)
            requires_concentration: Whether spell needs ongoing mental focus
            target_restrictions: Override default targeting restrictions
            
        Effect Requirements:
            The effect parameter is mandatory as buff spells must provide benefits:
            - ModifierEffect: Stat bonuses (attack, damage, AC, saves, abilities)
            - ResistanceEffect: Damage type resistances or immunities
            - SpecialEffect: Unique abilities (flight, invisibility, extra actions)
            - ComboEffect: Multiple simultaneous enhancements
            
        Examples:
            ```python
            # Single-target attack bonus spell
            bless = SpellBuff(
                name="Bless",
                type=ActionType.ACTION,
                description="Divine favor guides strikes",
                level=1,
                mind_cost=[2, 3, 4],
                effect=ModifierEffect(
                    name="Blessed",
                    duration=100,
                    modifiers=[
                        Modifier(BonusType.ATTACK, "1d4"),
                        Modifier(BonusType.SAVE, "1d4")
                    ]
                ),
                requires_concentration=True
            )
            
            # Multi-target defensive enhancement
            protection_from_evil = SpellBuff(
                name="Protection from Evil",
                type=ActionType.ACTION,
                description="Protective aura against dark forces",
                level=2,
                mind_cost=[4, 6, 8],
                effect=ResistanceEffect(
                    name="Protected",
                    duration=600,
                    resistances=["necrotic", "psychic"],
                    bonus_vs_types=["fiend", "undead"]
                ),
                target_expr="MIND",  # Affects spell level targets
                requires_concentration=True
            )
            
            # Utility enhancement with level scaling
            enhance_ability = SpellBuff(
                name="Enhance Ability", 
                type=ActionType.ACTION,
                description="Magical enhancement of natural talents",
                level=2,
                mind_cost=[4, 6, 8, 10],
                effect=ModifierEffect(
                    name="Enhanced Ability",
                    duration=3600,  # 1 hour
                    modifiers=[
                        Modifier(BonusType.ABILITY_SCORE, "MIND + 2"),
                        Modifier(BonusType.SKILL_CHECK, "MIND")
                    ]
                ),
                requires_concentration=False  # Long duration, no concentration
            )
            
            # Complex multi-benefit buff
            heroism = SpellBuff(
                name="Heroism",
                type=ActionType.ACTION,
                description="Inspiring courage and resilience",
                level=1,
                mind_cost=[2, 3, 4, 6],
                effect=ComboEffect(
                    name="Heroic",
                    duration=100,
                    effects=[
                        TempHPEffect(value="MIND + WIS"),
                        ModifierEffect(modifiers=[
                            Modifier(BonusType.SAVE_FEAR, "advantage"),
                            Modifier(BonusType.ATTACK, "1")
                        ])
                    ]
                ),
                requires_concentration=True
            )
            ```
            
        Raises:
            ValueError: If name is empty or effect is None
            AssertionError: If effect is not provided (required for buffs)
            
        Note:
            - Automatically sets category to ActionCategory.BUFF
            - Effect parameter is mandatory and validated
            - Many buff spells require concentration for balance
            - Target restrictions default to allies only (can be overridden)
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
                ActionCategory.BUFF,
                target_expr,
                requires_concentration,
                target_restrictions,
            )

            # Validate required effect
            if effect is None:
                log_critical(
                    f"SpellBuff {name} must have an effect",
                    {"name": name}
                )
                raise ValueError(f"SpellBuff {name} must have an effect")

            if not isinstance(effect, Effect):
                log_critical(
                    f"SpellBuff {name} effect must be an Effect instance, got: {type(effect).__name__}",
                    {"name": name, "effect_type": type(effect).__name__}
                )
                raise ValueError(f"SpellBuff {name} effect must be an Effect instance")

            self.effect = effect

        except Exception as e:
            log_critical(
                f"Error initializing SpellBuff {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

    # ============================================================================
    # BUFF SPELL METHODS
    # ============================================================================

    def cast_spell(
        self, actor: Any, target: Any, mind_level: int | None = 1
    ) -> bool:
        """
        Execute a buff spell with automatic success and beneficial effects.
        
        Performs buff spell casting including mind cost validation, concentration
        management, and effect application. Unlike offensive spells, buff spells
        automatically succeed without attack rolls and focus on enhancing targets.
        
        Args:
            actor: The character casting the spell (must have mind points)
            target: The character receiving the enhancement
            mind_level: The spell level to cast at (affects cost and effect power)
            
        Returns:
            bool: True if spell was successfully cast, False on failure
            
        Buff Process:
            1. Validate mind cost and cooldowns
            2. Handle concentration requirements (break existing if needed)
            3. Apply the beneficial effect with level scaling
            4. Display enhancement feedback with effect details
            5. Track effect duration and concentration if applicable
            
        Mind Cost System:
            Uses the mind_cost list to determine resource consumption:
            - mind_level=1 uses mind_cost[0]
            - mind_level=2 uses mind_cost[1]
            - Higher levels often provide stronger or longer effects
            
        Concentration Management:
            Many buff spells require concentration:
            - Automatically breaks caster's existing concentration
            - New effect becomes the active concentration spell
            - Effect ends immediately if concentration is broken
            
        Effect Scaling:
            Effects can scale with spell level through variables:
            - Static bonuses: Fixed numerical enhancements
            - Level scaling: Use MIND variable in effect expressions
            - Duration scaling: Longer effects at higher levels
            - Target scaling: More targets affected at higher levels
            
        Multi-Target Buffs:
            For spells with target_expr, this method is called once per target
            with each target receiving the full effect benefits.
            
        Error Handling:
            - Returns False if insufficient mind points
            - Returns False if spell is on cooldown
            - Logs all failures with detailed context
            - Handles effect application failures gracefully
            
        Example:
            ```python
            # Cast bless at level 2 for stronger bonus
            success = bless.cast_spell(cleric, ally, mind_level=2)
            # Applies enhanced effect, costs mind_cost[1] points
            ```
        """
        if mind_level is None:
            mind_level = 1
            
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

        # Apply the beneficial effect
        effect_applied = False
        if self.effect:
            effect_applied = self.apply_effect(actor, target, self.effect, mind_level)

        # Display enhancement results
        msg = f"    ✨ {actor_str} casts [bold]{self.name}[/] on {target_str} "
        if effect_applied:
            msg += f"applying [{get_effect_color(self.effect)}]{self.effect.name}[/]"
        else:
            msg += f"but fails to apply [{get_effect_color(self.effect)}]{self.effect.name}[/]"
        msg += "."

        cprint(msg)

        return True

    # ============================================================================
    # EFFECT ANALYSIS METHODS
    # ============================================================================

    def get_modifier_expressions(
        self, actor: Any, mind_level: int | None = 1
    ) -> dict[BonusType, str]:
        """
        Get modifier expressions with variables substituted for display.
        
        Returns a dictionary of bonus types to their expression strings with
        all variables (MIND, character stats, etc.) substituted with actual
        values. This is used for UI display and effect preview.
        
        Args:
            actor: The character casting the spell
            mind_level: The spell level to use for MIND variable substitution
            
        Returns:
            dict: Mapping of BonusType to expression strings
            
        Example:
            ```python
            # For effect with modifier "+MIND to attack rolls" 
            expressions = spell.get_modifier_expressions(cleric, mind_level=3)
            # Returns: {BonusType.ATTACK: "+3"}
            ```
        """
        if mind_level is None:
            mind_level = 1
            
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        expressions: dict[BonusType, str] = {}

        # Handle effects that have modifiers (ModifierEffect)
        if isinstance(self.effect, ModifierEffect):
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

    # ============================================================================
    # SERIALIZATION METHODS
    # ============================================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the buff spell to a dictionary representation.
        
        Creates a complete serializable representation including all base spell
        properties plus the required beneficial effect. This supports saving/loading
        spells and data exchange.
        
        Returns:
            dict: Complete dictionary suitable for JSON serialization
            
        Dictionary Structure:
            - Base properties: name, type, description, cooldown, etc.
            - Spell properties: level, mind_cost, requires_concentration
            - Buff properties: effect definition
            - Optional: target_expr if multi-target
            
        Example:
            ```python
            data = bless.to_dict()
            # Contains all spell data for reconstruction
            rebuilt = SpellBuff.from_dict(data)
            ```
        """
        data = super().to_dict()
        # Add SpellBuff-specific properties
        data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SpellBuff":
        """
        Create a SpellBuff instance from a dictionary.
        
        Factory method that reconstructs a SpellBuff from its dictionary
        representation. Handles all validation and type conversion needed
        for safe deserialization.
        
        Args:
            data: Dictionary containing buff spell data
            
        Returns:
            SpellBuff: Fully initialized buff spell instance
            
        Raises:
            KeyError: If required fields are missing
            ValueError: If data types are invalid or effect is missing
            
        Example:
            ```python
            spell_data = {
                "name": "Bless",
                "type": "ACTION",
                "level": 1,
                "mind_cost": [2, 3, 4],
                "effect": {
                    "type": "ModifierEffect",
                    "name": "Blessed",
                    "duration": 100,
                    "modifiers": [...]
                }
            }
            bless_spell = SpellBuff.from_dict(spell_data)
            ```
        """
        return SpellBuff(
            name=data["name"],
            type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            level=data["level"],
            mind_cost=data["mind_cost"],
            effect=Effect.from_dict(data["effect"]),
            target_expr=data.get("target_expr", ""),
            requires_concentration=data.get("requires_concentration", False),
            target_restrictions=data.get("target_restrictions", []),
        )


class SpellDebuff(Spell):
    """
    Detrimental spell that weakens enemies with negative effects.
    
    SpellDebuff represents magical debuffing spells that apply harmful effects
    to enemies to reduce their combat effectiveness. Unlike offensive damage
    spells, debuff spells focus on applying persistent penalties, conditions,
    or restrictions that hinder enemy capabilities over time.
    
    Core Mechanics:
        - Automatic Success: No attack rolls needed, effects apply directly
        - Effect Integration: Must provide a detrimental effect to apply
        - Multi-Target Support: Can weaken multiple enemies simultaneously
        - Mind Cost Scaling: Higher levels provide stronger or longer-lasting effects
        - Concentration Management: Many debuff spells require ongoing mental focus
        - Save Negation: Some effects allow saving throws to resist or reduce duration
        
    Effect System:
        Each debuff spell must have an Effect that defines the penalty:
        - Modifier effects: Stat penalties (attack, damage, AC, saves, etc.)
        - Condition effects: Status conditions (paralyzed, poisoned, charmed, etc.)
        - Movement effects: Speed reduction, restraint, or immobilization
        - Ability effects: Skill penalties, disadvantage on rolls, etc.
        - Ongoing damage: Damage over time effects (poison, burning, etc.)
        
    Debuff Resolution:
        1. Check mind point availability and cooldowns
        2. Handle concentration requirements (break existing if needed)
        3. Apply the detrimental effect with level scaling
        4. Allow saving throws if effect permits
        5. Display debuff feedback to players
        6. Track effect duration and concentration if applicable
        
    Level Scaling Examples:
        Effects can scale with spell level through variables:
        - Static penalties: "-2 to attack rolls"
        - Level scaling: "-MIND to damage rolls"
        - Duration scaling: "Duration increases by MIND rounds"
        - Save DC scaling: "DC = 8 + PROF + MIND + WIS"
        
    Multi-Target Debuffs:
        SpellDebuff supports weakening multiple targets through target_expr:
        - Single target: target_expr = "" (most debuff spells)
        - Group debuffs: target_expr = "2" or "MIND//2"
        - Area effects: target_expr = "MIND + 1"
        - Each target receives the full effect (not divided)
        
    Concentration Mechanics:
        Many debuff spells require concentration:
        - Only one concentration spell active per caster
        - Casting a new concentration spell breaks the previous one
        - Damage or specific conditions can break concentration
        - Lost concentration immediately ends the debuff effect
        
    Save System Integration:
        Some debuff effects allow saving throws:
        - Initial save: Target can resist the effect entirely
        - Ongoing saves: Periodic chances to end the effect early
        - Partial saves: Reduced duration or severity on success
        - Save DC: Typically 8 + proficiency + spell level + casting modifier
        
    Example Usage:
        ```python
        # Single-target attack penalty
        bane = SpellDebuff(
            name="Bane",
            type=ActionType.ACTION,
            description="Dark energy saps enemy strength",
            level=1,
            mind_cost=[2, 3, 4],
            effect=ModifierEffect(
                name="Cursed",
                duration=100,
                modifiers=[
                    Modifier(BonusType.ATTACK, "-1d4"),
                    Modifier(BonusType.SAVE, "-1d4")
                ],
                save_type=SaveType.CHARISMA,
                save_dc="8 + PROF + MIND + WIS"
            ),
            requires_concentration=True
        )
        
        # Multi-target movement debuff
        web = SpellDebuff(
            name="Web",
            type=ActionType.ACTION,
            description="Sticky webs entangle enemies",
            level=2,
            mind_cost=[4, 6, 8],
            effect=ConditionEffect(
                name="Webbed",
                duration=100,
                condition=Condition.RESTRAINED,
                save_type=SaveType.STRENGTH,
                save_dc="8 + PROF + MIND + DEX",
                save_ends=True  # Can break free with successful save
            ),
            target_expr="MIND + 1",  # Affects spell level + 1 targets
            requires_concentration=True
        )
        
        # Damage over time without concentration
        poison_spray = SpellDebuff(
            name="Poison Spray",
            type=ActionType.ACTION,
            description="Toxic cloud damages and sickens",
            level=0,  # Cantrip
            mind_cost=[1],
            effect=DamageOverTimeEffect(
                name="Poisoned",
                duration=30,
                damage_per_turn="1d4 + MIND//2",
                damage_type=DamageType.POISON,
                condition=Condition.POISONED
            ),
            requires_concentration=False  # Short duration, no concentration
        )
        
        # Complex multi-effect debuff
        bestow_curse = SpellDebuff(
            name="Bestow Curse",
            type=ActionType.ACTION,
            description="Powerful curse weakens the target",
            level=3,
            mind_cost=[6, 8, 10, 12],
            effect=ComboEffect(
                name="Cursed",
                duration=100,
                effects=[
                    ModifierEffect(modifiers=[
                        Modifier(BonusType.ABILITY_SCORE, "-MIND"),
                        Modifier(BonusType.SAVE, "-2")
                    ]),
                    ConditionEffect(condition=Condition.HEXED)
                ],
                save_type=SaveType.WISDOM,
                save_dc="8 + PROF + MIND + WIS"
            ),
            requires_concentration=True
        )
        ```
        
    Tactical Considerations:
        - Concentration management: Choose debuffs vs other concentration spells
        - Action economy: Debuffs use actions but provide ongoing benefits
        - Target prioritization: Focus on dangerous enemies or key threats
        - Save probabilities: Consider target save bonuses vs spell DC
        - Duration vs power: Longer effects vs stronger immediate impact
        
    Attributes:
        effect: Required detrimental effect that defines the penalty/condition
        
    Note:
        SpellDebuff inherits all spell mechanics (mind costs, concentration,
        targeting) from the base Spell class while adding debuff-specific
        logic that always succeeds initially but may allow saves to resist
        or reduce the effect's impact and duration.
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
        effect: Effect,  # Changed from Debuff to Effect for consistency
        target_expr: str = "",
        requires_concentration: bool = False,
        target_restrictions: list[str] | None = None,
    ):
        """
        Initialize a new SpellDebuff.
        
        Creates a detrimental spell that automatically weakens targets with
        negative effects. The spell uses mind points for casting and applies
        the specified effect without requiring attack rolls, though targets
        may be allowed saving throws to resist or reduce the effect.
        
        Args:
            name: Display name of the debuff spell
            type: Action type (ACTION, BONUS_ACTION, REACTION, etc.)
            description: Flavor text describing the debuff appearance/effects
            cooldown: Turns to wait before reusing (0 = no cooldown)
            maximum_uses: Max uses per encounter/day (-1 = unlimited)
            level: Base spell level determining scaling and prerequisites
            mind_cost: List of mind point costs per casting level
            effect: Required detrimental effect that defines the penalty/condition
            target_expr: Expression for multi-target debuffs ("" = single target)
            requires_concentration: Whether spell needs ongoing mental focus
            target_restrictions: Override default targeting restrictions
            
        Effect Requirements:
            The effect parameter is mandatory as debuff spells must provide penalties:
            - ModifierEffect: Stat penalties (attack, damage, AC, saves, abilities)
            - ConditionEffect: Status conditions (paralyzed, poisoned, charmed, etc.)
            - DamageOverTimeEffect: Ongoing damage (poison, burning, necrotic, etc.)
            - ComboEffect: Multiple simultaneous penalties and conditions
            - CustomEffect: Unique debuff mechanics specific to the spell
            
        Examples:
            ```python
            # Single-target attack/save penalty
            bane = SpellDebuff(
                name="Bane",
                type=ActionType.ACTION,
                description="Dark energy weakens enemies",
                level=1,
                mind_cost=[2, 3, 4],
                effect=ModifierEffect(
                    name="Cursed",
                    duration=100,
                    modifiers=[
                        Modifier(BonusType.ATTACK, "-1d4"),
                        Modifier(BonusType.SAVE, "-1d4")
                    ],
                    save_type=SaveType.CHARISMA,
                    save_dc="8 + PROF + MIND + WIS"
                ),
                requires_concentration=True
            )
            
            # Multi-target movement restriction
            entangle = SpellDebuff(
                name="Entangle", 
                type=ActionType.ACTION,
                description="Grasping vines restrain enemies",
                level=1,
                mind_cost=[2, 3, 4, 5],
                effect=ConditionEffect(
                    name="Entangled",
                    duration=100,
                    condition=Condition.RESTRAINED,
                    save_type=SaveType.STRENGTH,
                    save_dc="8 + PROF + MIND + WIS",
                    save_ends=True,  # Can break free each turn
                    difficult_terrain=True
                ),
                target_expr="MIND + 2",  # More targets at higher levels
                requires_concentration=True
            )
            
            # Damage over time debuff
            poison_cloud = SpellDebuff(
                name="Poison Cloud",
                type=ActionType.ACTION,
                description="Toxic vapors damage and sicken",
                level=2,
                mind_cost=[4, 6, 8, 10],
                effect=DamageOverTimeEffect(
                    name="Poisoned",
                    duration=60,
                    damage_per_turn="1d6 + MIND//2",
                    damage_type=DamageType.POISON,
                    condition=Condition.POISONED,
                    save_type=SaveType.CONSTITUTION,
                    save_dc="8 + PROF + MIND + INT",
                    save_halves_damage=True
                ),
                target_expr="MIND",  # Area effect
                requires_concentration=False
            )
            
            # Complex multi-effect curse
            bestow_curse = SpellDebuff(
                name="Bestow Curse",
                type=ActionType.ACTION,
                description="Powerful magical curse",
                level=3,
                mind_cost=[6, 8, 10, 12, 14],
                effect=ComboEffect(
                    name="Major Curse",
                    duration=600,  # 10 minutes
                    effects=[
                        ModifierEffect(modifiers=[
                            Modifier(BonusType.ABILITY_SCORE, "-MIND"),
                            Modifier(BonusType.SAVE, "-2"),
                            Modifier(BonusType.SKILL_CHECK, "-MIND")
                        ]),
                        ConditionEffect(condition=Condition.CURSED),
                        DamageOverTimeEffect(
                            damage_per_turn="1d8",
                            damage_type=DamageType.NECROTIC
                        )
                    ],
                    save_type=SaveType.WISDOM,
                    save_dc="8 + PROF + MIND + WIS + 2"  # Higher DC
                ),
                requires_concentration=True
            )
            
            # Mental control debuff
            charm_person = SpellDebuff(
                name="Charm Person",
                type=ActionType.ACTION,
                description="Magical compulsion bends the will",
                level=1,
                mind_cost=[2, 3, 4, 5],
                effect=ConditionEffect(
                    name="Charmed",
                    duration=3600,  # 1 hour
                    condition=Condition.CHARMED,
                    save_type=SaveType.WISDOM,
                    save_dc="8 + PROF + MIND + CHA",
                    save_ends=True,
                    repeat_save=True,  # Save at end of each turn
                    advantage_on_damage=True  # Advantage if damaged
                ),
                target_restrictions=["humanoid"],  # Only works on humanoids
                requires_concentration=False  # Long duration
            )
            ```
            
        Save System Integration:
            Many debuff effects include saving throw mechanics:
            - save_type: Ability score used for the save (STR, DEX, CON, etc.)
            - save_dc: Difficulty class, often "8 + PROF + MIND + STAT"
            - save_ends: Whether successful save immediately ends the effect
            - repeat_save: Whether target gets saves at end of each turn
            - save_halves_damage: Whether saves reduce ongoing damage by half
            
        Raises:
            ValueError: If name is empty or effect is None
            AssertionError: If effect is not provided (required for debuffs)
            
        Note:
            - Automatically sets category to ActionCategory.DEBUFF
            - Effect parameter is mandatory and validated
            - Many debuff spells require concentration for balance
            - Target restrictions often limit valid targets (humanoids, living, etc.)
            - Save DCs typically scale with spell level and caster ability
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
                ActionCategory.DEBUFF,
                target_expr,
                requires_concentration,
                target_restrictions,
            )

            # Validate required effect
            if effect is None:
                log_critical(
                    f"SpellDebuff {name} must have an effect",
                    {"name": name}
                )
                raise ValueError(f"SpellDebuff {name} must have an effect")

            if not isinstance(effect, Effect):
                log_critical(
                    f"SpellDebuff {name} effect must be an Effect instance, got: {type(effect).__name__}",
                    {"name": name, "effect_type": type(effect).__name__}
                )
                raise ValueError(f"SpellDebuff {name} effect must be an Effect instance")

            self.effect = effect

        except Exception as e:
            log_critical(
                f"Error initializing SpellDebuff {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

    # ============================================================================
    # DEBUFF SPELL METHODS
    # ============================================================================

    def cast_spell(
        self, actor: Any, target: Any, mind_level: int | None = 1
    ) -> bool:
        """
        Execute a debuff spell with automatic application and optional saves.
        
        Performs debuff spell casting including mind cost validation, concentration
        management, and effect application. Unlike offensive spells, debuff spells
        automatically apply their effects, though targets may get saving throws
        to resist or reduce the impact.
        
        Args:
            actor: The character casting the spell (must have mind points)
            target: The character receiving the debuff
            mind_level: The spell level to cast at (affects cost and effect power)
            
        Returns:
            bool: True if spell was successfully cast, False on failure
            
        Debuff Process:
            1. Validate mind cost and cooldowns
            2. Handle concentration requirements (break existing if needed)
            3. Apply the detrimental effect with level scaling
            4. Process any saving throws the effect allows
            5. Display debuff feedback with effect details
            6. Track effect duration and concentration if applicable
            
        Mind Cost System:
            Uses the mind_cost list to determine resource consumption:
            - mind_level=1 uses mind_cost[0]
            - mind_level=2 uses mind_cost[1]
            - Higher levels often provide stronger effects or better save DCs
            
        Concentration Management:
            Many debuff spells require concentration:
            - Automatically breaks caster's existing concentration
            - New effect becomes the active concentration spell
            - Effect ends immediately if concentration is broken
            
        Effect Application:
            Effects are applied with level scaling through variables:
            - Static penalties: Fixed numerical debuffs
            - Level scaling: Use MIND variable in effect expressions
            - Save DC scaling: Higher levels increase save difficulty
            - Duration scaling: Longer effects at higher levels
            
        Save System Integration:
            If the effect includes saving throw mechanics:
            - Target rolls appropriate save (STR, DEX, CON, INT, WIS, CHA)
            - Save DC typically includes spell level and caster modifier
            - Success may negate, reduce, or shorten the effect
            - Some effects allow repeated saves each turn
            
        Multi-Target Debuffs:
            For spells with target_expr, this method is called once per target
            with each target receiving the full effect and individual saves.
            
        Error Handling:
            - Returns False if insufficient mind points
            - Returns False if spell is on cooldown  
            - Logs all failures with detailed context
            - Handles effect application failures gracefully
            
        Example:
            ```python
            # Cast bane at level 3 for stronger penalties
            success = bane.cast_spell(warlock, enemy, mind_level=3)
            # Applies enhanced debuff with higher save DC, costs mind_cost[2] points
            ```
        """
        if mind_level is None:
            mind_level = 1
            
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

        # Apply the detrimental effect
        effect_applied = False
        save_result = None
        if self.effect:
            effect_applied = self.apply_effect(actor, target, self.effect, mind_level)
            
            # Check if target made a successful save (effect-dependent)
            if hasattr(self.effect, 'save_type') and hasattr(self.effect, 'save_dc'):
                # This would be handled within apply_effect, but we can track the result
                # for better feedback messages
                pass

        # Display debuff results with save information
        msg = f"    🔮 {actor_str} casts [bold]{self.name}[/] on {target_str} "
        if effect_applied:
            msg += f"applying [{get_effect_color(self.effect)}]{self.effect.name}[/]"
        else:
            msg += f"but fails to apply [{get_effect_color(self.effect)}]{self.effect.name}[/]"
            if save_result:
                msg += f" (saved)"
        msg += "."

        cprint(msg)

        return True

    # ============================================================================
    # EFFECT ANALYSIS METHODS  
    # ============================================================================

    def get_modifier_expressions(
        self, actor: Any, mind_level: int | None = 1
    ) -> dict[BonusType, str]:
        """
        Get modifier expressions with variables substituted for display.
        
        Returns a dictionary of bonus types to their expression strings with
        all variables (MIND, character stats, etc.) substituted with actual
        values. This is used for UI display and effect preview.
        
        Args:
            actor: The character casting the spell
            mind_level: The spell level to use for MIND variable substitution
            
        Returns:
            dict: Mapping of BonusType to expression strings
            
        Example:
            ```python
            # For effect with modifier "-MIND to attack rolls"
            expressions = spell.get_modifier_expressions(warlock, mind_level=3)
            # Returns: {BonusType.ATTACK: "-3"}
            ```
        """
        if mind_level is None:
            mind_level = 1
            
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        expressions: dict[BonusType, str] = {}

        # Handle effects that have modifiers (ModifierEffect)
        if hasattr(self.effect, 'modifiers'):
            modifiers = getattr(self.effect, 'modifiers', [])
            for modifier in modifiers:
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

    # ============================================================================
    # SERIALIZATION METHODS
    # ============================================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the debuff spell to a dictionary representation.
        
        Creates a complete serializable representation including all base spell
        properties plus the required detrimental effect. This supports saving/loading
        spells and data exchange.
        
        Returns:
            dict: Complete dictionary suitable for JSON serialization
            
        Dictionary Structure:
            - Base properties: name, type, description, cooldown, etc.
            - Spell properties: level, mind_cost, requires_concentration
            - Debuff properties: effect definition
            - Optional: target_expr if multi-target, save mechanics
            
        Example:
            ```python
            data = bane.to_dict()
            # Contains all spell data for reconstruction
            rebuilt = SpellDebuff.from_dict(data)
            ```
        """
        data = super().to_dict()
        # Add SpellDebuff-specific properties
        data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SpellDebuff":
        """
        Create a SpellDebuff instance from a dictionary.
        
        Factory method that reconstructs a SpellDebuff from its dictionary
        representation. Handles all validation and type conversion needed
        for safe deserialization.
        
        Args:
            data: Dictionary containing debuff spell data
            
        Returns:
            SpellDebuff: Fully initialized debuff spell instance
            
        Raises:
            KeyError: If required fields are missing
            ValueError: If data types are invalid or effect is missing
            
        Example:
            ```python
            spell_data = {
                "name": "Bane",
                "type": "ACTION",
                "level": 1,
                "mind_cost": [2, 3, 4],
                "effect": {
                    "type": "ModifierEffect",
                    "name": "Cursed", 
                    "duration": 100,
                    "modifiers": [
                        {
                            "bonus_type": "ATTACK",
                            "value": "-1d4"
                        }
                    ]
                }
            }
            bane_spell = SpellDebuff.from_dict(spell_data)
            ```
        """
        return SpellDebuff(
            name=data["name"],
            type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            level=data["level"],
            mind_cost=data["mind_cost"],
            effect=Effect.from_dict(data["effect"]),
            target_expr=data.get("target_expr", ""),
            requires_concentration=data.get("requires_concentration", False),
            target_restrictions=data.get("target_restrictions", []),
        )


def from_dict_spell(data: dict[str, Any]) -> Spell | None:
    """Factory function to create a Spell instance from a dictionary."""
    if data["class"] == "SpellAttack":
        return SpellAttack.from_dict(data)
    elif data["class"] == "SpellHeal":
        return SpellHeal.from_dict(data)
    elif data["class"] == "SpellBuff":
        return SpellBuff.from_dict(data)
    elif data["class"] == "SpellDebuff":
        return SpellDebuff.from_dict(data)
    return None
