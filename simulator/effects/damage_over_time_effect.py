"""
Damage over time effect module for the simulator.

Defines effects that deal damage over multiple turns, such as
poison, bleed, or ongoing damage spells.
"""

from typing import Any, Literal

from combat.damage import DamageComponent
from core.dice_parser import VarInfo, roll_and_describe
from core.logging import log_debug
from core.utils import cprint
from pydantic import Field

from .base_effect import ActiveEffect, Effect


class DamageOverTimeEffect(Effect):
    """
    Damage over Time effect that deals damage each turn.

    Damage over Time effects continuously damage the target for a specified duration,
    using a damage roll expression that can include variables like MIND level.
    """

    effect_type: Literal["DamageOverTimeEffect"] = "DamageOverTimeEffect"

    damage: DamageComponent = Field(
        description="Damage component defining the damage roll and type.",
    )

    @property
    def color(self) -> str:
        """Returns the color string for damage over time effects."""
        return "bold magenta"

    @property
    def emoji(self) -> str:
        """Returns the emoji for damage over time effects."""
        return "❣️"

    def model_post_init(self, _: Any) -> None:
        if self.duration is None or self.duration <= 0:
            raise ValueError(
                "Duration must be a positive integer for DamageOverTimeEffect."
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
        Check if the damage over time effect can be applied to the target.

        Rules for DoT application:
            1. Basic eligibility: Actor and target must be alive Characters
            2. Self-targeting: Cannot apply damaging DoT to self (unless special
               case)
            3. Damage type immunity: Target cannot be immune to the damage type
            4. Stacking limit: Target cannot have 3 or more active DoT effects

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

        # Rule 2: Self-targeting restriction
        if actor == target:
            log_debug("Cannot apply DoT effect: Self-targeting is not allowed.")
            return False

        # Rule 3: Damage type immunity check
        if self.damage.damage_type in target.immunities:
            log_debug(
                f"Cannot apply DoT effect: Target {target.colored_name} "
                f"is immune to {self.damage.damage_type}."
            )
            return False

        # Rule 4: Stacking limit - prevent applying if target has 3+ DoT
        # effects.
        existing_effects = [
            effect
            for effect in target.effects.damage_over_time_effects
            if effect.effect.name == self.name
        ]
        # Allow refreshing the duration of an existing effect of the same name.
        if existing_effects:
            return True
        # Otherwise, enforce stacking limit.
        if sum(1 for _ in target.effects.damage_over_time_effects) >= 3:
            log_debug(
                f"Cannot apply DoT effect: Target {target.colored_name} "
                "already has 3 or more active DoT effects."
            )
            return False

        return True

    def apply_effect(
        self,
        actor: Any,
        target: Any,
        variables: list[VarInfo],
    ) -> None:
        """
        Apply the damage over time effect to the target, creating an
        ActiveEffect if valid.

        Args:
            actor (Character):
                The character applying the effect.
            target (Character):
                The character receiving the effect.
            variables (list[VarInfo]):
                List of variable info for dynamic calculations.

        """
        from character.main import Character

        if not self.can_apply(actor, target, variables):
            return None

        assert isinstance(actor, Character), "Actor must be a Character."
        assert isinstance(target, Character), "Target must be a Character."

        existing_effects = [
            effect
            for effect in target.effects.damage_over_time_effects
            if effect.effect.name == self.name
        ]

        assert len(existing_effects) <= 1, (
            "Data integrity error: More than one instance of the same "
            "DamageOverTimeEffect found on target."
        )

        # Refresh duration of existing effect.
        if existing_effects:
            existing_effects[0].duration = self.duration
            cprint(f"    ⚠️  {self.name} duration refreshed on {target.colored_name}.")
            return None

        log_debug(
            f"Applying DoT effect '{self.colored_name}' "
            f"from {actor.colored_name} to {target.colored_name}."
        )

        # Create new ActiveDamageOverTimeEffect.
        target.effects.active_effects.append(
            ActiveDamageOverTimeEffect(
                source=actor,
                target=target,
                effect=self,
                duration=self.duration,
                variables=variables,
            )
        )


class ActiveDamageOverTimeEffect(ActiveEffect):
    """
    Active Damage over Time effect that deals damage each turn.
    """

    @property
    def damage_over_time_effect(self) -> DamageOverTimeEffect:
        """
        Get the effect as a DamageOverTimeEffect (narrowed type for clarity).

        Raises:
            TypeError:
                If the effect is not a DamageOverTimeEffect.

        Returns:
            DamageOverTimeEffect:
                The effect cast as a DamageOverTimeEffect.

        """
        if not isinstance(self.effect, DamageOverTimeEffect):
            raise TypeError("Effect is not a DamageOverTimeEffect.")
        return self.effect

    def turn_update(self) -> None:
        """
        Update the effect for the current turn by calling the effect's
        turn_update method.
        """
        DOT = self.damage_over_time_effect

        # Calculate the damage amount using the provided expression.
        outcome = roll_and_describe(
            DOT.damage.damage_roll,
            self.variables,
        )
        if outcome.value < 0:
            raise ValueError(
                "Damage value must be non-negative for DamageOverTimeEffect"
                f" '{DOT.name}', got {outcome.value}."
            )
        # Apply the damage to the target.
        base, adjusted, taken = self.target.take_damage(
            outcome.value, DOT.damage.damage_type
        )
        # If the damage value is positive, print the damage message.
        dot_str = f"    {DOT.emoji} "
        dot_str += self.target.colored_name + " takes "
        # Create a damage string for display.
        dot_str += f"{DOT.damage.color_roll(taken)} "
        # If the base damage differs from the adjusted damage (due to resistances),
        # include the original and adjusted values in the damage string.
        if base != adjusted:
            dot_str += f"[dim](reduced: {base} → {adjusted})[/] "
        # Append the rolled damage expression to the damage string.
        dot_str += f"({outcome.description})"
        # Print the damage string.
        cprint(dot_str)
        # If the target is defeated, print a message.
        if not self.target.is_alive():
            cprint(f"    [bold red]{self.target.name} has been defeated![/]")
