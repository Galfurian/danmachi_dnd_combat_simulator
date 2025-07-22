"""
Factory function for creating spell instances from data.

This module contains the factory pattern implementation for spell creation,
allowing dynamic instantiation of different spell types based on their
category classification.
"""

from typing import Any

from actions.spells.spell_attack import SpellAttack
from actions.spells.spell_buff import SpellBuff
from actions.spells.spell_debuff import SpellDebuff
from actions.spells.spell_heal import SpellHeal
from core.constants import ActionCategory, ActionType
from core.error_handling import log_critical


def from_dict_spell(data: dict[str, Any]) -> Any:
    """
    Factory function to create spell instances from dictionary data.
    
    This function dynamically creates the appropriate spell subclass based on
    the class field (legacy) or category field in the data dictionary. It serves
    as the entry point for deserializing spell data from JSON or other
    dictionary-based formats.
    
    Args:
        data: Dictionary containing spell configuration data with at minimum:
            - name: The spell's display name
            - type: ActionType enum value
            - level: Spell level (1-10)
            - mind_cost: List of mind costs per level
            - class OR category: Determines spell type (legacy 'class' field supported)
            Additional fields depend on specific spell category requirements.
    
    Returns:
        Spell instance of the appropriate subclass (SpellAttack, SpellHeal,
        SpellBuff, or SpellDebuff) based on the class/category field.
        
    Raises:
        ValueError: If the class/category is invalid or missing required fields
        KeyError: If required data fields are missing
    """
    try:
        # Check for legacy 'class' field first, then modern 'category' field
        spell_class = data.get("class", "")
        category_str = data.get("category", "")
        
        if spell_class:
            # Legacy class-based routing
            if spell_class == "SpellAttack":
                return SpellAttack.from_dict(data)
            elif spell_class == "SpellHeal":
                return SpellHeal.from_dict(data)
            elif spell_class == "SpellBuff":
                return SpellBuff.from_dict(data)
            elif spell_class == "SpellDebuff":
                return SpellDebuff.from_dict(data)
            else:
                # Not a spell class - return None for other action types
                return None
        
        elif category_str:
            # Modern category-based routing
            try:
                category = ActionCategory[category_str]
            except KeyError:
                log_critical(
                    f"Invalid spell category: {category_str}",
                    {"category": category_str, "spell_name": data.get("name", "Unknown")}
                )
                raise ValueError(f"Invalid spell category: {category_str}")

            if category == ActionCategory.OFFENSIVE:
                return SpellAttack.from_dict(data)
            elif category == ActionCategory.HEALING:
                return SpellHeal.from_dict(data)
            elif category == ActionCategory.BUFF:
                return SpellBuff.from_dict(data)
            elif category == ActionCategory.DEBUFF:
                return SpellDebuff.from_dict(data)
            else:
                log_critical(
                    f"Unsupported spell category: {category}",
                    {"category": category, "spell_name": data.get("name", "Unknown")}
                )
                raise ValueError(f"Unsupported spell category: {category}")
        else:
            # No class or category field - not a spell, return None
            return None

    except Exception as e:
        spell_name = data.get("name", "Unknown")
        log_critical(
            f"Error creating spell '{spell_name}': {str(e)}",
            {"spell_name": spell_name, "error": str(e)},
            e,
        )
        raise
