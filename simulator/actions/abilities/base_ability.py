"""
Base ability module for the simulator.

Defines the base classes for character abilities, including offensive, defensive,
healing, and buff abilities, with common functionality for execution and effects.
"""

from typing import TYPE_CHECKING, Any

from actions.base_action import BaseAction
from core.dice_parser import VarInfo

if TYPE_CHECKING:
    from character.main import Character


class BaseAbility(BaseAction):
    """Abstract base class for all character abilities and special powers.

    This class provides a foundation for implementing various types of abilities,
    such as offensive, healing, buff, and utility abilities. It includes shared
    functionality like targeting and serialization, while requiring subclasses
    to implement specific behavior through abstract methods.
    """

    @property
    def colored_name(self) -> str:
        """
        Returns the colored name of the attack for display purposes.
        """
        return f"[bold yellow]{self.name}[/]"

    def execute(
        self,
        actor: "Character",
        target: "Character",
        **kwargs: Any,
    ) -> bool:
        """Execute the action against a target character.

        Args:
            actor (Character):
                The character performing the action.
            target (Character):
                The character being targeted.
            **kwargs (Any):
                Additional parameters for action execution.

        Returns:
            bool:
                True if action executed successfully, False otherwise.

        """
        if not super().execute(actor, target, **kwargs):
            return False

        # Gather the variables for the action execution.
        variables = actor.get_expression_variables()

        return self._execute_ability(actor, target, variables)

    def _execute_ability(
        self,
        actor: "Character",
        target: "Character",
        variables: list[VarInfo],
    ) -> bool:
        """
        Abstract method to be implemented by subclasses for specific ability execution.

        Args:
            actor (Character):
                The character performing the action.
            target (Character):
                The character being targeted.
            variables (list[VarInfo]):
                The variables available for the action execution.

        Returns:
            bool:
                True if action executed successfully, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    # =========================================================================
    # TARGETING SYSTEM METHODS (SHARED BY ALL ABILITIES)
    # =========================================================================

    def is_single_target(self) -> bool:
        """Check if the ability targets a single entity.

        Returns:
            bool: True if ability targets one entity, False for multi-target.

        """
        return not self.target_expr or self.target_expr.strip() == ""


def deserialize_ability(data: dict[str, Any]) -> Any:
    """Deserialize a dictionary into a BaseAbility instance.

    Args:
        data (dict[str, Any]): The dictionary representation of the ability.

    Returns:
        BaseAbility | None: The deserialized ability instance, or None if deserialization fails.

    """
    from actions.abilities.ability_buff import AbilityBuff
    from actions.abilities.ability_debuff import AbilityDebuff
    from actions.abilities.ability_heal import AbilityHeal
    from actions.abilities.ability_offensive import AbilityOffensive

    action_type = data.get("action_type")

    if action_type == "AbilityBuff":
        return AbilityBuff(**data)
    if action_type == "AbilityDebuff":
        return AbilityDebuff(**data)
    if action_type == "AbilityHeal":
        return AbilityHeal(**data)
    if action_type == "AbilityOffensive":
        return AbilityOffensive(**data)

    return None
