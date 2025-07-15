from abc import abstractmethod
import json
from logging import debug, error
from rich.console import Console
from typing import Any, Optional
from pathlib import Path

from combat.damage import *
from core.utils import *
from core.constants import *
from combat.damage import *
from effects.effect import *

console = Console()


class BaseAction:
    def __init__(
        self,
        name: str,
        type: ActionType,
        category: ActionCategory,
        cooldown: int,
        maximum_uses: int,
    ):
        self.name: str = name
        self.type: ActionType = type
        self.category: ActionCategory = category
        self.cooldown: int = cooldown
        self.maximum_uses: int = maximum_uses

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
        return False

    def to_dict(self) -> dict[str, Any]:
        """Converts the action to a dictionary representation.

        Returns:
            dict: A dictionary containing the executable's data.
        """
        return {
            "class": self.__class__.__name__,
            "name": self.name,
            "type": self.type.name,
            "category": self.category.name,
            "cooldown": self.cooldown,
            "maximum_uses": self.maximum_uses,
        }
