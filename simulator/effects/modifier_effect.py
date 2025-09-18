from typing import Any

from pydantic import Field, model_validator

from .base_effect import Effect, Modifier


class ModifierEffect(Effect):
    """
    Base class for effects that apply stat modifiers to characters.

    This includes buffs and debuffs that temporarily modify character attributes
    like HP, AC, damage bonuses, etc.
    """

    modifiers: list[Modifier] = Field(
        description="List of modifiers applied by this effect.",
    )

    @property
    def color(self) -> str:
        """Returns the color string for modifier effects."""
        return "bold yellow"

    @property
    def emoji(self) -> str:
        """Returns the emoji for modifier effects."""
        return "🛡️"

    @model_validator(mode="after")
    def check_modifiers(self) -> "ModifierEffect":
        """
        Ensure that the modifiers list is not empty.

        Raises:
            ValueError: If the modifiers list is empty.
        """
        if not self.modifiers:
            raise ValueError("Modifiers list cannot be empty.")
        for modifier in self.modifiers:
            if not isinstance(modifier, Modifier):
                raise ValueError(f"Invalid modifier: {modifier}")
        return self

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

    @property
    def color(self) -> str:
        """Returns the color string for buff effects."""
        return "bold cyan"

    @property
    def emoji(self) -> str:
        """Returns the emoji for buff effects."""
        return "💫"


class DebuffEffect(ModifierEffect):
    """
    Negative effect that applies detrimental modifiers to a character.

    Debuffs provide temporary penalties to character attributes such as reduced
    damage, lowered AC, or decreased HP.
    """

    @property
    def color(self) -> str:
        """Returns the color string for debuff effects."""
        return "bold red"

    @property
    def emoji(self) -> str:
        """Returns the emoji for debuff effects."""
        return "☠️"
