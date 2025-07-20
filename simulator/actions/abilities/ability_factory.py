"""
Factory function for creating ability instances from data.

This module contains the factory pattern implementation for ability creation,
allowing dynamic instantiation of different ability types based on their
category or class classification.
"""

from typing import Any

from actions.abilities.ability_buff import BuffAbility
from actions.abilities.ability_healing import HealingAbility
from actions.abilities.ability_offensive import OffensiveAbility
from actions.abilities.ability_utility import UtilityAbility
from actions.abilities.base_ability import BaseAbility
from core.constants import ActionCategory
from core.error_handling import log_critical


def from_dict_ability(data: dict[str, Any]) -> BaseAbility | None:
    """
    Factory function to create ability instances from dictionary data.
    
    This function dynamically creates the appropriate ability subclass based on
    the class field (legacy) or category field in the data dictionary. It serves
    as the entry point for deserializing ability data from JSON or other
    dictionary-based formats.
    
    Args:
        data: Dictionary containing ability configuration data with at minimum:
            - name: The ability's display name
            - type: ActionType enum value
            - class OR category: Determines ability type (legacy 'class' field supported)
            Additional fields depend on specific ability category requirements.
    
    Returns:
        BaseAbility instance of the appropriate subclass (OffensiveAbility,
        HealingAbility, BuffAbility, or UtilityAbility) based on the 
        class/category field. Returns None if not a recognized ability type.
        
    Raises:
        ValueError: If the class/category is invalid or missing required fields
        KeyError: If required data fields are missing
        
    Supported Categories:
        - OFFENSIVE: Damage-dealing abilities (OffensiveAbility)
        - HEALING: Healing abilities (HealingAbility)
        - BUFF: Beneficial effect abilities (BuffAbility)
        - UTILITY: Non-combat utility abilities (UtilityAbility)
        
    Legacy Class Support:
        - "BaseAbility": Defaults to OffensiveAbility for backward compatibility
        - "OffensiveAbility": Direct routing to OffensiveAbility
        - "HealingAbility": Direct routing to HealingAbility
        - "BuffAbility": Direct routing to BuffAbility
        - "UtilityAbility": Direct routing to UtilityAbility
        
    Example:
        >>> ability_data = {
        ...     "name": "Dragon Breath",
        ...     "type": "STANDARD",
        ...     "category": "OFFENSIVE",
        ...     "damage": [{"damage_type": "fire", "damage_roll": "3d8"}],
        ...     "cooldown": 2
        ... }
        >>> ability = from_dict_ability(ability_data)
        >>> isinstance(ability, OffensiveAbility)
        True
    """
    try:
        # Check for legacy 'class' field first, then modern 'category' field
        ability_class = data.get("class", "")
        category_str = data.get("category", "")
        
        if ability_class:
            # Legacy class-based routing
            if ability_class == "BaseAbility":
                # For backward compatibility, default to OffensiveAbility
                return OffensiveAbility.from_dict(data)
            elif ability_class == "OffensiveAbility":
                return OffensiveAbility.from_dict(data)
            elif ability_class == "HealingAbility":
                return HealingAbility.from_dict(data)
            elif ability_class == "BuffAbility":
                return BuffAbility.from_dict(data)
            elif ability_class == "UtilityAbility":
                return UtilityAbility.from_dict(data)
            else:
                # Not a recognized ability class - return None for other action types
                return None
        
        elif category_str:
            # Modern category-based routing
            try:
                category = ActionCategory[category_str]
            except KeyError:
                log_critical(
                    f"Invalid ability category: {category_str}",
                    {"category": category_str, "ability_name": data.get("name", "Unknown")}
                )
                raise ValueError(f"Invalid ability category: {category_str}")

            if category == ActionCategory.OFFENSIVE:
                return OffensiveAbility.from_dict(data)
            elif category == ActionCategory.HEALING:
                return HealingAbility.from_dict(data)
            elif category == ActionCategory.BUFF:
                return BuffAbility.from_dict(data)
            elif category == ActionCategory.UTILITY:
                return UtilityAbility.from_dict(data)
            else:
                log_critical(
                    f"Unsupported ability category: {category}",
                    {"category": category, "ability_name": data.get("name", "Unknown")}
                )
                raise ValueError(f"Unsupported ability category: {category}")
        else:
            # No class or category field - not an ability, return None
            return None

    except Exception as e:
        ability_name = data.get("name", "Unknown")
        log_critical(
            f"Error creating ability '{ability_name}': {str(e)}",
            {"ability_name": ability_name, "error": str(e)},
            e,
        )
        raise
