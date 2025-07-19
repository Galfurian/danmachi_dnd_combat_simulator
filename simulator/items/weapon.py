from typing import Any, List

from actions.attack_action import BaseAttack, from_dict_attack


class Weapon:
    def __init__(
        self,
        name: str,
        description: str,
        attacks: list[BaseAttack],
        hands_required: int = 0,
    ):
        self.name: str = name
        self.description: str = description
        self.attacks: list[BaseAttack] = attacks
        self.hands_required: int = hands_required

        # Rename the attacks to match the weapon name.
        for attack in self.attacks:
            attack.name = f"{self.name} - {attack.name}"

    def to_dict(self) -> dict[str, Any]:
        """
        Converts the Weapon instance to a dictionary.
        Returns:
            dict: Dictionary representation of the Weapon instance.
        """
        return {
            "class": self.__class__.__name__,
            "name": self.name,
            "description": self.description,
            "attacks": [action.to_dict() for action in self.attacks],
            "hands_required": self.hands_required,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Weapon":
        """Creates a Weapon instance from a dictionary.
        Args:
            data (dict): Dictionary containing the weapon data.
            base_attacks (dict): Dictionary of base attacks.
        Returns:
            Weapon: An instance of Weapon.
        """
        # Load attacks using the dynamic attack factory
        attack_list = []
        for action_data in data.get("attacks", []):
            attack = from_dict_attack(action_data)
            if attack is not None:
                attack_list.append(attack)
        
        return Weapon(
            name=data["name"],
            description=data["description"],
            attacks=attack_list,
            hands_required=data.get("hands_required", 0),
        )
