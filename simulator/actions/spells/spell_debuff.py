"""Detrimental spell debuff implementation."""

from logging import debug
from typing import Any

from actions.spells.base_spell import Spell
from core.constants import (
    ActionCategory,
    ActionType,
    BonusType,
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
from effects.base_effect import Effect
from combat.damage import DamageComponent


class SpellDebuff(Spell):
    """Detrimental spell that weakens enemies with negative effects.

    This class represents spells designed to apply debuffs or negative effects
    to enemies. It includes attributes for required effects and methods for
    applying those effects during combat.
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
        """Initialize a new SpellDebuff.
        
        Args:
            name (str): Display name of the spell.
            type (ActionType): Action type (ACTION, BONUS_ACTION, REACTION, etc.).
            description (str): Flavor text describing what the spell does.
            cooldown (int): Turns to wait before reusing (0 = no cooldown).
            maximum_uses (int): Max uses per encounter/day (-1 = unlimited).
            level (int): Base spell level (1-9 for most spells, 0 for cantrips).
            mind_cost (list[int]): List of mind point costs per casting level.
            effect (Effect): Required detrimental effect applied to targets.
            target_expr (str): Expression determining number of targets.
            requires_concentration (bool): Whether spell requires concentration.
            target_restrictions (list[str] | None): Override default targeting if needed.
        
        Raises:
            ValueError: If effect is None or invalid.
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
                log_critical(f"SpellDebuff {name} must have an effect", {"name": name})
                raise ValueError(f"SpellDebuff {name} must have an effect")

            if not isinstance(effect, Effect):
                log_critical(
                    f"SpellDebuff {name} effect must be an Effect instance, got: {type(effect).__name__}",
                    {"name": name, "effect_type": type(effect).__name__},
                )
                raise ValueError(
                    f"SpellDebuff {name} effect must be an Effect instance"
                )

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

    def cast_spell(self, actor: Any, target: Any, mind_level: int) -> bool:
        """Execute a debuff spell with automatic application and optional saves.
        
        Args:
            actor (Any): The character casting the spell.
            target (Any): The character targeted by the spell.
            mind_level (int): The spell level to cast at (affects cost and power).
        
        Returns:
            bool: True if spell was cast successfully, False on failure.
        """
        # Call the base class cast_spell to handle common checks.
        if super().cast_spell(actor, target, mind_level) is False:
            return False

        # Handle concentration requirements
        if self.requires_concentration:
            actor.concentration_module.break_concentration()

        # Format character strings for output.
        actor_str, target_str = self._get_display_strings(actor, target)

        # Apply the detrimental effect
        effect_applied = False
        save_result = None
        if self.effect:
            effect_applied = self._common_apply_effect(
                actor, target, self.effect, mind_level
            )

            # Check if target made a successful save (effect-dependent)
            if hasattr(self.effect, "save_type") and hasattr(self.effect, "save_dc"):
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
        """Get modifier expressions with variables substituted for display.
        
        Args:
            actor (Any): The character casting the spell.
            mind_level (int | None): The spell level to use for MIND variable substitution.
        
        Returns:
            dict[BonusType, str]: Dictionary mapping bonus types to their expressions.
        """
        if mind_level is None:
            mind_level = 1

        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        expressions: dict[BonusType, str] = {}

        # Handle effects that have modifiers (ModifierEffect)
        if hasattr(self.effect, "modifiers"):
            modifiers = getattr(self.effect, "modifiers", [])
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
