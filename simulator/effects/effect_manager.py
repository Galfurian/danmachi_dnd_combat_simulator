from typing import Any, Generator, Iterator

from core.constants import *
from effects.effect import *


class ActiveEffect:
    def __init__(self, source: Any, effect: Effect, mind_level: int) -> None:
        self.source: Any = source
        self.effect: Effect = effect
        self.mind_level: int = mind_level
        self.duration: int = effect.max_duration
        self.consume_on_hit: bool = getattr(effect, "consume_on_hit", False)


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
                int(modifier)
                for modifier, _ in self._iterate_modifiers_by_type(bonus_type)
            )
        if bonus_type in [BonusType.AC, BonusType.INITIATIVE]:
            return max(
                (
                    int(modifier)
                    for modifier, _ in self._iterate_modifiers_by_type(bonus_type)
                ),
                default=0,
            )
        if bonus_type == BonusType.ATTACK:
            return [
                modifier for modifier, _ in self._iterate_modifiers_by_type(bonus_type)
            ]
        if bonus_type == BonusType.DAMAGE:
            consume_on_hit: list[DamageComponent] = []
            best_by_type: dict[DamageType, DamageComponent] = {}
            for modifier, ae in self._iterate_melee_damage_modifiers():
                # Consume on hit effects are handled separately.
                if ae.consume_on_hit:
                    consume_on_hit.append(modifier)
                    ae.consume_on_hit = False
                    continue
                variables = ae.source.get_expression_variables()
                variables["MIND"] = ae.mind_level
                # Compute the maximum roll for the modifier.
                new_max = get_max_roll(modifier.damage_roll, variables)
                # Get the current best modifier for this damage type.
                current = best_by_type.get(modifier.damage_type)
                # Compute the maximum roll for the current best modifier.
                current_max = (
                    get_max_roll(current.damage_roll, variables) if current else -1
                )
                # If the new modifier is better, update the best_by_type dictionary.
                if new_max > current_max:
                    best_by_type[modifier.damage_type] = modifier
            return list(best_by_type.values()) + consume_on_hit
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
            variables = entity.get_expression_variables()
            variables["MIND"] = mind_level

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
                        get_max_roll(existing_modifier, variables)
                        for existing_modifier in self.get_modifier(BonusType.ATTACK)
                    )
                    new_roll_max = get_max_roll(modifier, variables)
                    if new_roll_max > existing_roll_max:
                        usefulness_found = True
                elif bonus_type == BonusType.DAMAGE:
                    existing_components = self.get_modifier(BonusType.DAMAGE)
                    existing_by_type = {
                        c["type"]: get_max_roll(c["roll"], variables)
                        for c in existing_components
                    }
                    for new_component in modifier:
                        new_type = new_component["type"]
                        new_roll_max = get_max_roll(new_component["roll"], variables)
                        if new_type not in existing_by_type:
                            usefulness_found = True
                            break
                        if new_roll_max > existing_by_type[new_type]:
                            usefulness_found = True
                            break
            return usefulness_found

        return False

    def get_damage_modifiers(self) -> list[Tuple[DamageComponent, int]]:
        """Returns a list of all damage modifiers plus the mind used to apply them."""
        consume_on_hit: list[Tuple[DamageComponent, int]] = []
        best_by_type: dict[DamageType, Tuple[DamageComponent, int]] = {}
        for modifier, ae in self._iterate_melee_damage_modifiers():
            # Consume on hit effects are handled separately.
            if ae.consume_on_hit:
                consume_on_hit.append((modifier, ae.mind_level))
                ae.consume_on_hit = False
                continue
            # Get the varibles for the effect.
            variables = ae.source.get_expression_variables()
            variables["MIND"] = ae.mind_level
            # Compute the maximum roll for the modifier.
            new_max = get_max_roll(modifier.damage_roll, variables)
            # Get the current best modifier for this damage type.
            current = best_by_type.get(modifier.damage_type)
            # Compute the maximum roll for the current best modifier.
            current_max = (
                get_max_roll(current[0].damage_roll, variables) if current else -1
            )
            # If the new modifier is better, update the best_by_type dictionary.
            if new_max > current_max:
                best_by_type[modifier.damage_type] = (modifier, ae.mind_level)
        return list(best_by_type.values()) + consume_on_hit

    def turn_update(self):
        """Updates the active effects at the end of each turn."""
        for ae in self.active_effects:
            if ae.consume_on_hit:
                continue
            # Call the turn_update method of the effect.
            ae.effect.turn_update(ae.source, self.owner, ae.mind_level)
            # Decrease the duration of the effect.
            ae.duration -= 1
            # If the duration is less than or equal to zero, remove the effect.
            if ae.duration <= 0:
                console.print(
                    f"    :hourglass_done: [bold yellow]{ae.effect.name}[/] has expired on [bold]{self.owner.name}[/]."
                )
        self.active_effects = [
            ae for ae in self.active_effects if ae.duration > 0 or ae.consume_on_hit
        ]

    def _iterate_active_modifiers_effects(
        self, bonus_type: Optional[BonusType] = None
    ) -> Iterator[ActiveEffect]:
        """Yield all active effects that are ModifierEffects.

        Args:
            bonus_type (Optional[BonusType], optional): The type of bonus to filter by. Defaults to None.

        Yields:
            Iterator[ActiveEffect]: An iterator over active effects that are ModifierEffects, optionally filtered by bonus_type.
        """
        for ae in self.active_effects:
            if isinstance(ae.effect, ModifierEffect) and (
                bonus_type is None or bonus_type in ae.effect.modifiers
            ):
                yield ae

    def _iterate_modifiers_by_type(
        self, bonus_type: BonusType
    ) -> Generator[tuple[Any, ActiveEffect], Any, None]:
        for ae in self._iterate_active_modifiers_effects(bonus_type):
            assert isinstance(ae.effect, ModifierEffect)
            yield ae.effect.modifiers[bonus_type], ae

    def _iterate_melee_damage_modifiers(
        self,
    ) -> Generator[tuple[DamageComponent, ActiveEffect], Any, None]:
        for modifier, ae in self._iterate_modifiers_by_type(BonusType.DAMAGE):
            yield modifier, ae

    def _iterate_consume_on_hit_modifiers(
        self,
    ) -> Generator[tuple[DamageComponent, ActiveEffect], Any, None]:
        """Yield (modifier_dict, active_effect) for one-shot damage riders."""
        for modifier, ae in self._iterate_melee_damage_modifiers():
            if ae.consume_on_hit:
                yield modifier, ae
