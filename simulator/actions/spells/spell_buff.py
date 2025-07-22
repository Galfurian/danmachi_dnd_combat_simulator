"""
Beneficial spell buff implementation.

This module contains the SpellBuff class for enhancement spells that apply
positive effects to allies and the caster.
"""

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
from effects.effect import Effect, ModifierEffect
from combat.damage import DamageComponent


class SpellBuff(Spell):
    """
    Beneficial spell that enhances targets with positive effects.

    SpellBuff represents magical enhancement spells that apply beneficial effects
    to allies or the caster. These spells automatically succeed without requiring
    attack rolls, making them reliable support options for improving combat
    effectiveness and providing tactical advantages.

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
        effect: Effect,
        target_expr: str = "",
        requires_concentration: bool = False,
        target_restrictions: list[str] | None = None,
    ):
        """
        Initialize a new SpellBuff.

        Args:
            name: Display name of the spell
            type: Action type (ACTION, BONUS_ACTION, REACTION, etc.)
            description: Flavor text describing what the spell does
            cooldown: Turns to wait before reusing (0 = no cooldown)
            maximum_uses: Max uses per encounter/day (-1 = unlimited)
            level: Base spell level (1-9 for most spells, 0 for cantrips)
            mind_cost: List of mind point costs per casting level
            effect: Required beneficial effect applied to targets
            target_expr: Expression determining number of targets
            requires_concentration: Whether spell requires concentration
            target_restrictions: Override default targeting if needed

        Raises:
            ValueError: If effect is None or invalid
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
                log_critical(f"SpellBuff {name} must have an effect", {"name": name})
                raise ValueError(f"SpellBuff {name} must have an effect")

            if not isinstance(effect, Effect):
                log_critical(
                    f"SpellBuff {name} effect must be an Effect instance, got: {type(effect).__name__}",
                    {"name": name, "effect_type": type(effect).__name__},
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

    def cast_spell(self, actor: Any, target: Any, mind_level: int) -> bool:
        """
        Execute a buff spell with automatic success and beneficial effects.

        Args:
            actor: The character casting the spell
            target: The character targeted by the spell
            mind_level: The spell level to cast at (affects cost and power)

        Returns:
            bool: True if spell was cast successfully, False on failure
        """
        # Call the base class cast_spell to handle common checks.
        if super().cast_spell(actor, target, mind_level) is False:
            return False

        # Handle concentration requirements
        if self.requires_concentration:
            actor.concentration_module.break_concentration()

        # Format character strings for output.
        actor_str, target_str = self._get_display_strings(actor, target)

        # Apply the beneficial effect
        effect_applied = False
        if self.effect:
            effect_applied = self._common_apply_effect(
                actor, target, self.effect, mind_level
            )

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

        Args:
            actor: The character casting the spell
            mind_level: The spell level to use for MIND variable substitution

        Returns:
            dict[BonusType, str]: Dictionary mapping bonus types to their expressions
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
