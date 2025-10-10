"""
Instant damage effect module for the simulator.

Defines effects that deal damage immediately upon application.
"""

from typing import Any, Literal

from combat.damage import DamageComponent
from core.dice_parser import VarInfo, roll_and_describe
from core.logging import effects_logger as logger
from core.utils import cprint
from pydantic import Field

from .base_effect import Effect


class InstantDamageEffect(Effect):
    """
    Instant damage effect that deals damage immediately upon application.

    Used for effects like thorns, backfire, etc., that deal damage instantly
    when triggered.
    """

    effect_type: Literal["InstantDamageEffect"] = "InstantDamageEffect"

    damage: DamageComponent = Field(
        description="Damage component defining the damage roll and type.",
    )

    @property
    def color(self) -> str:
        """Returns the color string for instant damage effects."""
        return "bold red"

    @property
    def emoji(self) -> str:
        """Returns the emoji for instant damage effects."""
        return "💥"

    def model_post_init(self, _: Any) -> None:
        if self.duration is not None and self.duration != 0:
            raise ValueError(
                "Duration must be 0 or None for InstantDamageEffect."
            )
        if not isinstance(self.damage, DamageComponent):
            raise ValueError("Damage must be of type DamageComponent.")

    def can_apply(
        self,
        actor: Any,
        target: Any,
        variables: list[VarInfo],
    ) -> bool:
        """
        Check if the instant damage effect can be applied to the target.

        Rules for instant damage application:
            1. Basic eligibility: Actor and target must be alive Characters
            2. Damage type immunity: Target cannot be immune to the damage type

        Args:
            actor (Character):
                The character applying the effect.
            target (Character):
                The character receiving the effect.
            variables (list[VarInfo]):
                List of variable info for dynamic calculations.

        Returns:
            bool:
                True if the effect can be applied, False otherwise.

        """
        from character.main import Character

        # Rule 1: Basic validation from parent class
        if not super().can_apply(actor, target, variables):
            return False

        assert isinstance(actor, Character), "Actor must be a Character."
        assert isinstance(target, Character), "Target must be a Character."

        # Rule 2: Damage type immunity check
        if self.damage.damage_type in target.immunities:
            logger.debug(
                f"Cannot apply instant damage effect: Target {target.colored_name} "
                f"is immune to {self.damage.damage_type}."
            )
            return False

        return True

    def apply_effect(
        self,
        actor: Any,
        target: Any,
        variables: list[VarInfo],
    ) -> bool:
        """
        Apply the instant damage effect to the target, dealing damage immediately.

        Args:
            actor (Character):
                The character applying the effect.
            target (Character):
                The character receiving the effect.
            variables (list[VarInfo]):
                List of variable info for dynamic calculations.

        Returns:
            bool:
                True if the effect was applied successfully, False otherwise.

        """
        from character.main import Character

        if not self.can_apply(actor, target, variables):
            return False

        assert isinstance(actor, Character), "Actor must be a Character."
        assert isinstance(target, Character), "Target must be a Character."

        # Apply damage immediately
        outcome = roll_and_describe(self.damage.damage_roll, variables)
        if outcome.value < 0:
            raise ValueError(
                "Damage value must be non-negative for InstantDamageEffect"
                f" '{self.name}', got {outcome.value}."
            )
        base, adjusted, taken = target.take_damage(outcome.value, self.damage.damage_type)
        damage_str = f"    {self.emoji} "
        damage_str += target.colored_name + " takes "
        damage_str += f"{self.damage.color_roll(taken)} "
        if base != adjusted:
            damage_str += f"[dim](reduced: {base} → {adjusted})[/] "
        damage_str += f"({outcome.description})"
        cprint(damage_str)
        if not target.is_alive():
            cprint(f"    [bold red]{target.name} has been defeated![/]")
        logger.debug(
            f"Instant damage effect '{self.name}' on {target.colored_name} "
            f"dealt {taken} {self.damage.damage_type} damage."
        )
        return True
