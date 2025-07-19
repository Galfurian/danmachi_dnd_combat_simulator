from typing import Any, Optional

from actions.base_action import BaseAction
from combat.damage import DamageComponent, roll_damage_components_no_mind
from core.constants import (
    ActionCategory, ActionType, BonusType, GLOBAL_VERBOSE_LEVEL,
    apply_character_type_color, get_effect_color, is_oponent
)
from core.error_handling import GameError, ErrorSeverity, error_handler
from core.utils import (
    debug, parse_expr_and_assume_max_roll, parse_expr_and_assume_min_roll, 
    substitute_variables, cprint
)
from effects.effect import Effect


class BaseAbility(BaseAction):
    """Base class for creature abilities (like dragon breath, wing buffet, etc.)
    
    Unlike spells, abilities don't use mind points or spellcasting abilities.
    They typically have uses per day/encounter or cooldowns instead.
    """
    
    def __init__(
        self,
        name: str,
        type: ActionType,
        description: str,
        cooldown: int,
        maximum_uses: int,
        damage: list[DamageComponent],
        effect: Optional[Effect] = None,
        target_expr: str = "",
        target_restrictions: list[str] | None = None,
    ):
        try:
            super().__init__(
                name, type, ActionCategory.OFFENSIVE, description, cooldown, maximum_uses, target_restrictions
            )
            
            # Validate damage list
            if not isinstance(damage, list):
                error_handler.handle_error(GameError(
                    f"Ability {name} damage must be list, got: {damage.__class__.__name__}",
                    ErrorSeverity.HIGH,
                    {"name": name, "damage": damage}
                ))
                damage = []
            else:
                # Validate each damage component
                for i, dmg_comp in enumerate(damage):
                    if not isinstance(dmg_comp, DamageComponent):
                        error_handler.handle_error(GameError(
                            f"Ability {name} damage[{i}] must be DamageComponent, got: {dmg_comp.__class__.__name__}",
                            ErrorSeverity.HIGH,
                            {"name": name, "damage_index": i, "damage_component": dmg_comp}
                        ))
            
            # Validate effect
            if effect is not None and not isinstance(effect, Effect):
                error_handler.handle_error(GameError(
                    f"Ability {name} effect must be Effect or None, got: {effect.__class__.__name__}",
                    ErrorSeverity.MEDIUM,
                    {"name": name, "effect": effect}
                ))
                effect = None
                
            # Validate target_expr
            if not isinstance(target_expr, str):
                error_handler.handle_error(GameError(
                    f"Ability {name} target_expr must be string, got: {target_expr.__class__.__name__}",
                    ErrorSeverity.MEDIUM,
                    {"name": name, "target_expr": target_expr}
                ))
                target_expr = str(target_expr) if target_expr is not None else ""
            
            self.damage: list[DamageComponent] = damage
            self.effect: Optional[Effect] = effect
            self.target_expr: str = target_expr
            
        except Exception as e:
            error_handler.handle_error(GameError(
                f"Error initializing BaseAbility {name}: {str(e)}",
                ErrorSeverity.CRITICAL,
                {"name": name, "error": str(e)}
            ))
            raise

    def is_single_target(self) -> bool:
        """Check if the ability is single-target.

        Returns:
            bool: True if single-target, False otherwise.
        """
        return not self.target_expr or self.target_expr.strip() == ""

    def target_count(self, actor: Any) -> int:
        """Returns the number of targets this ability can affect.

        Args:
            actor (Any): The character using the ability.

        Returns:
            int: The number of targets this ability can affect.
        """
        if self.target_expr:
            from core.utils import evaluate_expression
            variables = actor.get_expression_variables()
            return max(1, int(evaluate_expression(self.target_expr, variables)))
        return 1

    def execute(self, actor: Any, target: Any) -> bool:
        """Execute the ability.

        Args:
            actor (Any): The character using the ability.
            target (Any): The character targeted by the ability.

        Returns:
            bool: True if the ability was successfully used, False otherwise.
        """
        actor_str = apply_character_type_color(actor.type, actor.name)
        target_str = apply_character_type_color(target.type, target.name)

        debug(f"{actor.name} attempts to use {self.name} on {target.name}.")

        # Check cooldown and uses
        assert not actor.is_on_cooldown(self), f"Action {self.name} is on cooldown."

        # Roll damage directly (no spell attack roll needed for most abilities)
        base_damage, base_damage_details = roll_damage_components_no_mind(
            actor, target, self.damage
        )

        # Get any damage modifiers from effects
        all_damage_modifiers = actor.effect_manager.get_damage_modifiers()
        bonus_damage, bonus_damage_details = roll_damage_components_no_mind(
            actor, target, all_damage_modifiers
        )

        # Calculate total damage
        total_damage = base_damage + bonus_damage
        damage_details = base_damage_details + bonus_damage_details

        # Check if target is defeated
        is_dead = not target.is_alive()

        # Display message
        msg = f"    🔥 {actor_str} uses [bold blue]{self.name}[/] on {target_str}"
        
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
            msg += f" dealing {total_damage} damage to {target_str} → "
            msg += " + ".join(damage_details) + ".\n"
            if is_dead:
                msg += f"        {target_str} is defeated."
            elif self.effect:
                if self.apply_effect(actor, target, self.effect):
                    msg += f"        {target_str} is affected by"
                else:
                    msg += f"        {target_str} is not affected by"
                msg += f" [{get_effect_color(self.effect)}]{self.effect.name}[/]."
        
        cprint(msg)

        return True

    def get_damage_expr(self, actor: Any) -> str:
        """Returns the damage expression with variables substituted.

        Args:
            actor (Any): The character using the ability.

        Returns:
            str: The damage expression with variables substituted.
        """
        return " + ".join(
            substitute_variables(component.damage_roll, actor)
            for component in self.damage
        )

    def get_min_damage(self, actor: Any) -> int:
        """Returns the minimum damage value for the ability.

        Args:
            actor (Any): The character using the ability.

        Returns:
            int: The minimum damage value for the ability.
        """
        return sum(
            parse_expr_and_assume_min_roll(
                substitute_variables(component.damage_roll, actor)
            )
            for component in self.damage
        )

    def get_max_damage(self, actor: Any) -> int:
        """Returns the maximum damage value for the ability.

        Args:
            actor (Any): The character using the ability.

        Returns:
            int: The maximum damage value for the ability.
        """
        return sum(
            parse_expr_and_assume_max_roll(
                substitute_variables(component.damage_roll, actor)
            )
            for component in self.damage
        )

    def to_dict(self) -> dict[str, Any]:
        """Converts the ability to a dictionary representation."""
        data = super().to_dict()
        # Add specific fields for BaseAbility
        data["damage"] = [component.to_dict() for component in self.damage]
        if self.target_expr:
            data["target_expr"] = self.target_expr
        if self.effect:
            data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "BaseAbility":
        """Creates a BaseAbility instance from a dictionary."""
        return BaseAbility(
            name=data["name"],
            type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            damage=[DamageComponent.from_dict(comp) for comp in data["damage"]],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
            target_expr=data.get("target_expr", ""),
            target_restrictions=data.get("target_restrictions"),
        )


def from_dict_ability(data: dict[str, Any]) -> Optional[BaseAbility]:
    """Factory function to create an ability instance from a dictionary."""
    ability_class = data.get("class", "BaseAbility")
    
    if ability_class == "BaseAbility":
        return BaseAbility.from_dict(data)
    
    return None
