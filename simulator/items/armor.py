"""
Armor module for the simulator.

Defines the Armor class and related types for managing armor pieces,
their properties, and effects within the combat simulator.
"""

from typing import Any, TypeAlias

from core.constants import ArmorSlot, ArmorType
from core.logging import log_debug
from effects.damage_over_time_effect import DamageOverTimeEffect
from effects.incapacitating_effect import IncapacitatingEffect
from effects.modifier_effect import ModifierEffect
from effects.trigger_effect import TriggerEffect
from pydantic import BaseModel, Field

ValidArmorEffect: TypeAlias = (
    DamageOverTimeEffect | ModifierEffect | IncapacitatingEffect | TriggerEffect
)


class Armor(BaseModel):
    """
    Represents a piece of armor that can be equipped by characters.

    Armor provides Armor Class (AC) bonuses and may have special effects.
    Different armor types (light, medium, heavy) interact differently with
    Dexterity modifiers, and armor can be equipped in different slots.
    """

    name: str = Field(
        description="The name of the armor piece.",
    )
    description: str = Field(
        description="A brief description of the armor piece.",
    )
    ac: int = Field(
        description="The base Armor Class (AC) bonus provided by this armor piece.",
        ge=0,
    )
    armor_slot: ArmorSlot = Field(
        description="The slot where this armor piece is equipped (e.g., torso, shield).",
    )
    armor_type: ArmorType = Field(
        description="The type of armor (light, medium, heavy).",
    )
    max_dex_bonus: int = Field(
        default=0,
        description=(
            "The maximum Dexterity modifier that can be applied to the AC bonus. "
            "Relevant for medium armor."
        ),
        ge=0,
    )
    effects: list[ValidArmorEffect] = Field(
        default_factory=list,
        description="An optional special effect granted by this armor piece.",
    )

    @property
    def colored_name(self) -> str:
        """Returns the armor name with ANSI color codes for terminal display."""
        return self.armor_type.colorize(self.name)

    def model_post_init(self, _: Any) -> None:
        """
        Validate the armor's properties.

        Raises:
            AssertionError: If any armor property is invalid.

        """
        assert self.name and isinstance(self.name, str), "Armor name must not be empty."
        assert self.ac >= 0, "Armor AC bonus must be a non-negative integer."
        assert isinstance(
            self.armor_slot, ArmorSlot
        ), "Armor slot must be an instance of ArmorSlot."
        assert isinstance(
            self.armor_type, ArmorType
        ), "Armor type must be an instance of ArmorType."
        assert (
            self.max_dex_bonus >= 0
        ), "Max Dexterity bonus must be a non-negative integer."

    def get_ac(self, dex_mod: int = 0) -> int:
        """
        Returns the total AC of the armor, considering the Dexterity modifier.

        Args:
            dex_mod (int): The character's Dexterity modifier. Defaults to 0.

        Returns:
            int: The total AC bonus provided by this armor piece.

        """
        if self.armor_slot == ArmorSlot.TORSO:
            if self.armor_type == ArmorType.LIGHT:
                return self.ac + dex_mod
            if self.armor_type == ArmorType.MEDIUM:
                return self.ac + min(dex_mod, self.max_dex_bonus)
            if self.armor_type == ArmorType.HEAVY:
                return self.ac
            return self.ac
        if self.armor_slot == ArmorSlot.SHIELD:
            return self.ac
        return 0

    def apply_effects(self, wearer: Any) -> None:
        """
        Applies all effects of the armor to the wearer.

        Args:
            wearer (Any):
                The entity to which the armor effects will be applied.

        """
        from character.main import Character

        if not isinstance(wearer, Character):
            raise ValueError("Wearer must be a Character instance.")

        variables = wearer.get_expression_variables()

        for effect in self.effects:
            log_debug(
                f"Applying effect {effect.colored_name} from armor {self.colored_name} to {wearer.colored_name}",
                context={"character": wearer.name, "armor": self.name, "effect": effect.name},
            )
            effect.apply_effect(wearer, wearer, variables)
