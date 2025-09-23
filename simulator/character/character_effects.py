# Revised effects_module.py (per-BonusType tracking, 5e-style strict)

from collections.abc import Iterator
from typing import Any, Union

from catchery import log_critical
from combat.damage import DamageComponent
from core.constants import BonusType, DamageType
from core.utils import GameException, VarInfo, cprint, get_max_roll
from effects.base_effect import Effect, ActiveEffect
from effects.damage_over_time_effect import DamageOverTimeEffect
from effects.healing_over_time_effect import HealingOverTimeEffect
from effects.incapacitating_effect import IncapacitatingEffect
from effects.modifier_effect import ModifierEffect
from effects.trigger_effect import TriggerData, TriggerEffect
from pydantic import BaseModel, Field


class CharacterEffects(BaseModel):
    """
    Manages all effects (active, passive, modifiers, triggers) for a character,
    including application, removal, and effect updates.
    """

    owner: Any = Field(
        description="The character that owns this effects module",
    )
    active_effects: list[ActiveEffect] = Field(
        default_factory=list,
        description="List of currently active effects on the character",
    )
    active_modifiers: dict[BonusType, ActiveEffect] = Field(
        default_factory=dict,
        description="Mapping of active modifier effects by BonusType",
    )

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
        from character.main import Character
        from actions.spells.base_spell import Spell

        assert isinstance(self.owner, Character)
        assert isinstance(source, Character)
        assert isinstance(effect, Effect)
        assert all(isinstance(v, VarInfo) for v in variables)

        new_effect = ActiveEffect(
            source=source,
            target=self.owner,
            effect=effect,
            duration=effect.duration,
            variables=variables,
        )

        if isinstance(effect, HealingOverTimeEffect | DamageOverTimeEffect):
            if self.has_effect(effect):
                return False
        elif (
            isinstance(effect, TriggerEffect)
            and effect.trigger_condition.trigger_type.value == "on_hit"
        ):
            # Only allow one OnHit trigger spell at a time (like D&D 5e smite spells)
            # Remove any existing OnHit trigger effects first
            existing_triggers = [
                ae
                for ae in self.active_effects
                if isinstance(ae.effect, TriggerEffect)
                and ae.effect.trigger_condition.trigger_type.value == "on_hit"
            ]
            for existing_trigger in existing_triggers:
                self.remove_effect(existing_trigger)
                cprint(f"    ⚠️  {effect.name} replaces {existing_trigger.effect.name}.")

        elif isinstance(effect, ModifierEffect):
            for modifier in effect.modifiers:
                bonus_type = modifier.bonus_type
                existing = self.active_modifiers.get(bonus_type)
                if existing:
                    if self._get_modifier_strength(
                        new_effect, bonus_type
                    ) <= self._get_modifier_strength(existing, bonus_type):
                        return False
                    self.remove_effect(existing)
                self.active_modifiers[bonus_type] = new_effect

        # Handle incapacitating effects
        if isinstance(effect, IncapacitatingEffect):
            # Remove any existing incapacitating effects of the same type
            existing_incap = [
                ae
                for ae in self.active_effects
                if isinstance(ae.effect, IncapacitatingEffect)
                and ae.effect.incapacitation_type == effect.incapacitation_type
            ]
            for existing in existing_incap:
                self.remove_effect(existing)

        self.active_effects.append(new_effect)
        return True

    def handle_damage_taken(
        self,
        damage_amount: int,
    ) -> list[str]:
        """
        Handle effects that should trigger or break when damage is taken.

        Args:
            damage_amount (int):
                Amount of damage taken.

        Returns:
            list[str]:
                Messages about effects that were broken or triggered.

        """
        messages = []

        if damage_amount <= 0:
            return messages

        # Check for incapacitating effects that should break on damage
        effects_to_remove = []
        for active_effect in self.active_effects:
            if isinstance(active_effect.effect, IncapacitatingEffect):
                if active_effect.effect.breaks_on_damage(damage_amount):
                    effects_to_remove.append(active_effect)
                    messages.append(
                        f"{self.owner.name} wakes up from "
                        f"{active_effect.effect.name} due to taking damage!"
                    )

        # Remove the effects that should break
        for effect_to_remove in effects_to_remove:
            self.remove_effect(effect_to_remove)

        return messages

    def remove_effect(self, effect: "ActiveEffect") -> bool:
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

    def add_passive_effect(self, effect: Effect) -> bool:
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
        if effect not in self.owner.passive_effects:
            self.owner.passive_effects.append(effect)
            return True
        return False

    def remove_passive_effect(self, effect: Effect) -> bool:
        """
        Remove a passive effect.

        Args:
            effect (Effect): The passive effect to remove.

        Returns:
            bool: True if the passive effect was removed, False otherwise.

        """
        if effect in self.owner.passive_effects:
            self.owner.passive_effects.remove(effect)
            return True
        return False

    def check_passive_triggers(self) -> list[str]:
        """
        Check all passive effects for trigger conditions and activate them.

        Returns:
            list[str]:
                Messages for effects that were triggered this check.

        """
        activation_messages = []

        for effect in self.owner.passive_effects:
            if not isinstance(effect, TriggerEffect):
                continue
            # Check for low health triggers using the new TriggerEffect system.
            if effect.trigger_condition.trigger_type.value == "on_low_health":
                # Create event data for health check
                event_data = {"event_type": "health_check", "character": self.owner}

                if effect.check_trigger(self.owner, event_data):
                    # Activate the trigger
                    _, trigger_effects = effect.activate_trigger(
                        self.owner,
                        event_data,
                    )
                    # Apply triggered effects to self
                    for triggered_effect in trigger_effects:
                        if triggered_effect.can_apply(self.owner, self.owner):
                            self.add_effect(self.owner, triggered_effect)
                    # Create activation message.
                    activation_messages.append(
                        f"🔥 {self.owner.name}'s [bold][{effect.color}]"
                        f"{effect.name}[/][/] activates!"
                    )

        return activation_messages

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
        from character.main import Character

        if not isinstance(self.owner, Character):
            raise GameException("Owner must be a Character instance.")

        if isinstance(effect, HealingOverTimeEffect):
            return self.owner.hp < self.owner.HP_MAX and not self.has_effect(effect)

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
            ae.effect.turn_update(ae)

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

    # === OnHit Trigger Management (TriggerEffect) ===

    def get_on_hit_triggers(self) -> list[ActiveEffect]:
        """
        Get all active TriggerEffect effects with on_hit condition.

        Returns:
            list[ActiveEffect]: List of active OnHit trigger effects.

        """
        triggers = []
        for ae in self.active_effects:
            if (
                isinstance(ae.effect, TriggerEffect)
                and ae.effect.trigger_condition.trigger_type.value == "on_hit"
            ):
                triggers.append(ae)
        return triggers

    def trigger_on_hit_effects(
        self,
        target: Any,
    ) -> TriggerData:
        """
        Trigger all OnHit trigger effects and return damage bonuses and effects
        to apply.

        Args:
            target (Any):
                The target being hit.

        Returns:
            TriggerData:
                A tuple containing:
                    - List of DamageComponent for bonus damage.
                    - List of Effect to apply to the target.
                    - List of TriggerEffect that were consumed.

        """
        # Prepare the object to return.
        trigger_data = TriggerData(
            damage_bonuses=[],
            effects_to_apply=[],
            consumed_triggers=[],
        )

        # Keep track of the effects to remove.
        effects_to_remove: list[ActiveEffect] = []

        for ae in self.get_on_hit_triggers():
            if not isinstance(ae.effect, TriggerEffect):
                continue

            trigger = ae.effect

            # Create event data for the hit
            event_data = {
                "event_type": "on_hit",
                "target": target,
                "variables": ae.variables,
            }

            # Check if the trigger should activate
            if trigger.check_trigger(self.owner, event_data):
                # Activate the trigger and get results
                damage_bonus, trigger_effects = trigger.activate_trigger(
                    self.owner, event_data
                )

                # Add damage bonuses from this trigger
                for damage_comp in damage_bonus:
                    trigger_data.damage_bonuses.append(damage_comp)

                # Add effects to apply to target
                for effect in trigger_effects:
                    trigger_data.effects_to_apply.append(effect)

                # Mark for removal if it consumes on trigger
                if trigger.consumes_on_trigger:
                    effects_to_remove.append(ae)
                    trigger_data.consumed_triggers.append(trigger)

        # Remove consumed effects
        for ae in effects_to_remove:
            self.remove_effect(ae)

        return trigger_data
