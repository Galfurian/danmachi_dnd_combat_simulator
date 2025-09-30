"""
Character effects module for the simulator.

Manages the application, tracking, and resolution of effects on characters,
including bonuses, penalties, status conditions, and temporary modifications.
"""

# Revised effects_module.py (per-BonusType tracking, 5e-style strict)

from collections.abc import Iterator
from typing import Any

from combat.damage import DamageComponent
from core.constants import BonusType, DamageType
from core.dice_parser import VarInfo, get_max_roll
from core.logging import log_error
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
        owner (Any):
            The character that owns this effects module.
        active_effects (list[ActiveEffect]):
            List of currently active effects on the character.
        passive_effects (list[ActiveEffect]):
            List of passive effects that are always active.
        active_modifiers (dict[BonusType, ActiveEffect]):
            Dictionary mapping bonus types to their active modifier effects.

    """

    def __init__(self, owner: Any) -> None:
        """
        Initialize the CharacterEffects module.

        Args:
            owner (Any):
                The character that owns this effects module.

        """
        super().__init__()
        self.owner = owner
        self.active_effects: list[ActiveEffect] = []
        self.passive_effects: list[ActiveEffect] = []
        self.active_modifiers: dict[BonusType, ActiveEffect] = {}

    # === Effect Management ===

    def add_effect(
        self,
        source: Any,
        effect: Effect,
        variables: list[VarInfo] = [],
    ) -> bool:
        """
        Add a new effect to the character.

        Args:
            source (Any):
                The source of the effect (e.g., the caster).
            effect (Effect):
                The effect to add.
            variables (list[VarInfo]):
                The variables associated with the effect.

        Returns:
            bool:
                True if the effect was added successfully, False otherwise.

        """
        assert all(isinstance(v, VarInfo) for v in variables)

        if isinstance(effect, HealingOverTimeEffect):
            return self._add_healing_over_time_effect(source, effect, variables)
        if isinstance(effect, DamageOverTimeEffect):
            return self._add_damage_over_time_effect(source, effect, variables)
        if isinstance(effect, IncapacitatingEffect):
            return self._add_incapacitating_effect(source, effect, variables)
        if isinstance(effect, ModifierEffect):
            return self._add_modifier_effect(source, effect, variables)
        if isinstance(effect, TriggerEffect):
            return self._add_trigger_effect(source, effect, variables)

        log_error(
            f"Effect type {type(effect)} not recognized for adding to character.",
            {
                "source": source.name if hasattr(source, "name") else str(source),
                "effect": effect.name,
                "variables": variables,
            },
        )

        return False

    def _add_healing_over_time_effect(
        self,
        source: Any,
        effect: HealingOverTimeEffect,
        variables: list[VarInfo] = [],
    ) -> bool:
        """
        Add a new healing over time effect to the character.

        Args:
            source (Any):
                The source of the effect (e.g., the caster).
            effect (HealingOverTimeEffect):
                The healing over time effect to add.
            variables (list[VarInfo]):
                The variables associated with the effect.

        Returns:
            bool:
                True if the healing over time effect was added successfully,
                False otherwise.

        """
        assert all(isinstance(v, VarInfo) for v in variables)

        # Basic validation.
        if self.has_effect(effect):
            return False

        self.active_effects.append(
            ActiveHealingOverTimeEffect(
                source=source,
                target=self.owner,
                effect=effect,
                duration=effect.duration,
                variables=variables,
            )
        )
        return True

    def _add_damage_over_time_effect(
        self,
        source: Any,
        effect: DamageOverTimeEffect,
        variables: list[VarInfo] = [],
    ) -> bool:
        """
        Add a new damage over time effect to the character.

        Args:
            source (Any):
                The source of the effect (e.g., the caster).
            effect (DamageOverTimeEffect):
                The damage over time effect to add.
            variables (list[VarInfo]):
                The variables associated with the effect.

        Returns:
            bool:
                True if the damage over time effect was added successfully,
                False otherwise.

        """
        assert all(isinstance(v, VarInfo) for v in variables)

        # Basic validation.
        if self.has_effect(effect):
            return False

        self.active_effects.append(
            ActiveDamageOverTimeEffect(
                source=source,
                target=self.owner,
                effect=effect,
                duration=effect.duration,
                variables=variables,
            )
        )
        return True

    def _add_incapacitating_effect(
        self,
        source: Any,
        effect: IncapacitatingEffect,
        variables: list[VarInfo] = [],
    ) -> bool:
        """
        Add a new incapacitating effect to the character.

        Args:
            source (Any):
                The source of the effect (e.g., the caster).
            effect (IncapacitatingEffect):
                The incapacitating effect to add.
            variables (list[VarInfo]):
                The variables associated with the effect.

        Returns:
            bool:
                True if the incapacitating effect was added successfully, False otherwise.

        """
        assert all(isinstance(v, VarInfo) for v in variables)

        # Basic validation.
        if self.has_effect(effect):
            return False

        existing_incap = [
            ae
            for ae in self.incapacitating_effects
            if ae.incapacitating_effect.incapacitation_type
            == effect.incapacitation_type
        ]

        for existing in existing_incap:
            self.remove_effect(existing)
            cprint(f"    ⚠️  {effect.name} replaces {existing.effect.name}.")

        self.active_effects.append(
            ActiveIncapacitatingEffect(
                source=source,
                target=self.owner,
                effect=effect,
                duration=effect.duration,
                variables=variables,
            )
        )
        return True

    def _add_modifier_effect(
        self,
        source: Any,
        effect: ModifierEffect,
        variables: list[VarInfo] = [],
    ) -> bool:
        """
        Add a new modifier effect to the character.

        Args:
            source (Any):
                The source of the effect (e.g., the caster).
            effect (ModifierEffect):
                The modifier effect to add.
            variables (list[VarInfo]):
                The variables associated with the effect.

        Returns:
            bool:
                True if the modifier effect was added successfully, False otherwise.

        """
        assert all(isinstance(v, VarInfo) for v in variables)

        # Basic validation.
        if self.has_effect(effect):
            cprint(f"    ⚠️  {effect.name} not applied; already active.")
            return False

        new_effect = ActiveModifierEffect(
            source=source,
            target=self.owner,
            effect=effect,
            duration=effect.duration,
            variables=variables,
        )

        for modifier in effect.modifiers:
            bonus_type = modifier.bonus_type
            existing = self.active_modifiers.get(bonus_type)
            if existing:
                new_strength = self._get_modifier_strength(new_effect, bonus_type)
                existing_strength = self._get_modifier_strength(existing, bonus_type)
                if new_strength <= existing_strength:
                    cprint(
                        f"    ⚠️  {effect.name} not applied; existing "
                        f"{existing.effect.name} is stronger."
                    )
                    continue
                cprint(f"    ⚠️  {effect.name} replaces {existing.effect.name}.")
                self.remove_effect(existing)
            self.active_modifiers[bonus_type] = new_effect

        self.active_effects.append(new_effect)
        return True

    def _add_trigger_effect(
        self,
        source: Any,
        effect: TriggerEffect,
        variables: list[VarInfo] = [],
    ) -> bool:
        """
        Add a new trigger effect to the character.

        Args:
            source (Any):
                The source of the effect (e.g., the caster).
            effect (TriggerEffect):
                The trigger effect to add.
            variables (list[VarInfo]):
                The variables associated with the effect.

        Returns:
            bool:
                True if the trigger effect was added successfully, False otherwise.

        """
        assert all(isinstance(v, VarInfo) for v in variables)

        # Basic validation.
        if self.has_effect(effect):
            return False

        # Only allow one OnHit trigger spell at a time.
        if effect.is_type(EventType.ON_HIT):
            existing_triggers = [
                ae
                for ae in self.trigger_effects
                if ae.trigger_effect.is_type(EventType.ON_HIT)
            ]
            # Remove any existing OnHit trigger effects first.
            for existing_trigger in existing_triggers:
                self.active_effects.remove(existing_trigger)
                cprint(f"    ⚠️  {effect.name} replaces {existing_trigger.effect.name}.")

        # Actually add the trigger effect now.
        self.active_effects.append(
            ActiveTriggerEffect(
                source=source,
                target=self.owner,
                effect=effect,
                duration=effect.duration,
                variables=variables,
                cooldown_remaining=0,
            )
        )

        return True

    def on_hit(self, event: HitEvent) -> list[EventResponse]:
        """
        Handle effects that should trigger or break when a hit occurs.

        Args:
            event (HitEvent):
                The hit event.

        Returns:
            list[EventResponse]:
                Responses from effects that were broken or triggered.

        """
        responses: list[EventResponse] = []
        effects_to_remove: list[ActiveEffect] = []
        for ae in self.incapacitating_effects:
            response = ae.on_hit(event)
            if response:
                if response.remove_effect:
                    effects_to_remove.append(ae)
                responses.append(response)

        # Remove the effects that should break.
        for effect_to_remove in effects_to_remove:
            self.remove_effect(effect_to_remove)

        return responses

    def on_damage_taken(self, event: DamageTakenEvent) -> list[EventResponse]:
        """
        Handle effects that should trigger or break when damage is taken.

        Args:
            event (DamageTakenEvent):
                The damage taken event.

        Returns:
            list[EventResponse]:
                Responses from effects that were broken or triggered.

        """
        # Check for incapacitating effects that should break on damage.
        responses: list[EventResponse] = []
        effects_to_remove: list[ActiveEffect] = []
        for ae in self.incapacitating_effects:
            response = ae.on_damage_taken(event)
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
        variables = variables or self.owner.get_expression_variables()

        # Build the ActiveEffect for the passive effect.
        passive_ae = ActiveEffect(
            source=self.owner,
            target=self.owner,
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

    def has_effect(self, effect: Effect) -> bool:
        """
        Check if a specific effect is currently active.

        Args:
            effect (Effect): The effect to check.

        Returns:
            bool: True if the effect is active, False otherwise.

        """
        return any(ae.effect == effect for ae in self.active_effects)

    def can_add_effect(
        self,
        source: Any,
        effect: Effect,
        variables: list[VarInfo] = [],
    ) -> bool:
        """
        Determine if an effect can be added to the character.

        Args:
            effect (Effect):
                The effect to check.
            source (Any):
                The source of the effect (e.g., the caster).
            variables (list[VarInfo]):
                The variables associated with the effect.

        Returns:
            bool:
                True if the effect can be added, False otherwise.

        """
        if isinstance(effect, HealingOverTimeEffect):
            return self.owner.stats.hp < self.owner.HP_MAX and not self.has_effect(effect)

        if isinstance(effect, DamageOverTimeEffect):
            return not self.has_effect(effect)

        if isinstance(effect, ModifierEffect):
            candidate = ActiveEffect(
                source=source,
                target=self.owner,
                effect=effect,
                duration=effect.duration,
                variables=variables,
            )
            for modifier in effect.modifiers:
                bonus_type = modifier.bonus_type
                existing = self.active_modifiers.get(bonus_type)
                if not existing or self._get_modifier_strength(
                    candidate, bonus_type
                ) > self._get_modifier_strength(existing, bonus_type):
                    return True
            return False

        # Check for IncapacitatingEffect - don't apply same type if already active

        if isinstance(effect, IncapacitatingEffect):
            # Don't apply the same incapacitation type if already present
            for ae in self.active_effects:
                if (
                    isinstance(ae.effect, IncapacitatingEffect)
                    and ae.effect.incapacitation_type == effect.incapacitation_type
                ):
                    return False
            return True

        return True

    # === Modifier Management ===

    def get_modifier(
        self,
        bonus_type: BonusType,
    ) -> Any:
        """
        Get the modifier value for a specific bonus type.

        Args:
            bonus_type (BonusType):
                The type of bonus to retrieve.

        Returns:
            Any:
                Either `list[str]` or `list[DamageComponent]` depending on the
                bonus type, or an empty list if no modifier is active.

        """
        # Get all the active effects for the bonus type.
        ae = self.active_modifiers.get(bonus_type)
        if not ae:
            return []
        # If the effect is not a ModifierEffect, return an empty list.
        if not isinstance(ae.effect, ModifierEffect):
            return []
        # Find the modifier for the specific bonus type.
        modifiers = []
        for mod in ae.effect.modifiers:
            if mod.bonus_type == bonus_type:
                modifiers.append(mod)
        # If no modifiers found, return None.
        if not modifiers:
            return []
        # Return the modifier value(s) based on the bonus type.
        if bonus_type == BonusType.ATTACK:
            return [str(modifier.value) for modifier in modifiers]
        if bonus_type == BonusType.DAMAGE:
            return [modifier.value for modifier in modifiers]
        return [modifier.value for modifier in modifiers]

    def get_damage_modifiers(self) -> list[DamageComponent]:
        """
        Get the best damage modifiers for each damage type from all active
        effects.

        Returns:
            list[DamageComponent]:
                List of the best modifier for each damage type.

        """
        best_by_type: dict[DamageType, DamageComponent] = {}

        for ae in self.active_effects:
            if not isinstance(ae.effect, ModifierEffect):
                continue

            # Find damage modifier in the effect
            damage_modifier = None
            for modifier in ae.effect.modifiers:
                if modifier.bonus_type == BonusType.DAMAGE:
                    damage_modifier = modifier
                    break

            if not damage_modifier or not isinstance(
                damage_modifier.value, DamageComponent
            ):
                continue

            mod = damage_modifier.value
            new_max = get_max_roll(mod.damage_roll, ae.variables)
            current = best_by_type.get(mod.damage_type)
            current_max = (
                get_max_roll(current.damage_roll, ae.variables) if current else -1
            )
            if new_max > current_max:
                best_by_type[mod.damage_type] = mod

        return list(best_by_type.values())

    def turn_update(self) -> None:
        """
        Update the effects for a turn, applying any changes and removing expired effects.
        """
        updated = []
        for ae in self.active_effects:

            ae.turn_update()

            # Only decrement duration if it's not None (indefinite effects)
            if ae.duration is not None:
                ae.duration -= 1

            # Keep effect if duration is None (indefinite) or still has time remaining
            if ae.duration is None or ae.duration > 0:
                updated.append(ae)
            else:
                cprint(
                    f"    :hourglass_done: [bold yellow]{ae.effect.name}[/] "
                    f"has expired on [bold]{self.owner.name}[/]."
                )
        self.active_effects = updated
        # Rebuild active_modifiers
        self.active_modifiers.clear()
        for ae in self.active_effects:
            if isinstance(ae.effect, ModifierEffect):
                for modifier in ae.effect.modifiers:
                    bt = modifier.bonus_type
                    if bt not in self.active_modifiers:
                        self.active_modifiers[bt] = ae

    # === Helpers ===

    def _get_modifier_strength(
        self,
        ae: ActiveEffect,
        bonus_type: BonusType,
    ) -> int:
        """
        Helper to determine the strength of a modifier for comparison purposes.

        Args:
            ae (ActiveEffect): The active effect to evaluate.
            bonus_type (BonusType): The bonus type to check.

        Returns:
            int: The strength value of the modifier.

        """
        if not isinstance(ae.effect, ModifierEffect):
            return 0

        # Find the modifier for the specific bonus type
        modifier = None
        for mod in ae.effect.modifiers:
            if mod.bonus_type == bonus_type:
                modifier = mod
                break

        if not modifier:
            return 0

        if bonus_type in [
            BonusType.HP,
            BonusType.MIND,
            BonusType.AC,
            BonusType.INITIATIVE,
        ]:
            if isinstance(modifier.value, int):
                return modifier.value
            if isinstance(modifier.value, str):
                return int(modifier.value)
            # DamageComponent - shouldn't happen for these bonus types
            return 0
        if bonus_type == BonusType.ATTACK:
            if isinstance(modifier.value, str):
                return get_max_roll(modifier.value, ae.variables)
            # int or DamageComponent - convert to string or return 0
            return (
                get_max_roll(str(modifier.value), ae.variables)
                if isinstance(modifier.value, int)
                else 0
            )
        if bonus_type == BonusType.DAMAGE:
            if isinstance(modifier.value, DamageComponent):
                return get_max_roll(modifier.value.damage_roll, ae.variables)
        return 0

    def _iterate_active_effects(self) -> Iterator[ActiveEffect]:
        """
        Iterator over all active effects.

        Returns:
            Iterator[ActiveEffect]: An iterator over active effects.

        """
        yield from self.active_effects

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
