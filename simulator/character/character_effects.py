# Revised effects_module.py (per-BonusType tracking, 5e-style strict)

from typing import Any, Generator, Iterator, Optional
from core.constants import *
from core.utils import cprint, get_max_roll
from core.error_handling import log_error, log_warning, log_critical
from combat.damage import DamageComponent
from effects import *


class ActiveEffect:
    """
    Represents an active effect applied to a character, including its source, target, effect details, mind level, and duration.
    """

    def __init__(
        self, source: Any, target: Any, effect: Effect, mind_level: int
    ) -> None:
        self.source: Any = source  # The caster
        self.target: Any = target  # The recipient
        self.effect: Effect = effect
        self.mind_level: int = mind_level
        self.duration: int = effect.duration


class CharacterEffects:
    """
    Manages all effects (active, passive, modifiers, triggers) for a character, including application, removal, and effect updates.
    """

    def __init__(self, owner: Any) -> None:
        self.owner: Any = owner
        self.active_effects: list[ActiveEffect] = []
        self.active_modifiers: dict[BonusType, ActiveEffect] = {}
        self.passive_effects: list[Effect] = []

    # === Effect Management ===

    def add_effect(
        self, source: Any, effect: Effect, mind_level: int, spell: Optional[Any] = None
    ) -> bool:
        """
        Add a new effect to the character.

        Args:
            source (Any): The source of the effect (e.g., the caster).
            effect (Effect): The effect to add.
            mind_level (int): The mind level of the effect.
            spell (Optional[Any], optional): The spell associated with the effect, if any. Defaults to None.

        Returns:
            bool: True if the effect was added successfully, False otherwise.
        """
        try:
            # Validate inputs
            if not source:
                log_error(
                    "Source cannot be None when adding effect",
                    {"effect": getattr(effect, "name", "unknown")},
                )
                return False

            if not effect:
                log_error(
                    "Effect cannot be None when adding to effect manager",
                    {"source": getattr(source, "name", "unknown")},
                )
                return False

            if not isinstance(mind_level, int) or mind_level < 0:
                log_warning(
                    f"Mind level must be non-negative integer, got: {mind_level}",
                    {"effect": effect.name, "mind_level": mind_level},
                )
                mind_level = max(
                    0, int(mind_level) if isinstance(mind_level, (int, float)) else 0
                )

            new_effect = ActiveEffect(source, self.owner, effect, mind_level)

            # Check concentration limit if this effect requires concentration
            if getattr(effect, "requires_concentration", False) and spell:
                # The concentration is managed by the SOURCE (caster), not the target
                if not source.concentration_module.add_concentration_effect(
                    spell, self.owner, new_effect, mind_level
                ):
                    return False  # Could not add due to concentration limits

            if isinstance(effect, HealingOverTimeEffect):
                if self.has_effect(effect):
                    return False

            elif isinstance(effect, DamageOverTimeEffect):
                if self.has_effect(effect):
                    return False

            elif isinstance(effect, TriggerEffect) and effect.trigger_condition.trigger_type.value == "on_hit":
                # Only allow one OnHit trigger spell at a time (like D&D 5e smite spells)
                # Remove any existing OnHit trigger effects first
                existing_triggers = [
                    ae
                    for ae in self.active_effects
                    if isinstance(ae.effect, TriggerEffect) and ae.effect.trigger_condition.trigger_type.value == "on_hit"
                ]
                for existing_trigger in existing_triggers:
                    self.remove_effect(existing_trigger)
                    # Show message about replacing the old trigger
                    from core.utils import cprint

                    cprint(
                        f"    ⚠️  {effect.name} replaces {existing_trigger.effect.name}."
                    )

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

        except Exception as e:
            log_critical(
                f"Error adding effect to manager: {str(e)}",
                {
                    "ctx_effect": getattr(effect, "name", "unknown"),
                    "ctx_source": getattr(source, "name", "unknown"),
                    "ctx_target": getattr(self.owner, "name", "unknown"),
                },
                e,
            )
            return False

    def handle_damage_taken(self, damage_amount: int) -> list[str]:
        """
        Handle effects that should trigger or break when damage is taken.
        
        Args:
            damage_amount (int): Amount of damage taken.
            
        Returns:
            list[str]: Messages about effects that were broken or triggered.
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
                        f"{self.owner.name} wakes up from {active_effect.effect.name} due to taking damage!"
                    )
        
        # Remove the effects that should break
        for effect_to_remove in effects_to_remove:
            self.remove_effect(effect_to_remove)
            
        return messages

    def remove_effect(self, effect: "ActiveEffect") -> bool:
        """
        Remove an active effect from the character.

        Args:
            effect (ActiveEffect): The effect to remove.

        Returns:
            bool: True if the effect was removed successfully, False otherwise.
        """
        try:
            if effect in self.active_effects:
                self.active_effects.remove(effect)
                return True
            return False
        except Exception as e:
            log_error(
                f"Error removing effect from manager: {str(e)}",
                {
                    "ctx_effect": getattr(effect.effect, "name", "unknown"),
                    "ctx_target": getattr(self.owner, "name", "unknown"),
                },
                e,
            )
            return False

    # === Passive Effect Management ===

    def add_passive_effect(self, effect: Effect) -> bool:
        """
        Add a passive effect that is always active (like boss phase triggers).

        Args:
            effect (Effect): The passive effect to add.

        Returns:
            bool: True if the passive effect was added, False if it was already present.
        """
        if effect not in self.passive_effects:
            self.passive_effects.append(effect)
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
        if effect in self.passive_effects:
            self.passive_effects.remove(effect)
            return True
        return False

    def check_passive_triggers(self) -> list[str]:
        """Check all passive effects for trigger conditions and activate them.
        
        Returns:
            list[str]: Messages for effects that were triggered this check.
        """
        activation_messages = []

        for effect in self.passive_effects:
            # Check for low health triggers using the new TriggerEffect system
            if isinstance(effect, TriggerEffect) and effect.trigger_condition.trigger_type.value == "on_low_health":

                trigger_effect: TriggerEffect = effect  # type: ignore

                # Create event data for health check
                event_data = {
                    "event_type": "health_check",
                    "character": self.owner
                }

                if trigger_effect.check_trigger(self.owner, event_data):
                    # Activate the trigger
                    damage_bonuses, trigger_effects_with_levels = (
                        trigger_effect.activate_trigger(self.owner, event_data)
                    )

                    # Apply triggered effects to self
                    for triggered_effect, mind_level in trigger_effects_with_levels:
                        if triggered_effect.can_apply(self.owner, self.owner):
                            self.add_effect(self.owner, triggered_effect, mind_level)

                    # Create activation message
                    from core.constants import get_effect_color

                    activation_messages.append(
                        f"🔥 {self.owner.name}'s [bold][{get_effect_color(effect)}]{effect.name}[/][/] activates!"
                    )

        return activation_messages

    # === Regular Effect Management ===

    def get_effect_remaining_duration(self, effect: Effect) -> int:
        """
        Get the remaining duration of a specific effect.

        Args:
            effect (Effect): The effect to check.

        Returns:
            int: The remaining duration of the effect, or 0 if not active.
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

    def can_add_effect(self, effect: Effect, source: Any, mind_level: int) -> bool:
        """
        Determine if an effect can be added to the character.

        Args:
            effect (Effect): The effect to add.
            source (Any): The source of the effect.
            mind_level (int): The mind level of the effect.

        Returns:
            bool: True if the effect can be added, False otherwise.
        """
        if isinstance(effect, HealingOverTimeEffect):
            return self.owner.hp < self.owner.HP_MAX and not self.has_effect(effect)

        if isinstance(effect, DamageOverTimeEffect):
            return not self.has_effect(effect)

        if isinstance(effect, ModifierEffect):
            candidate = ActiveEffect(source, self.owner, effect, mind_level)
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

    def get_modifier(self, bonus_type: BonusType) -> Any:
        """
        Get the modifier value for a specific bonus type.

        Args:
            bonus_type (BonusType): The type of bonus to retrieve.

        Returns:
            Any: The modifier value, which can be an integer, list, or 0.
        """
        ae = self.active_modifiers.get(bonus_type)
        if not ae:
            return (
                0
                if bonus_type
                in [BonusType.HP, BonusType.MIND, BonusType.AC, BonusType.INITIATIVE]
                else []
            )
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
            elif isinstance(modifier.value, str):
                return int(modifier.value)
            else:
                # DamageComponent - shouldn't happen for these bonus types
                return 0
        elif bonus_type == BonusType.ATTACK:
            return [modifier.value]
        elif bonus_type == BonusType.DAMAGE:
            return (
                [modifier.value] if isinstance(modifier.value, DamageComponent) else []
            )

    def get_damage_modifiers(self) -> list[tuple[DamageComponent, int]]:
        """
        Get the best damage modifiers for each damage type from all active effects.

        Returns:
            list[tuple[DamageComponent, int]]: List of (DamageComponent, mind_level) tuples for the best modifier of each type.
        """
        best_by_type: dict[DamageType, tuple[DamageComponent, int]] = {}

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
            variables = ae.source.get_expression_variables()
            variables["MIND"] = ae.mind_level
            new_max = get_max_roll(mod.damage_roll, variables)
            current = best_by_type.get(mod.damage_type)
            current_max = (
                get_max_roll(current[0].damage_roll, variables) if current else -1
            )
            if new_max > current_max:
                best_by_type[mod.damage_type] = (mod, ae.mind_level)

        return list(best_by_type.values())

    def turn_update(self) -> None:
        """
        Update the effects for a turn, applying any changes and removing expired effects.
        """
        updated = []
        for ae in self.active_effects:
            ae.effect.turn_update(ae.source, self.owner, ae.mind_level)
            ae.duration -= 1
            if ae.duration > 0:
                updated.append(ae)
            else:
                cprint(
                    f"    :hourglass_done: [bold yellow]{ae.effect.name}[/] has expired on [bold]{self.owner.name}[/]."
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

    def _get_modifier_strength(self, ae: ActiveEffect, bonus_type: BonusType) -> int:
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

        variables = ae.source.get_expression_variables()
        variables["MIND"] = ae.mind_level

        if bonus_type in [
            BonusType.HP,
            BonusType.MIND,
            BonusType.AC,
            BonusType.INITIATIVE,
        ]:
            if isinstance(modifier.value, int):
                return modifier.value
            elif isinstance(modifier.value, str):
                return int(modifier.value)
            else:
                # DamageComponent - shouldn't happen for these bonus types
                return 0
        elif bonus_type == BonusType.ATTACK:
            if isinstance(modifier.value, str):
                return get_max_roll(modifier.value, variables)
            else:
                # int or DamageComponent - convert to string or return 0
                return (
                    get_max_roll(str(modifier.value), variables)
                    if isinstance(modifier.value, int)
                    else 0
                )
        elif bonus_type == BonusType.DAMAGE:
            if isinstance(modifier.value, DamageComponent):
                return get_max_roll(modifier.value.damage_roll, variables)
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
            if isinstance(ae.effect, TriggerEffect) and ae.effect.trigger_condition.trigger_type.value == "on_hit":
                triggers.append(ae)
        return triggers

    def trigger_on_hit_effects(
        self, target: Any
    ) -> tuple[
        list[tuple[DamageComponent, int]], list[tuple[Effect, int]], list[TriggerEffect]
    ]:
        """
        Trigger all OnHit trigger effects and return damage bonuses and effects to apply.

        Args:
            target (Any): The target being hit.

        Returns:
            tuple: (damage_bonuses, effects_to_apply, consumed_triggers)
                - damage_bonuses: List of (DamageComponent, mind_level) tuples.
                - effects_to_apply: List of (Effect, mind_level) tuples.
                - consumed_triggers: List of TriggerEffect effects that were consumed.
        """
        damage_bonuses: list[tuple[DamageComponent, int]] = []
        effects_to_apply: list[tuple[Effect, int]] = []
        effects_to_remove: list[ActiveEffect] = []
        consumed_triggers: list[TriggerEffect] = []

        for ae in self.get_on_hit_triggers():
            if not isinstance(ae.effect, TriggerEffect):
                continue

            trigger = ae.effect

            # Create event data for the hit
            event_data = {
                "event_type": "on_hit",
                "target": target,
                "mind_level": ae.mind_level
            }

            # Check if the trigger should activate
            if trigger.check_trigger(self.owner, event_data):
                # Activate the trigger and get results
                damage_bonus, trigger_effects_with_levels = trigger.activate_trigger(self.owner, event_data)
                
                # Add damage bonuses from this trigger
                for damage_comp in damage_bonus:
                    damage_bonuses.append((damage_comp, ae.mind_level))

                # Add effects to apply to target (with mind level)
                for effect, mind_level in trigger_effects_with_levels:
                    effects_to_apply.append((effect, mind_level))

                # Mark for removal if it consumes on trigger
                if trigger.consumes_on_trigger:
                    effects_to_remove.append(ae)
                    consumed_triggers.append(trigger)

        # Remove consumed effects
        for ae in effects_to_remove:
            self.remove_effect(ae)

        return damage_bonuses, effects_to_apply, consumed_triggers
