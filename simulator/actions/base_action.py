from logging import debug, error
from typing import Any, Optional

from combat.damage import *
from core.utils import *
from core.constants import *
from core.error_handling import error_handler, ErrorSeverity, GameError
from effects.effect import *


class BaseAction:
    def __init__(
        self,
        name: str,
        type: ActionType,
        category: ActionCategory,
        description: str = "",
        cooldown: int = 0,
        maximum_uses: int = -1,
        target_restrictions: list[str] | None = None,
    ):
        # Validate inputs
        if not name or not isinstance(name, str):
            error_handler.handle_error(GameError(
                f"Action name must be a non-empty string, got: {name}",
                ErrorSeverity.HIGH,
                {"name": name, "type": type}
            ))
            raise ValueError(f"Invalid action name: {name}")
            
        if not isinstance(type, ActionType):
            error_handler.handle_error(GameError(
                f"Action type must be ActionType enum, got: {type(type).__name__}",
                ErrorSeverity.HIGH,
                {"name": name, "type": type}
            ))
            raise ValueError(f"Invalid action type: {type}")
            
        if not isinstance(category, ActionCategory):
            error_handler.handle_error(GameError(
                f"Action category must be ActionCategory enum, got: {type(category).__name__}",
                ErrorSeverity.HIGH,
                {"name": name, "category": category}
            ))
            raise ValueError(f"Invalid action category: {category}")
            
        if not isinstance(description, str):
            error_handler.handle_error(GameError(
                f"Action description must be string, got: {type(description).__name__}",
                ErrorSeverity.MEDIUM,
                {"name": name, "description": description}
            ))
            description = str(description) if description is not None else ""
            
        if not isinstance(cooldown, int) or cooldown < 0:
            error_handler.handle_error(GameError(
                f"Action cooldown must be non-negative integer, got: {cooldown}",
                ErrorSeverity.MEDIUM,
                {"name": name, "cooldown": cooldown}
            ))
            cooldown = max(0, int(cooldown) if isinstance(cooldown, (int, float)) else 0)
            
        if not isinstance(maximum_uses, int) or maximum_uses < -1:
            error_handler.handle_error(GameError(
                f"Action maximum_uses must be integer >= -1 (where -1 = unlimited), got: {maximum_uses}",
                ErrorSeverity.MEDIUM,
                {"name": name, "maximum_uses": maximum_uses}
            ))
            maximum_uses = max(-1, int(maximum_uses) if isinstance(maximum_uses, (int, float)) else -1)
            
        self.name: str = name
        self.type: ActionType = type
        self.category: ActionCategory = category
        self.description: str = description
        self.cooldown: int = cooldown
        self.maximum_uses: int = maximum_uses
        self.target_restrictions: list[str] = target_restrictions or []

    def execute(self, actor: Any, target: Any) -> bool:
        """Abstract method for executables.

        Args:
            actor (Any): The character performing the action.
            target (Any): The character targeted by the action.

        Returns:
            bool: True if the action was successfully executed, False otherwise.
        """
        ...

    def apply_effect(
        self,
        actor: Any,
        target: Any,
        effect: Optional[Effect],
        mind_level: Optional[int] = 0,
    ) -> bool:
        """Applies an effect to a target character.

        Args:
            actor (Any): The character performing the action.
            target (Any): The character targeted by the action.
            effect (Optional[Effect]): The effect to apply.
            mind_level (Optional[int], optional): The mind_cost level to use for the effect. Defaults to 0.

        Returns:
            bool: True if the effect was successfully applied, False otherwise.
        """
        try:
            if not effect:
                return False
            
            if not actor:
                error_handler.handle_error(GameError(
                    f"Cannot apply effect {effect.name}: actor is None",
                    ErrorSeverity.MEDIUM,
                    {"effect": effect.name, "actor": actor}
                ))
                return False
                
            if not target:
                error_handler.handle_error(GameError(
                    f"Cannot apply effect {effect.name}: target is None",
                    ErrorSeverity.MEDIUM,
                    {"effect": effect.name, "actor": getattr(actor, 'name', 'Unknown'), "target": target}
                ))
                return False
                
            if not hasattr(actor, 'is_alive') or not callable(actor.is_alive):
                error_handler.handle_error(GameError(
                    f"Actor lacks is_alive method for effect {effect.name}",
                    ErrorSeverity.HIGH,
                    {"effect": effect.name, "actor": getattr(actor, 'name', 'Unknown')}
                ))
                return False
                
            if not hasattr(target, 'is_alive') or not callable(target.is_alive):
                error_handler.handle_error(GameError(
                    f"Target lacks is_alive method for effect {effect.name}",
                    ErrorSeverity.HIGH,
                    {"effect": effect.name, "target": getattr(target, 'name', 'Unknown')}
                ))
                return False
                
            if not actor.is_alive():
                return False
            if not target.is_alive():
                return False
                
            if not hasattr(target, 'effect_manager'):
                error_handler.handle_error(GameError(
                    f"Target lacks effect_manager for effect {effect.name}",
                    ErrorSeverity.HIGH,
                    {"effect": effect.name, "target": getattr(target, 'name', 'Unknown')}
                ))
                return False
                
            # Validate mind_level
            if not isinstance(mind_level, int) or mind_level < 0:
                error_handler.handle_error(GameError(
                    f"Invalid mind_level for effect {effect.name}: {mind_level}",
                    ErrorSeverity.MEDIUM,
                    {"effect": effect.name, "mind_level": mind_level}
                ))
                mind_level = max(0, int(mind_level) if isinstance(mind_level, (int, float)) else 0)
            
            if target.effect_manager.add_effect(actor, effect, mind_level):
                debug(f"Applied effect {effect.name} from {actor.name} to {target.name}.")
                return True
            debug(f"Not applied effect {effect.name} from {actor.name} to {target.name}.")
            return False
            
        except Exception as e:
            error_handler.handle_error(GameError(
                f"Error applying effect {getattr(effect, 'name', 'Unknown')}: {str(e)}",
                ErrorSeverity.HIGH,
                {"effect": getattr(effect, 'name', 'Unknown'), "error": str(e), 
                 "actor": getattr(actor, 'name', 'Unknown'), "target": getattr(target, 'name', 'Unknown')}
            ))
            return False

    def roll_attack_with_crit(
        self, actor, attack_bonus_expr: str, bonus_list: list[str]
    ) -> Tuple[int, str, int]:
        """Roll attack with critical hit detection."""
        try:
            if not actor:
                error_handler.handle_error(GameError(
                    "Cannot roll attack: actor is None",
                    ErrorSeverity.HIGH,
                    {"actor": actor}
                ))
                return 1, "1D20: 1", 1  # Return minimum valid roll
            
            if not hasattr(actor, 'get_expression_variables'):
                error_handler.handle_error(GameError(
                    f"Actor {getattr(actor, 'name', 'Unknown')} lacks get_expression_variables method",
                    ErrorSeverity.HIGH,
                    {"actor": getattr(actor, 'name', 'Unknown')}
                ))
                return 1, "1D20: 1", 1  # Return minimum valid roll
            
            expr = "1D20"
            if attack_bonus_expr and isinstance(attack_bonus_expr, str):
                expr += f" + {attack_bonus_expr}"
            elif attack_bonus_expr:
                error_handler.handle_error(GameError(
                    f"Invalid attack_bonus_expr type: {type(attack_bonus_expr).__name__}",
                    ErrorSeverity.MEDIUM,
                    {"attack_bonus_expr": attack_bonus_expr, "type": type(attack_bonus_expr).__name__}
                ))
            
            if bonus_list:
                if not isinstance(bonus_list, list):
                    error_handler.handle_error(GameError(
                        f"bonus_list must be a list, got: {type(bonus_list).__name__}",
                        ErrorSeverity.MEDIUM,
                        {"bonus_list": bonus_list, "type": type(bonus_list).__name__}
                    ))
                    bonus_list = []
                else:
                    for bonus in bonus_list:
                        if isinstance(bonus, str):
                            expr += f" + {bonus}"
                        else:
                            error_handler.handle_error(GameError(
                                f"Bonus in bonus_list must be string, got: {type(bonus).__name__}",
                                ErrorSeverity.LOW,
                                {"bonus": bonus, "type": type(bonus).__name__}
                            ))
            
            variables = actor.get_expression_variables()
            if not isinstance(variables, dict):
                error_handler.handle_error(GameError(
                    f"Actor expression variables must be dict, got: {type(variables).__name__}",
                    ErrorSeverity.MEDIUM,
                    {"variables": variables, "actor": getattr(actor, 'name', 'Unknown')}
                ))
                variables = {}
            
            total, desc, rolls = roll_and_describe(expr, variables)
            return total, desc, rolls[0] if rolls else 0
            
        except Exception as e:
            error_handler.handle_error(GameError(
                f"Error rolling attack: {str(e)}",
                ErrorSeverity.HIGH,
                {"error": str(e), "actor": getattr(actor, 'name', 'Unknown'), 
                 "attack_bonus_expr": attack_bonus_expr, "bonus_list": bonus_list}
            ))
            return 1, "1D20: 1 (error)", 1  # Return safe fallback

    def is_valid_target(self, actor: Any, target: Any) -> bool:
        """Checks if the target is valid for the action.

        Args:
            actor (Any): The character performing the action.
            target (Any): The character targeted by the action.

        Returns:
            bool: True if the target is valid, False otherwise.
        """
        # If target_restrictions are defined, use the generic targeting system
        if self.target_restrictions:
            return self._check_target_restrictions(actor, target)
        
        # Otherwise, fall back to category-based default targeting
        return self._get_default_targeting_by_category(actor, target)
    
    def _check_target_restrictions(self, actor: Any, target: Any) -> bool:
        """Check if target is valid based on target_restrictions."""
        # Basic validation - both must be alive
        if not actor.is_alive() or not target.is_alive():
            return False
            
        # Check each restriction
        for restriction in self.target_restrictions:
            if restriction == "SELF" and actor == target:
                return True
            elif restriction == "ALLY" and self._is_relationship_valid(actor, target, is_ally=True):
                return True
            elif restriction == "ENEMY" and self._is_relationship_valid(actor, target, is_ally=False):
                return True
            elif restriction == "ANY":
                return True
                
        return False
    
    def _get_default_targeting_by_category(self, actor: Any, target: Any) -> bool:
        """Provide sensible default targeting based on action category."""
        # Basic validation - both must be alive
        if not actor.is_alive() or not target.is_alive():
            return False
            
        from core.constants import ActionCategory
        
        if self.category == ActionCategory.OFFENSIVE:
            # Offensive actions target enemies (not self, must be opponents)
            return target != actor and is_oponent(actor.type, target.type)
            
        elif self.category == ActionCategory.HEALING:
            # Healing actions target self and allies (not enemies, not at full health for healing)
            if target == actor:
                return target.hp < target.HP_MAX  # Can heal self if not at full health
            elif not is_oponent(actor.type, target.type):
                return target.hp < target.HP_MAX  # Can heal allies if not at full health
            return False
            
        elif self.category == ActionCategory.BUFF:
            # Buff actions target self and allies
            return target == actor or not is_oponent(actor.type, target.type)
            
        elif self.category == ActionCategory.DEBUFF:
            # Debuff actions target enemies
            return target != actor and is_oponent(actor.type, target.type)
            
        elif self.category == ActionCategory.UTILITY:
            # Utility actions can target anyone
            return True
            
        elif self.category == ActionCategory.DEBUG:
            # Debug actions can target anyone
            return True
            
        else:
            # Unknown category - default to no targeting
            return False
    
    def _is_relationship_valid(self, actor: Any, target: Any, is_ally: bool) -> bool:
        """Helper to check if actor and target have the correct relationship."""
        if actor == target:  # Self is neither ally nor enemy in this context
            return False
        
        # Check if they are opponents (enemies to each other)
        are_opponents = is_oponent(actor.type, target.type)
        
        if is_ally:
            return not are_opponents  # Allies are not opponents
        else:
            return are_opponents  # Enemies are opponents

    def to_dict(self) -> dict[str, Any]:
        """Converts the action to a dictionary representation.

        Returns:
            dict: A dictionary containing the executable's data.
        """
        data = {
            "class": self.__class__.__name__,
            "name": self.name,
            "type": self.type.name,
            "category": self.category.name,
            "description": self.description,
            "cooldown": self.cooldown,
            "maximum_uses": self.maximum_uses,
        }
        if self.target_restrictions:
            data["target_restrictions"] = self.target_restrictions
        return data
