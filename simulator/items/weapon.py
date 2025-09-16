from typing import Any

from actions.attacks import BaseAttack


class Weapon:
    """
    Represents a weapon that can be wielded by characters in combat.

    Weapons contain one or more attacks that can be performed, specify how many
    hands are required to wield them, and automatically prefix attack names
    with the weapon name for identification.
    """

    def __init__(
        self,
        name: str,
        description: str,
        attacks: list[BaseAttack],
        hands_required: int = 0,
    ):
        """
        Initialize a new weapon instance.

        Args:
            name (str): The name of the weapon.
            description (str): A description of the weapon.
            attacks (list[BaseAttack]): List of attacks this weapon can perform.
            hands_required (int): Number of hands required to wield this weapon. Defaults to 0.
        """
        self.name: str = name
        self.description: str = description
        self.attacks: list[BaseAttack] = attacks
        self._hands_required: int = hands_required

        # Rename the attacks to match the weapon name.
        for attack in self.attacks:
            attack.name = f"{self.name} - {attack.name}"

    # ===========================================================================
    # GENERIC METHODS
    # ===========================================================================

    def requires_hands(self) -> int:
        """Get the number of hands required to perform this attack.

        Returns:
            int: Number of hands required.
        """
        return self._hands_required > 0

    def get_required_hands(self) -> int:
        """Get the number of hands required to perform this attack.

        Returns:
            int: Number of hands required.
        """
        return self._hands_required

    # ===========================================================================
    # SERIALIZATION METHODS
    # ===========================================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the weapon to a dictionary representation.

        Returns:
            dict[str, Any]: Dictionary containing the weapon's properties including
                          class name, name, description, attacks, and hands required.
        """
        data = {
            "class": self.__class__.__name__,
            "name": self.name,
            "description": self.description,
            "attacks": [action.model_dump() for action in self.attacks],
        }
        if self.requires_hands():
            data["hands_required"] = self.get_required_hands()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Weapon":
        """
        Create a Weapon instance from a dictionary representation.

        Args:
            data (dict[str, Any]): Dictionary containing weapon properties including
                                 name, description, attacks, and hands_required.

        Returns:
            Weapon: A new Weapon instance created from the dictionary data.

        Raises:
            KeyError: If required keys are missing from the data.
        """
        from actions.attacks.base_attack import deserialze_attack

        # Load attacks using the dynamic attack factory
        attack_list = []
        for action_data in data.get("attacks", []):
            attack = deserialze_attack(action_data)
            if attack is not None:
                attack_list.append(attack)

        return Weapon(
            name=data["name"],
            description=data["description"],
            attacks=attack_list,
            hands_required=data.get("hands_required", 0),
        )
