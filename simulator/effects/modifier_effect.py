from typing import Any

from .base_effect import Effect, Modifier


class ModifierEffect(Effect):
    """
    Base class for effects that apply stat modifiers to characters.

    This includes buffs and debuffs that temporarily modify character attributes
    like HP, AC, damage bonuses, etc.
    """

    def __init__(
        self,
        name: str,
        description: str,
        duration: int | None,
        modifiers: list[Modifier],
    ):
        super().__init__(name, description, duration)
        self.modifiers: list[Modifier] = modifiers
        self.validate()

    def validate(self) -> None:
        """
        Validate the modifier effect's properties.

        Raises:
            AssertionError: If validation conditions are not met.
        """
        super().validate()
        assert isinstance(self.modifiers, list), "Modifiers must be a list."
        for modifier in self.modifiers:
            assert isinstance(
                modifier, Modifier
            ), f"Modifier '{modifier}' must be of type Modifier."

    def can_apply(self, actor: Any, target: Any) -> bool:
        """
        Check if the modifier effect can be applied to the target.

        Args:
            actor (Any): The character applying the effect.
            target (Any): The character receiving the effect.

        Returns:
            bool: True if the effect can be applied, False otherwise.
        """
        if not target.is_alive():
            return False
        # Check if the target is already affected by the same modifiers.
        for modifier in self.modifiers:
            existing_modifiers = target.effects_module.get_modifier(modifier.bonus_type)
            if not existing_modifiers:
                continue
            # Check if the target already has this exact modifier
            if modifier in existing_modifiers:
                return False
        return True


class BuffEffect(ModifierEffect):
    """
    Positive effect that applies beneficial modifiers to a character.

    Buffs provide temporary bonuses to character attributes such as increased
    damage, improved AC, or additional HP.
    """

    def __init__(
        self,
        name: str,
        description: str,
        duration: int | None,
        modifiers: list[Modifier],
    ):
        super().__init__(name, description, duration, modifiers)


class DebuffEffect(ModifierEffect):
    """
    Negative effect that applies detrimental modifiers to a character.

    Debuffs provide temporary penalties to character attributes such as reduced
    damage, lowered AC, or decreased HP.
    """

    def __init__(
        self,
        name: str,
        description: str,
        duration: int | None,
        modifiers: list[Modifier],
    ):
        super().__init__(name, description, duration, modifiers)
