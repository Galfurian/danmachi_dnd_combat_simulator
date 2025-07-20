from typing import Any

from .base_attack import BaseAttack
from .weapon_attack import WeaponAttack
from .natural_attack import NaturalAttack


def from_dict_attack(data: dict[str, Any]) -> BaseAttack | None:
    """
    Creates a BaseAttack instance from a dictionary using the factory pattern.

    This factory function automatically determines the correct attack class
    based on the 'class' field in the data dictionary and creates an
    appropriate instance. This enables polymorphic loading of different
    attack types from configuration files.

    Supported Attack Classes:
        - "BaseAttack": Generic attack (default)
        - "WeaponAttack": Equipable weapon attacks
        - "NaturalAttack": Biological/innate attacks

    Args:
        data: Dictionary containing attack specification with 'class' field

    Returns:
        BaseAttack | None: Appropriate attack subclass instance, or None if
                          class is not recognized

    Dictionary Requirements:
        - Must contain a 'class' field specifying the attack type
        - Must contain all required fields for the specified class
        - Field names must match the class constructor parameters

    Example:
        ```python
        # Load different attack types polymorphically
        weapon_data = {"class": "WeaponAttack", "name": "Sword", ...}
        natural_data = {"class": "NaturalAttack", "name": "Claws", ...}

        sword = from_dict_attack(weapon_data)    # Returns WeaponAttack
        claws = from_dict_attack(natural_data)   # Returns NaturalAttack
        ```

    Error Handling:
        Returns None for unrecognized class names rather than raising
        exceptions, allowing graceful handling of invalid data.
    """
    attack_class = data.get("class", "BaseAttack")

    if attack_class == "WeaponAttack":
        return WeaponAttack.from_dict(data)
    elif attack_class == "NaturalAttack":
        return NaturalAttack.from_dict(data)
    elif attack_class == "BaseAttack":
        return BaseAttack.from_dict(data)

    return None
