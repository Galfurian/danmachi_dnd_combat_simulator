from typing import Any


class CharacterClassAction:
    """
    Represents an action available to a character class, including prerequisites and default status.
    """

    def __init__(
        self, action: str, is_default: bool = False, prerequisites: list[str] = []
    ) -> None:
        """
        Initializes a CharacterClassAction instance.

        Args:
            action (str): The action associated with this character class action.
            is_default (bool, optional): Whether this action is given by default. Defaults to False.
            prerequisites (list[str], optional): The pre-required actions to acquire this action, if any. Defaults to an empty list.
        """
        self.action: str = action
        self.is_default: bool = is_default
        self.prerequisites: list[str] = prerequisites

    def has_prerequisite(self, known_actions: list[str]) -> bool:
        """
        Checks if the action has any prerequisites that are not met.

        Args:
            known_actions (list[str]): A list of actions that the character already knows.

        Returns:
            bool: True if all prerequisites are met, False otherwise.
        """
        return all(prerequisite in known_actions for prerequisite in self.prerequisites)

    def to_dict(self) -> dict[str, Any]:
        """
        Converts the CharacterClassAction instance to a dictionary.

        Returns:
            dict[str, Any]: The dictionary representation of the CharacterClassAction instance.
        """
        return {
            "action": self.action,
            "is_default": self.is_default,
            "prerequisites": self.prerequisites,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "CharacterClassAction":
        """
        Creates a CharacterClassAction instance from a dictionary.

        Args:
            data (dict[str, Any]): The dictionary containing action data.

        Returns:
            CharacterClassAction: An instance of CharacterClassAction.
        """
        return CharacterClassAction(
            action=data["action"],
            is_default=data.get("is_default", False),
            prerequisites=data.get("prerequisites", []),
        )


class CharacterClass:
    """
    Represents a character class with its properties and available actions per level.
    """

    def __init__(
        self,
        name: str,
        hp_mult: int,
        mind_mult: int,
        levels: dict[str, list[CharacterClassAction]] = {},
    ) -> None:
        """
        Initializes a CharacterClass instance.

        Args:
            name (str): The name of the character class.
            hp_mult (int): The HP multiplier for this character class.
            mind_mult (int): The mind multiplier for this character class.
            levels (dict[str, list[CharacterClassAction]], optional): A dictionary mapping level strings to lists of available actions. Defaults to an empty dictionary.
        """
        self.name: str = name
        self.hp_mult: int = hp_mult
        self.mind_mult: int = mind_mult
        self.levels: dict[str, list[CharacterClassAction]] = levels

    def get_actions_at_level(
        self,
        level: int,
        known_action_names: list[str] = [],
        include_non_default: bool = False,
    ) -> list[str]:
        """
        Returns the actions available at a specific level.

        Args:
            level (int): The level for which to retrieve actions.
            known_action_names (list[str]): The list of known action names.
            include_non_default (bool, optional): Whether to include non-default actions. Defaults to False.

        Returns:
            list[str]: A list of action names available at the specified level.
        """
        # Load the actions from the content repository.
        actions: list[str] = []
        for class_action in self.levels.get(str(level), []):
            # Check if the action is a prerequisite for any known action
            if class_action.has_prerequisite(known_action_names):
                # If the action is a default action, add it to the list.
                if class_action.is_default or include_non_default:
                    actions.append(class_action.action)
        return actions

    def to_dict(self) -> dict[str, Any]:
        """
        Converts the CharacterClass instance to a dictionary.

        Returns:
            dict[str, Any]: The dictionary representation of the CharacterClass instance.
        """
        return {
            "name": self.name,
            "hp_mult": self.hp_mult,
            "mind_mult": self.mind_mult,
            "levels": {
                level: [action.to_dict() for action in actions]
                for level, actions in self.levels.items()
            },
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "CharacterClass":
        """
        Creates a CharacterClass instance from a dictionary.

        Args:
            data (dict[str, Any]): The dictionary containing character class data with keys 'name', 'hp_mult', 'mind_mult', and 'levels'.

        Returns:
            CharacterClass: An instance of CharacterClass created from the provided dictionary data.
        """
        return CharacterClass(
            name=data["name"],
            hp_mult=data.get("hp_mult", 0),
            mind_mult=data.get("mind_mult", 0),
            levels={
                level: [CharacterClassAction.from_dict(action) for action in actions]
                for level, actions in data.get("levels", {}).items()
            },
        )
