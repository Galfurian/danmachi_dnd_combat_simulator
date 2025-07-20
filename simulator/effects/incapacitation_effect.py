"""
Incapacitating effects that prevent character actions.

This module contains effect types that prevent characters from taking actions
during combat, such as Sleep, Paralyzed, Stunned, etc.
"""

from typing import Any
from effects.effect import Effect


class IncapacitatingEffect(Effect):
    """
    Effect that prevents a character from taking actions.
    
    Unlike ModifierEffect which only applies stat penalties, IncapacitatingEffect
    completely prevents the character from acting during their turn.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        max_duration: int,
        incapacitation_type: str = "general",  # "sleep", "paralyzed", "stunned", etc.
        save_ends: bool = False,
        save_dc: int = 0,
        save_stat: str = "CON",
        requires_concentration: bool = False,
    ):
        super().__init__(name, description, max_duration, requires_concentration)
        self.incapacitation_type = incapacitation_type
        self.save_ends = save_ends
        self.save_dc = save_dc
        self.save_stat = save_stat
    
    def prevents_actions(self) -> bool:
        """Check if this effect prevents the character from taking actions."""
        return True
    
    def prevents_movement(self) -> bool:
        """Check if this effect prevents movement."""
        return self.incapacitation_type in ["paralyzed", "stunned", "unconscious"]
    
    def auto_fails_saves(self) -> bool:
        """Check if character automatically fails certain saves."""
        return self.incapacitation_type in ["unconscious"]
    
    def can_apply(self, actor: Any, target: Any) -> bool:
        """Incapacitating effects can be applied to any living target."""
        return target.is_alive()
    
    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update({
            "incapacitation_type": self.incapacitation_type,
            "save_ends": self.save_ends,
            "save_dc": self.save_dc,
            "save_stat": self.save_stat,
        })
        return data
    
    @staticmethod
    def from_dict(data: dict[str, Any]) -> "IncapacitatingEffect":
        return IncapacitatingEffect(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            incapacitation_type=data.get("incapacitation_type", "general"),
            save_ends=data.get("save_ends", False),
            save_dc=data.get("save_dc", 0),
            save_stat=data.get("save_stat", "CON"),
            requires_concentration=data.get("requires_concentration", False),
        )
