"""
Factory pattern implementation for spell creation and serialization.

This module provides centralized factory classes for creating and serializing
spell instances, maintaining clean separation of concerns by removing
serialization logic from individual spell classes.
"""

from typing import Any

from actions.spells.base_spell import Spell
from actions.spells.spell_attack import SpellAttack
from actions.spells.spell_buff import SpellBuff
from actions.spells.spell_debuff import SpellDebuff
from actions.spells.spell_heal import SpellHeal
from core.constants import ActionType
from core.error_handling import log_critical
from combat.damage import DamageComponent
from effects.effect import Effect


class SpellDeserializer:
    """Factory for creating spell instances from dictionary data."""

    @staticmethod
    def deserialize(data: dict[str, Any]) -> Any | None:
        """
        Deserialize spell data from dictionary to appropriate spell instance.

        This method dynamically creates the correct spell subclass based on
        the 'class' field in the data dictionary.

        Args:
            data: Dictionary containing spell configuration data.

        Returns:
            Spell instance of the appropriate subclass, or None if not recognized.
        """
        try:
            spell_class = data.get("class", "")

            if spell_class == "SpellAttack":
                return SpellDeserializer._deserialize_spell_attack(data)
            elif spell_class == "SpellBuff":
                return SpellDeserializer._deserialize_spell_buff(data)
            elif spell_class == "SpellDebuff":
                return SpellDeserializer._deserialize_spell_debuff(data)
            elif spell_class == "SpellHeal":
                return SpellDeserializer._deserialize_spell_heal(data)
            else:
                # Not a recognized spell class - return None for other action types
                return None
        except Exception as e:
            spell_name = data.get("name", "Unknown")
            log_critical(
                f"Error creating spell '{spell_name}': {str(e)}",
                {"spell_name": spell_name, "error": str(e)},
                e,
            )
            raise

    @staticmethod
    def _deserialize_spell_attack(data: dict[str, Any]) -> SpellAttack:
        """Create SpellAttack from dictionary data."""
        return SpellAttack(
            name=data["name"],
            type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            level=data["level"],
            mind_cost=data["mind_cost"],
            damage=[
                DamageComponent.from_dict(component) for component in data["damage"]
            ],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
            target_expr=data.get("target_expr", ""),
            requires_concentration=data.get("requires_concentration", False),
            target_restrictions=data.get("target_restrictions"),
        )

    @staticmethod
    def _deserialize_spell_buff(data: dict[str, Any]) -> SpellBuff:
        """Create SpellBuff from dictionary data."""
        return SpellBuff(
            name=data["name"],
            type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            level=data["level"],
            mind_cost=data["mind_cost"],
            effect=Effect.from_dict(data["effect"]),
            target_expr=data.get("target_expr", ""),
            requires_concentration=data.get("requires_concentration", False),
            target_restrictions=data.get("target_restrictions", []),
        )

    @staticmethod
    def _deserialize_spell_debuff(data: dict[str, Any]) -> SpellDebuff:
        """Create SpellDebuff from dictionary data."""
        return SpellDebuff(
            name=data["name"],
            type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            level=data["level"],
            mind_cost=data["mind_cost"],
            effect=Effect.from_dict(data["effect"]),
            target_expr=data.get("target_expr", ""),
            requires_concentration=data.get("requires_concentration", False),
            target_restrictions=data.get("target_restrictions", []),
        )

    @staticmethod
    def _deserialize_spell_heal(data: dict[str, Any]) -> SpellHeal:
        """Create SpellHeal from dictionary data."""
        return SpellHeal(
            name=data["name"],
            type=ActionType[data["type"]],
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            level=data["level"],
            mind_cost=data["mind_cost"],
            heal_roll=data["heal_roll"],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
            target_expr=data.get("target_expr", ""),
            requires_concentration=data.get("requires_concentration", False),
            target_restrictions=data.get("target_restrictions", []),
        )


class SpellSerializer:
    """Serializer for converting spell instances to dictionary format."""

    @staticmethod
    def serialize(spell: Spell) -> dict[str, Any]:
        """
        Serialize spell instance to dictionary format.

        This method handles common fields for all spell types and delegates
        specific serialization to the appropriate subclass methods.

        Args:
            spell: The spell instance to serialize.

        Returns:
            dict: Dictionary representation of the spell.
        """
        if isinstance(spell, SpellAttack):
            return SpellSerializer._serialize_spell_attack(spell)
        elif isinstance(spell, SpellBuff):
            return SpellSerializer._serialize_spell_buff(spell)
        elif isinstance(spell, SpellDebuff):
            return SpellSerializer._serialize_spell_debuff(spell)
        elif isinstance(spell, SpellHeal):
            return SpellSerializer._serialize_spell_heal(spell)
        else:
            raise ValueError(f"Unsupported spell type: {type(spell)}")

    @staticmethod
    def _serialize_base_spell(spell: Spell) -> dict[str, Any]:
        """Serialize common BaseSpell fields."""
        data = {
            "name": spell.name,
            "type": spell.type.name,
            "description": spell.description,
            "cooldown": spell.cooldown,
            "maximum_uses": spell.maximum_uses,
            "level": spell.level,
            "mind_cost": spell.mind_cost,
            "requires_concentration": spell.requires_concentration,
        }

        if spell.target_expr:
            data["target_expr"] = spell.target_expr

        return data

    @staticmethod
    def _serialize_spell_attack(spell: SpellAttack) -> dict[str, Any]:
        """Serialize SpellAttack to dictionary."""
        data = SpellSerializer._serialize_base_spell(spell)
        data["damage"] = [component.to_dict() for component in spell.damage]

        if spell.effect:
            data["effect"] = spell.effect.to_dict()

        return data

    @staticmethod
    def _serialize_spell_buff(spell: SpellBuff) -> dict[str, Any]:
        """Serialize SpellBuff to dictionary."""
        data = SpellSerializer._serialize_base_spell(spell)
        data["effect"] = spell.effect.to_dict()
        return data

    @staticmethod
    def _serialize_spell_debuff(spell: SpellDebuff) -> dict[str, Any]:
        """Serialize SpellDebuff to dictionary."""
        data = SpellSerializer._serialize_base_spell(spell)
        data["effect"] = spell.effect.to_dict()
        return data

    @staticmethod
    def _serialize_spell_heal(spell: SpellHeal) -> dict[str, Any]:
        """Serialize SpellHeal to dictionary."""
        data = SpellSerializer._serialize_base_spell(spell)
        data["heal_roll"] = spell.heal_roll

        if spell.effect:
            data["effect"] = spell.effect.to_dict()

        return data
