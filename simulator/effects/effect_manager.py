# Revised effect_manager.py (per-BonusType tracking, 5e-style strict)

from typing import Any, Generator, Iterator, Optional
from core.constants import *
from core.utils import cprint
from core.error_handling import log_error, log_warning, log_critical
from effects.effect import *
from effects.modifier import Modifier


class ActiveEffect:
    def __init__(
        self, source: Any, target: Any, effect: Effect, mind_level: int
    ) -> None:
        self.source: Any = source  # The caster
        self.target: Any = target  # The recipient
        self.effect: Effect = effect
        self.mind_level: int = mind_level
        self.duration: int = effect.max_duration


class EffectManager:
    def __init__(self, owner: Any) -> None:
        self.owner: Any = owner
        self.active_effects: list[ActiveEffect] = []
        self.active_modifiers: dict[BonusType, ActiveEffect] = {}
        # Passive effects that are always active (like boss phase triggers)
        self.passive_effects: list[Effect] = []

    # === Effect Management ===

    def add_effect(
        self, source: Any, effect: Effect, mind_level: int, spell: Optional[Any] = None
    ) -> bool:
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

            if isinstance(effect, HoT):
                if self.has_effect(effect):
                    return False

            elif isinstance(effect, DoT):
                if self.has_effect(effect):
                    return False

            elif isinstance(effect, OnHitTrigger):
                # Only allow one OnHitTrigger spell at a time (like D&D 5e smite spells)
                # Remove any existing OnHitTrigger effects first
                existing_triggers = [
                    ae
                    for ae in self.active_effects
                    if isinstance(ae.effect, OnHitTrigger)
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
            from effects.incapacitation_effect import IncapacitatingEffect
            if isinstance(effect, IncapacitatingEffect):
                # Remove any existing incapacitating effects of the same type
                existing_incap = [
                    ae for ae in self.active_effects 
                    if isinstance(ae.effect, IncapacitatingEffect) and 
                    ae.effect.incapacitation_type == effect.incapacitation_type
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

    def remove_effect(self, effect: "ActiveEffect") -> bool:
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
        """Add a passive effect that is always active (like boss phase triggers)."""
        if effect not in self.passive_effects:
            self.passive_effects.append(effect)
            return True
        return False

    def remove_passive_effect(self, effect: Effect) -> bool:
        """Remove a passive effect."""
        if effect in self.passive_effects:
            self.passive_effects.remove(effect)
            return True
        return False

    def check_passive_triggers(self) -> list[str]:
        """
        Checks all passive effects for trigger conditions and activates them.
        Returns a list of activation messages for triggered effects.

        Returns:
            list[str]: Messages for effects that were triggered this check.
        """
        activation_messages = []

        for effect in self.passive_effects:
            # Check for OnLowHealthTrigger specifically
            if effect.__class__.__name__ == "OnLowHealthTrigger":
                # Import here to avoid circular imports
                from effects.effect import OnLowHealthTrigger

                trigger_effect: OnLowHealthTrigger = effect  # type: ignore

                if trigger_effect.should_trigger(self.owner):
                    # Activate the trigger
                    damage_bonuses, trigger_effects_with_levels = (
                        trigger_effect.activate(self.owner)
                    )

                    # Apply triggered effects to self
                    for triggered_effect, mind_level in trigger_effects_with_levels:
                        if triggered_effect.can_apply(self.owner, self.owner):
                            self.add_effect(
                                self.owner, triggered_effect, mind_level
                            )

                    # Create activation message
                    from core.constants import get_effect_color

                    activation_messages.append(
                        f"🔥 {self.owner.name}'s [bold][{get_effect_color(effect)}]{effect.name}[/][/] activates!"
                    )

        return activation_messages

    # === Regular Effect Management ===

    def get_effect_remaining_duration(self, effect: Effect) -> int:
        for ae in self.active_effects:
            if ae.effect == effect:
                return ae.duration
        return 0

    def has_effect(self, effect: Effect) -> bool:
        return any(ae.effect == effect for ae in self.active_effects)

    def can_add_effect(self, effect: Effect, source: Any, mind_level: int) -> bool:
        if isinstance(effect, HoT):
            return self.owner.hp < self.owner.HP_MAX and not self.has_effect(effect)

        if isinstance(effect, DoT):
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
        from effects.incapacitation_effect import IncapacitatingEffect
        if isinstance(effect, IncapacitatingEffect):
            # Don't apply the same incapacitation type if already present
            for ae in self.active_effects:
                if (isinstance(ae.effect, IncapacitatingEffect) and 
                    ae.effect.incapacitation_type == effect.incapacitation_type):
                    return False
            return True

        return True

    # === Modifier Management ===

    def get_modifier(self, bonus_type: BonusType) -> Any:
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
        yield from self.active_effects

    # === OnHitTrigger Management ===

    def get_on_hit_triggers(self) -> list[ActiveEffect]:
        """Get all active OnHitTrigger effects."""
        triggers = []
        for ae in self.active_effects:
            if isinstance(ae.effect, OnHitTrigger):
                triggers.append(ae)
        return triggers

    def trigger_on_hit_effects(
        self, target: Any
    ) -> tuple[
        list[tuple[DamageComponent, int]], list[tuple[Effect, int]], list[OnHitTrigger]
    ]:
        """
        Trigger all OnHitTrigger effects and return damage bonuses and effects to apply.

        Args:
            target: The target being hit

        Returns:
            tuple: (damage_bonuses, effects_to_apply, consumed_triggers)
                - damage_bonuses: List of (DamageComponent, mind_level) tuples for extra damage
                - effects_to_apply: List of (Effect, mind_level) tuples to apply to the target
                - consumed_triggers: List of OnHitTrigger effects that were consumed
        """
        damage_bonuses: list[tuple[DamageComponent, int]] = []
        effects_to_apply: list[tuple[Effect, int]] = []
        effects_to_remove: list[ActiveEffect] = []
        consumed_triggers: list[OnHitTrigger] = []

        for ae in self.get_on_hit_triggers():
            if not isinstance(ae.effect, OnHitTrigger):
                continue

            trigger = ae.effect

            # Add damage bonuses from this trigger
            for damage_comp in trigger.damage_bonus:
                damage_bonuses.append((damage_comp, ae.mind_level))

            # Add effects to apply to target (with mind level)
            for effect in trigger.trigger_effects:
                effects_to_apply.append((effect, ae.mind_level))

            # Mark for removal if it consumes on trigger
            if trigger.consumes_on_trigger:
                effects_to_remove.append(ae)
                consumed_triggers.append(trigger)

        # Remove consumed effects
        for ae in effects_to_remove:
            self.remove_effect(ae)

        return damage_bonuses, effects_to_apply, consumed_triggers
