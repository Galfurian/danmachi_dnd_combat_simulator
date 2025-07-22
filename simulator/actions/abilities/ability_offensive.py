"""
Offensive abilities that deal damage to enemies.

This module contains the OffensiveAbility class for damage-dealing special
abilities like breath weapons, natural attacks, and combat techniques.
"""

from typing import Any

from actions.abilities.base_ability import BaseAbility
from combat.damage import DamageComponent, roll_damage_components_no_mind
from core.constants import ActionCategory, ActionType, GLOBAL_VERBOSE_LEVEL
from core.error_handling import ensure_list_of_type, log_critical
from core.utils import cprint
from effects.effect import Effect


class OffensiveAbility(BaseAbility):
    """
    Offensive abilities that deal damage to targets.

    OffensiveAbility represents damage-dealing special powers like dragon breath
    weapons, natural attacks, monster abilities, and combat techniques. These
    abilities deal direct damage without requiring attack rolls in most cases.
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
        Initialize a new OffensiveAbility.

        Args:
            name: Display name of the ability
            type: Action type (STANDARD, BONUS, REACTION, etc.)
            description: Flavor text describing what the ability does
            cooldown: Turns to wait before reusing (0 = no cooldown)
            maximum_uses: Max uses per encounter/day (-1 = unlimited)
            damage: List of damage components to roll when used
            effect: Optional effect applied to targets on successful hits
            target_expr: Expression determining number of targets ("" = single target)
            target_restrictions: Override default targeting if needed

        Raises:
            ValueError: If name is empty or required parameters are invalid
        """
        try:
            super().__init__(
                name,
                type,
                ActionCategory.OFFENSIVE,
                description,
                cooldown,
                maximum_uses,
                effect,
                target_expr,
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

        except Exception as e:
            log_critical(
                f"Error initializing OffensiveAbility {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

    def execute(self, actor: Any, target: Any) -> bool:
        """
        Execute this offensive ability against a target.

        This method handles the complete offensive ability activation sequence
        from damage calculation through effect application.

        Args:
            actor: The character using the ability (must have combat methods)
            target: The character being damaged (must have combat methods)

        Returns:
            bool: True if ability was executed successfully, False on system errors
        """
        actor_str, target_str = self._get_display_strings(actor, target)

        # Check cooldown and uses
        assert not actor.is_on_cooldown(self), f"Action {self.name} is on cooldown."

        # Roll base damage from the ability
        base_damage, base_damage_details = roll_damage_components_no_mind(
            actor, target, self.damage
        )

        # Get any bonus damage from effects
        bonus_damage, bonus_damage_details = self._roll_bonus_damage(actor, target)

        # Calculate total damage
        total_damage = base_damage + bonus_damage
        damage_details = base_damage_details + bonus_damage_details

        # Apply damage to target
        target.take_damage(total_damage)

        # Check if target is defeated
        is_dead = not target.is_alive()

        # Apply effects if target is still alive (or if effect works on dead targets)
        effect_applied = self._apply_common_effects(actor, target)

        # Display results
        self._display_execution_result(
            actor_str, target_str, total_damage, damage_details, is_dead, effect_applied
        )

        return True

    def _display_execution_result(
        self,
        actor_str: str,
        target_str: str,
        total_damage: int,
        damage_details: list[str],
        is_dead: bool,
        effect_applied: bool,
    ) -> None:
        """
        Display the results of the offensive ability execution.

        Args:
            actor_str: Formatted actor name string
            target_str: Formatted target name string
            total_damage: Total damage dealt
            damage_details: List of damage component descriptions
            is_dead: Whether the target was defeated
            effect_applied: Whether effect was successfully applied
        """
        msg = f"    🔥 {actor_str} uses [bold blue]{self.name}[/] on {target_str}"

        if GLOBAL_VERBOSE_LEVEL == 0:
            msg += f" dealing {total_damage} damage"
            if is_dead:
                msg += f" defeating {target_str}"
            elif self.effect:
                if effect_applied:
                    msg += f" and applying"
                else:
                    msg += f" and failing to apply"
                msg += f" [bold yellow]{self.effect.name}[/]"
            msg += "."
        elif GLOBAL_VERBOSE_LEVEL >= 1:
            if damage_details:
                msg += f" dealing {total_damage} damage → "
                msg += " + ".join(damage_details)
            else:
                msg += f" dealing {total_damage} damage"
            msg += ".\n"

            if is_dead:
                msg += f"        {target_str} is defeated."
            elif self.effect:
                if effect_applied:
                    msg += f"        {target_str} is affected by"
                else:
                    msg += f"        {target_str} resists"
                msg += f" [bold yellow]{self.effect.name}[/]."

        cprint(msg)

    # ============================================================================
    # DAMAGE CALCULATION METHODS
    # ============================================================================

    def get_damage_expr(self, actor: Any) -> str:
        """
        Returns the damage expression with variables substituted.

        Args:
            actor: The character using the ability

        Returns:
            str: Complete damage expression with variables replaced by values
        """
        return super()._common_get_damage_expr(actor, self.damage)

    def get_min_damage(self, actor: Any) -> int:
        """
        Returns the minimum possible damage value for the ability.

        Args:
            actor: The character using the ability

        Returns:
            int: Minimum total damage across all damage components
        """
        return super()._common_get_min_damage(actor, self.damage)

    def get_max_damage(self, actor: Any) -> int:
        """
        Returns the maximum possible damage value for the ability.

        Args:
            actor: The character using the ability

        Returns:
            int: Maximum total damage across all damage components
        """
        return super()._common_get_max_damage(actor, self.damage)

    # ============================================================================
    # SERIALIZATION METHODS
    # ============================================================================

    def to_dict(self) -> dict[str, Any]:
        """Convert offensive ability to dictionary using AbilitySerializer."""
        from actions.abilities.ability_serializer import AbilitySerializer

        return AbilitySerializer.serialize(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "OffensiveAbility | None":
        """Create OffensiveAbility from dictionary using AbilityDeserializer."""
        from actions.abilities.ability_serializer import AbilityDeserializer

        return AbilityDeserializer.deserialize(data)
