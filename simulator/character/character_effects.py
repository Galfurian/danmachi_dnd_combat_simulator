"""
Character effects module for the simulator.

Manages the application, tracking, and resolution of effects on characters,
including bonuses, penalties, status conditions, and temporary modifications.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from combat.damage import DamageComponent
from core.constants import BonusType, DamageType
from core.dice_parser import VarInfo, get_max_roll
from core.logging import log_debug, log_error
from core.utils import cprint
from effects.base_effect import ActiveEffect, Effect, EventResponse
from effects.damage_over_time_effect import (
    ActiveDamageOverTimeEffect,
    DamageOverTimeEffect,
)
from effects.event_system import DamageTakenEvent, EventType, HitEvent
from effects.healing_over_time_effect import (
    ActiveHealingOverTimeEffect,
    HealingOverTimeEffect,
)
from effects.incapacitating_effect import (
    ActiveIncapacitatingEffect,
    IncapacitatingEffect,
)
from effects.modifier_effect import ActiveModifierEffect, ModifierEffect
from effects.trigger_effect import ActiveTriggerEffect, TriggerEffect

ValidPassiveEffect = (
    DamageOverTimeEffect | ModifierEffect | IncapacitatingEffect | TriggerEffect
)


class CharacterEffects:
    """
    Manages all effects (active, passive, modifiers, triggers) for a character,
    including application, removal, and effect updates.

    Attributes:
        _owner (Any):
            The character that owns this effects module.
        active_effects (list[ActiveEffect]):
            List of currently active effects on the character.
        passive_effects (list[ActiveEffect]):
            List of passive effects that are always active.

    """

    _owner: Any
    active_effects: list[ActiveEffect]
    passive_effects: list[ActiveEffect]

    def __init__(self, owner: Any) -> None:
        """
        Initialize the CharacterEffects module.

        Args:
            owner (Any):
                The character that owns this effects module.

        """
        super().__init__()
        self._owner = owner
        self.active_effects: list[ActiveEffect] = []
        # TODO: Properly populate this one.
        self.passive_effects: list[ActiveEffect] = []

    # === Effect Management ===

    def on_event(self, event: Any) -> list[EventResponse]:
        """
        Handle effects that should trigger or break on generic events.

        Args:
            event (Any):
                The event to handle.

        Returns:
            list[EventResponse]:
                Responses from effects that were broken or triggered.
        """
        responses: list[EventResponse] = []
        effects_to_remove: list[ActiveEffect] = []
        for ae in self.active_effects:
            response = ae.on_event(event)
            if response:
                if response.remove_effect:
                    effects_to_remove.append(ae)
                responses.append(response)
        # Remove the effects that should break.
        for effect_to_remove in effects_to_remove:
            self.remove_effect(effect_to_remove)
        return responses

    def remove_effect(self, effect: ActiveEffect) -> bool:
        """
        Remove an active effect from the character.

        Args:
            effect (ActiveEffect):
                The effect to remove.

        Returns:
            bool:
                True if the effect was removed successfully, False otherwise.

        """
        if effect in self.active_effects:
            self.active_effects.remove(effect)
            return True
        return False

    # === Passive Effect Management ===

    def add_passive_effect(
        self,
        effect: Effect,
        variables: list[VarInfo] = [],
    ) -> bool:
        """
        Add a passive effect that is always active (like boss phase triggers).

        Args:
            effect (Effect):
                The passive effect to add.

        Returns:
            bool:
                True if the passive effect was added, False if it was already
                present.

        """
        from effects.base_effect import ActiveEffect

        # If the effect is already present, do not add it again.
        if effect in [ae.effect for ae in self.passive_effects]:
            return False

        # Use provided variables or get default ones from the owner.
        variables = variables or self._owner.get_expression_variables()

        # Build the ActiveEffect for the passive effect.
        passive_ae = ActiveEffect(
            source=self._owner,
            target=self._owner,
            effect=effect,
            duration=None,
            variables=variables,
        )
        # Add the passive effect to the list.
        self.passive_effects.append(passive_ae)

        return True

    def remove_passive_effect(self, effect: Effect) -> bool:
        """
        Remove a passive effect.

        Args:
            effect (Effect): The passive effect to remove.

        Returns:
            bool: True if the passive effect was removed, False otherwise.

        """
        for ae in self.passive_effects:
            if ae.effect == effect:
                self.passive_effects.remove(ae)
                return True
        return False

    # === Regular Effect Management ===

    def get_effect_remaining_duration(self, effect: Effect) -> int | None:
        """
        Get the remaining duration of a specific effect.

        Args:
            effect (Effect):
                The effect to check.

        Returns:
            int | None:
                The remaining duration of the effect, None for indefinite
                effects, or 0 if not active.

        """
        for ae in self.active_effects:
            if ae.effect == effect:
                return ae.duration
        return 0

    # === Modifier Management ===

    def get_base_modifier(self, bonus_type: BonusType) -> list[str]:

        assert (
            bonus_type != BonusType.DAMAGE
        ), "Use get_damage_modifier for DAMAGE type."

        @dataclass
        class Entry:
            value: str
            score: int

        # Collect all modifiers for this bonus type
        modifiers: list[Entry] = []
        has_non_stacking = False
        for effect in self.modifier_effects:
            for mod in effect.modifier_effect.modifiers:
                if mod.bonus_type != bonus_type:
                    continue
                if isinstance(mod.value, DamageComponent):
                    continue
                if not mod.stacks:
                    has_non_stacking = True
                # Compute the projected strength with current variables.
                new_entry = Entry(
                    value=mod.value,
                    score=mod.get_projected_strength(effect.variables),
                )
                # If the score is zero, skip adding this modifier.
                if new_entry.score == 0:
                    continue
                # If there is already one with the same value, keep the one with
                # the higher score, but only for those modifiers where we keep
                # only the strongest.
                existing = next((e for e in modifiers if e.value == mod.value), None)
                if existing:
                    if new_entry.score > existing.score:
                        existing.value = new_entry.value
                        existing.score = new_entry.score
                    continue
                # Otherwise, add the new modifier.
                modifiers.append(new_entry)

        if has_non_stacking:
            # For non-stacking, find the strongest modifier
            if modifiers:
                best = max(modifiers, key=lambda e: e.score)
                return [best.value]
            return []
        # Stacking: return all
        return [m.value for m in modifiers]

    def get_damage_modifier(self) -> list[DamageComponent]:
        """
        Get the modifier value for a specific bonus type.

        Args:
            bonus_type (BonusType):
                The type of bonus to retrieve.

        Returns:
            list[str | DamageComponent]:
                List of modifier values for the specified bonus type.

        """

        @dataclass
        class Entry:
            value: DamageComponent
            score: int

        # Collect all modifiers for this bonus type
        modifiers: list[Entry] = []
        has_non_stacking = False
        for effect in self.modifier_effects:
            for mod in effect.modifier_effect.modifiers:
                if mod.bonus_type != BonusType.DAMAGE:
                    continue
                if isinstance(mod.value, str):
                    continue
                if not mod.stacks:
                    has_non_stacking = True
                # Compute the projected strength with current variables.
                new_entry = Entry(
                    value=mod.value,
                    score=mod.get_projected_strength(effect.variables),
                )
                # If the score is zero, skip adding this modifier.
                if new_entry.score == 0:
                    continue
                # If there is already one with the same value, keep the one with
                # the higher score, but only for those modifiers where we keep
                # only the strongest.
                existing = next((e for e in modifiers if e.value == mod.value), None)
                if existing:
                    if new_entry.score > existing.score:
                        existing.value = new_entry.value
                        existing.score = new_entry.score
                    continue
                # Otherwise, add the new modifier.
                modifiers.append(new_entry)

        if has_non_stacking:
            # For non-stacking, find the strongest modifier
            if modifiers:
                best = max(modifiers, key=lambda e: e.score)
                return [best.value]
            return []
        # Stacking: return all
        return [m.value for m in modifiers]

    # === Helpers ===

    @property
    def damage_over_time_effects(self) -> Iterator[ActiveDamageOverTimeEffect]:
        """
        Get all active damage over time effects.

        Returns:
            Iterator[ActiveDamageOverTimeEffect]:
                An iterator over active damage over time effects.

        """
        for ae in self.active_effects:
            if isinstance(ae, ActiveDamageOverTimeEffect):
                yield ae

    @property
    def healing_over_time_effects(self) -> Iterator[ActiveHealingOverTimeEffect]:
        """
        Get all active healing over time effects.

        Returns:
            Iterator[ActiveHealingOverTimeEffect]:
                An iterator over active healing over time effects.

        """
        for ae in self.active_effects:
            if isinstance(ae, ActiveHealingOverTimeEffect):
                yield ae

    @property
    def incapacitating_effects(self) -> Iterator[ActiveIncapacitatingEffect]:
        """
        Get all active incapacitating effects.

        Returns:
            Iterator[ActiveIncapacitatingEffect]:
                An iterator over active incapacitating effects.

        """
        for ae in self.active_effects:
            if isinstance(ae, ActiveIncapacitatingEffect):
                yield ae

    @property
    def modifier_effects(self) -> Iterator[ActiveModifierEffect]:
        """
        Get all active modifier effects.

        Returns:
            Iterator[ActiveModifierEffect]:
                An iterator over active modifier effects.

        """
        for ae in self.active_effects:
            if isinstance(ae, ActiveModifierEffect):
                yield ae

    @property
    def trigger_effects(self) -> Iterator[ActiveTriggerEffect]:
        """
        Get all active trigger effects.

        Returns:
            Iterator[ActiveTriggerEffect]:
                An iterator over active trigger effects.

        """
        for ae in self.active_effects:
            if isinstance(ae, ActiveTriggerEffect):
                yield ae
