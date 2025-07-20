"""
Detrimental spell debuff implementation.

This module contains the SpellDebuff class for weakening spells that apply
harmful effects to enemies to reduce their combat effectiveness.
"""

from logging import debug
from typing import Any

from actions.spells.base_spell import Spell
from core.constants import (
    ActionCategory,
    ActionType,
    BonusType,
    get_character_type_color,
    get_effect_color,
)
from core.error_handling import (
    log_error,
    log_warning,
    log_critical,
)
from core.utils import (
    substitute_variables,
    cprint,
)
from effects.effect import Effect
from combat.damage import DamageComponent


class SpellDebuff(Spell):
    """
    Detrimental spell that weakens enemies with negative effects.
    
    SpellDebuff represents magical debuffing spells that apply harmful effects
    to enemies to reduce their combat effectiveness. Unlike offensive damage
    spells, debuff spells focus on applying persistent penalties, conditions,
    or restrictions that hinder enemy capabilities over time.
    
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
        effect: Effect,
        target_expr: str = "",
        requires_concentration: bool = False,
        target_restrictions: list[str] | None = None,
    ):
        """Initialize a new SpellDebuff."""
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
        """Execute a debuff spell with automatic application and optional saves."""
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
        """Get modifier expressions with variables substituted for display."""
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
        """Convert the debuff spell to a dictionary representation."""
        data = super().to_dict()
        # Add SpellDebuff-specific properties
        data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SpellDebuff":
        """Create a SpellDebuff instance from a dictionary."""
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
