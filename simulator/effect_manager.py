from typing import Any
from effect import *
from constants import *


class ActiveEffect:
    def __init__(self, source: Any, effect: Effect, mind_level: int) -> None:
        self.source: Any = source
        self.effect: Effect = effect
        self.mind_level: int = mind_level
        self.duration: int = effect.max_duration

        assert self.duration > 0, "ActiveEffect duration must be greater than 0."


class EffectManager:
    def __init__(self, owner: Any):
        self.owner: Any = owner
        self.active_effects: list[ActiveEffect] = []

    def add_effect(self, source: Any, effect: Effect, mind_level: int):
        """Adds an effect to the character."""
        self.active_effects.append(ActiveEffect(source, effect, mind_level))

    def remove_effect(self, active_effect: ActiveEffect):
        """Removes an effect from the character."""
        self.active_effects.remove(active_effect)

    def has_effect(self, effect: Effect) -> bool:
        """Checks if the character has a specific effect active."""
        return any(ae.effect == effect for ae in self.active_effects)

    def get_remaining_duration(self, effect: Effect) -> int:
        """Gets the remaining duration of a specific effect."""
        for ae in self.active_effects:
            if ae.effect == effect:
                return ae.duration
        return 0

    def get_all_effects_of_type(self, effect_type: type[Effect]) -> list[ActiveEffect]:
        """Returns all active effects of a specific type."""
        return [ae for ae in self.active_effects if isinstance(ae.effect, effect_type)]

    def get_modifier(self, bonus_type: BonusType) -> Any:
        if bonus_type in [BonusType.HP, BonusType.MIND]:
            return sum(
                int(ae.effect.modifiers[bonus_type])
                for ae in self.active_effects
                if isinstance(ae.effect, ModifierEffect)
                if bonus_type in ae.effect.modifiers
            )
        if bonus_type in [BonusType.AC, BonusType.INITIATIVE]:
            return max(
                (
                    int(ae.effect.modifiers[bonus_type])
                    for ae in self.active_effects
                    if isinstance(ae.effect, ModifierEffect)
                    if bonus_type in ae.effect.modifiers
                ),
                default=0,
            )
        if bonus_type == BonusType.ATTACK:
            return [
                ae.effect.modifiers[bonus_type]
                for ae in self.active_effects
                if isinstance(ae.effect, ModifierEffect)
                if bonus_type in ae.effect.modifiers
            ]
        if bonus_type == BonusType.DAMAGE:
            best_by_type: dict[DamageType, dict[str, str]] = {}
            for ae in self.active_effects:
                if not isinstance(ae.effect, ModifierEffect):
                    continue
                if bonus_type not in ae.effect.modifiers:
                    continue
                dmg_type = ae.effect.modifiers[BonusType.DAMAGE]["damage_type"]
                dmg_roll = ae.effect.modifiers[BonusType.DAMAGE]["damage_roll"]
                new_max = get_max_roll(dmg_roll, self, 1)
                current = best_by_type.get(dmg_type)
                current_max = (
                    get_max_roll(current["damage_roll"], self, 1) if current else -1
                )
                if new_max > current_max:
                    best_by_type[dmg_type] = {
                        "damage_type": dmg_type,
                        "damage_roll": dmg_roll,
                    }
            return list(best_by_type.values())
        raise ValueError(f"Unknown bonus type: {bonus_type}")

    def would_be_useful(self, effect: Effect, entity: Any, mind_level: int) -> bool:
        if isinstance(effect, HoT):
            return entity.hp < entity.HP_MAX

        if isinstance(effect, DoT):
            return not any(
                isinstance(ae.effect, DoT) and ae.effect.name == effect.name
                for ae in self.active_effects
            )

        if isinstance(effect, ModifierEffect):
            usefulness_found = False
            for bonus_type, modifier in effect.modifiers.items():
                if bonus_type in [BonusType.HP, BonusType.MIND]:
                    usefulness_found = True
                elif bonus_type in [BonusType.AC, BonusType.INITIATIVE]:
                    value = int(modifier)
                    if value > self.get_modifier(bonus_type):
                        usefulness_found = True
                elif bonus_type == BonusType.ATTACK:
                    existing_roll_max = max(
                        get_max_roll(existing_modifier, entity, mind_level)
                        for existing_modifier in self.get_modifier(BonusType.ATTACK)
                    )
                    new_roll_max = get_max_roll(modifier, entity, mind_level)
                    if new_roll_max > existing_roll_max:
                        usefulness_found = True
                elif bonus_type == BonusType.DAMAGE:
                    existing_components = self.get_modifier(BonusType.DAMAGE)
                    existing_by_type = {
                        c["type"]: get_max_roll(c["roll"], entity, mind_level)
                        for c in existing_components
                    }
                    for new_component in modifier:
                        new_type = new_component["type"]
                        new_roll_max = get_max_roll(
                            new_component["roll"], entity, mind_level
                        )
                        if new_type not in existing_by_type:
                            usefulness_found = True
                            break
                        if new_roll_max > existing_by_type[new_type]:
                            usefulness_found = True
                            break
            return usefulness_found

        return False

    def turn_update(self):
        """Updates the active effects at the end of each turn."""
        for ae in self.active_effects:
            ae.effect.turn_update(ae.source, self.owner, ae.mind_level)
            # Decrease the duration of the effect.
            ae.duration -= 1
            # If the duration is less than or equal to zero, remove the effect.
            if ae.duration <= 0:
                console.print(
                    f"    :hourglass_done: [bold yellow]{ae.effect.name}[/] has expired on [bold]{self.owner.name}[/]."
                )
        self.active_effects = [ae for ae in self.active_effects if ae.duration > 0]
