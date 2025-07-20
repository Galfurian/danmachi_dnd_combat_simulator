"""
Healing spell implementation.

This module contains the SpellHeal class for restorative magical spells
that restore hit points and can apply beneficial effects.
"""

from logging import debug
from typing import Any

from actions.spells.base_spell import Spell
from core.constants import (
    ActionCategory,
    ActionType,
    GLOBAL_VERBOSE_LEVEL,
    get_character_type_color,
    get_effect_color,
)
from core.error_handling import (
    log_error,
    log_warning,
    log_critical,
    ensure_string,
)
from core.utils import (
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    roll_and_describe,
    simplify_expression,
    substitute_variables,
    cprint,
)
from effects.effect import Effect


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
        """Execute a healing spell with automatic success and beneficial effects."""
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
        """Get healing expression with variables substituted for display."""
        if mind_level is None:
            mind_level = 1
            
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return simplify_expression(self.heal_roll, variables)

    def get_min_heal(self, actor: Any, mind_level: int | None = 1) -> int:
        """Calculate the minimum possible healing for the spell."""
        if mind_level is None:
            mind_level = 1
            
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return parse_expr_and_assume_min_roll(
            substitute_variables(self.heal_roll, variables)
        )

    def get_max_heal(self, actor: Any, mind_level: int | None = 1) -> int:
        """Calculate the maximum possible healing for the spell."""
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
        """Convert the healing spell to a dictionary representation."""
        data = super().to_dict()
        # Add SpellHeal-specific properties
        data["heal_roll"] = self.heal_roll
        # Include optional effect if present
        if self.effect:
            data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SpellHeal":
        """Create a SpellHeal instance from a dictionary."""
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
