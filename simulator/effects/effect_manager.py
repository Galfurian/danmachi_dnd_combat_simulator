# Revised effect_manager.py (per-BonusType tracking, 5e-style strict)

from typing import Any, Generator, Iterator
from core.constants import *
from effects.effect import *
from effects.modifier import Modifier


class ActiveEffect:
    def __init__(self, source: Any, effect: Effect, mind_level: int) -> None:
        self.source: Any = source
        self.effect: Effect = effect
        self.mind_level: int = mind_level
        self.duration: int = effect.max_duration
        self.consume_on_hit: bool = getattr(effect, "consume_on_hit", False)


class EffectManager:
    def __init__(self, owner: Any) -> None:
        self.owner: Any = owner
        self.active_effects: list[ActiveEffect] = []
        self.active_modifiers: dict[BonusType, ActiveEffect] = {}

    # === Effect Management ===

    def add_effect(self, source: Any, effect: Effect, mind_level: int) -> bool:
        new_effect = ActiveEffect(source, effect, mind_level)

        if isinstance(effect, HoT):
            if self.has_effect(effect):
                return False

        elif isinstance(effect, DoT):
            if self.has_effect(effect):
                return False

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

        self.active_effects.append(new_effect)
        return True

    def remove_effect(self, active_effect: ActiveEffect) -> None:
        if active_effect in self.active_effects:
            self.active_effects.remove(active_effect)
        # Clean up from active_modifiers
        if isinstance(active_effect.effect, ModifierEffect):
            for modifier in active_effect.effect.modifiers:
                bonus_type = modifier.bonus_type
                if self.active_modifiers.get(bonus_type) == active_effect:
                    del self.active_modifiers[bonus_type]

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
            candidate = ActiveEffect(source, effect, mind_level)
            for modifier in effect.modifiers:
                bonus_type = modifier.bonus_type
                existing = self.active_modifiers.get(bonus_type)
                if not existing or self._get_modifier_strength(
                    candidate, bonus_type
                ) > self._get_modifier_strength(existing, bonus_type):
                    return True
            return False

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
            return int(modifier.value)
        elif bonus_type == BonusType.ATTACK:
            return [modifier.value]
        elif bonus_type == BonusType.DAMAGE:
            return (
                [modifier.value] if isinstance(modifier.value, DamageComponent) else []
            )

    def get_damage_modifiers(self) -> list[tuple[DamageComponent, int]]:
        consume_on_hit: list[tuple[DamageComponent, int]] = []
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
            if ae.consume_on_hit:
                consume_on_hit.append((mod, ae.mind_level))
                ae.consume_on_hit = False
                continue

            variables = ae.source.get_expression_variables()
            variables["MIND"] = ae.mind_level
            new_max = get_max_roll(mod.damage_roll, variables)
            current = best_by_type.get(mod.damage_type)
            current_max = (
                get_max_roll(current[0].damage_roll, variables) if current else -1
            )
            if new_max > current_max:
                best_by_type[mod.damage_type] = (mod, ae.mind_level)

        return list(best_by_type.values()) + consume_on_hit

    def turn_update(self) -> None:
        updated = []
        for ae in self.active_effects:
            if ae.consume_on_hit:
                updated.append(ae)
                continue
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
            return int(modifier.value)
        elif bonus_type == BonusType.ATTACK:
            return get_max_roll(modifier.value, variables)
        elif bonus_type == BonusType.DAMAGE:
            if isinstance(modifier.value, DamageComponent):
                return get_max_roll(modifier.value.damage_roll, variables)
        return 0

    def _iterate_active_effects(self) -> Iterator[ActiveEffect]:
        yield from self.active_effects
