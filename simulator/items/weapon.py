from actions.attack_action import *


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
        return Weapon(
            name=data["name"],
            description=data["description"],
            attacks=[
                BaseAttack.from_dict(action_data)
                for action_data in data.get("attacks", [])
            ],
            hands_required=data.get("hands_required", 0),
        )
