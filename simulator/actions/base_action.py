from logging import debug, error
from typing import Any, Optional

from combat.damage import *
from core.utils import *
from core.constants import *
from effects.effect import *


class BaseAction:
    def __init__(
        self,
        name: str,
        type: ActionType,
        category: ActionCategory,
        description: str = "",
        cooldown: int = 0,
        maximum_uses: int = 0,
        target_restrictions: list[str] | None = None,
    ):
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
        if not effect:
            return False
        if not actor.is_alive():
            return False
        if not target.is_alive():
            return False
        if target.effect_manager.add_effect(actor, effect, mind_level):
            debug(f"Applied effect {effect.name} from {actor.name} to {target.name}.")
            return True
        debug(f"Not applied effect {effect.name} from {actor.name} to {target.name}.")
        return False

    def roll_attack_with_crit(
        self, actor, attack_bonus_expr: str, bonus_list: list[str]
    ) -> Tuple[int, str, int]:
        expr = "1D20"
        if attack_bonus_expr:
            expr += f" + {attack_bonus_expr}"
        for bonus in bonus_list:
            expr += f" + {bonus}"
        total, desc, rolls = roll_and_describe(expr, actor.get_expression_variables())
        return total, desc, rolls[0] if rolls else 0

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
