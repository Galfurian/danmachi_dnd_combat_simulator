from actions.base_action import *
from actions.attack_action import *
from actions.spell_action import *
from entities.character import *

# =============================================================================
# Sorting Functions
# =============================================================================


def _sort_for_base_attack(
    actor: Character, action: BaseAttack, targets: list[Character]
) -> list[Character]:
    """
    Prioritizes targets for base attacks.
    - Lower HP gets higher priority.
    - Effects (if any) are considered via `would_be_useful`.
    """
    useful = [
        t
        for t in targets
        if action.effect is None
        or t.effect_manager.would_be_useful(action.effect, t, mind_level=0)
    ]
    not_useful = [t for t in targets if t not in useful]

    def hp_ratio(t: Character) -> float:
        return t.hp / t.HP_MAX if t.HP_MAX > 0 else 1.0

    useful_sorted = sorted(useful, key=hp_ratio)
    not_useful_sorted = sorted(not_useful, key=hp_ratio)

    return useful_sorted + not_useful_sorted


def _sort_for_spell_attack(
    actor: Character, spell: SpellAttack, targets: list[Character]
) -> list[Character]:
    """
    Prioritizes targets for offensive spells:
    - Enemies with lower HP
    - Enemies not already affected by this effect (if applicable)
    """
    useful = [
        t
        for t in targets
        if spell.effect is None
        or t.effect_manager.would_be_useful(spell.effect, t, spell.mind_cost[0])
    ]
    not_useful = [t for t in targets if t not in useful]

    # Within each group, sort by lowest HP%
    def hp_ratio(t: Character) -> float:
        return t.hp / t.HP_MAX if t.HP_MAX > 0 else 1.0

    useful_sorted = sorted(useful, key=hp_ratio)
    not_useful_sorted = sorted(not_useful, key=hp_ratio)

    return useful_sorted + not_useful_sorted


def _sort_for_spell_heal(
    actor: Character, spell: SpellHeal, targets: list[Character]
) -> list[Character]:
    """
    Prioritizes targets by how much they need healing and
    whether the healing effect (e.g., HoT) is useful.
    """
    wounded = [t for t in targets if t.hp < t.HP_MAX]

    def priority_key(t: Character) -> Tuple[float, bool]:
        hp_ratio = t.hp / t.HP_MAX if t.HP_MAX > 0 else 1.0
        usefulness = spell.effect is None or t.effect_manager.would_be_useful(
            spell.effect, t, spell.mind_cost[0]
        )
        # Lower HP and useful effect come first.
        return (hp_ratio, not usefulness)

    return sorted(wounded, key=priority_key)


def _sort_for_spell_buff(
    actor: Character, action: SpellBuff, targets: list[Character]
) -> list[Character]:
    """
    Returns targets sorted by whether the effect would be useful for them.
    Currently, only separates useful from not-useful, but preserves a consistent order.
    """
    useful = [
        t
        for t in targets
        if t.effect_manager.would_be_useful(action.effect, t, action.mind_cost[0])
    ]
    not_useful = [t for t in targets if t not in useful]
    return useful + not_useful


def _sort_for_spell_debuff(
    actor: Character, spell: SpellDebuff, targets: list[Character]
) -> list[Character]:
    """
    Sorts debuff targets:
    - First, those for whom the effect would be useful
    - Within that, prioritize lowest HP or worst resistance
    """
    useful = [
        t
        for t in targets
        if t.effect_manager.would_be_useful(spell.effect, t, spell.mind_cost[0])
    ]
    not_useful = [t for t in targets if t not in useful]

    def hp_ratio(t: Character) -> float:
        return t.hp / t.HP_MAX if t.HP_MAX > 0 else 1.0

    useful_sorted = sorted(useful, key=hp_ratio)
    not_useful_sorted = sorted(not_useful, key=hp_ratio)

    return useful_sorted + not_useful_sorted


# =============================================================================
# Public API
# =============================================================================


def get_all_combat_actions(npc: Character) -> list[BaseAction]:
    return (
        npc.get_available_attacks()
        + npc.get_available_actions()
        + npc.get_available_spells()
    )


def get_full_attacks(actions: list[BaseAction]) -> list[FullAttack]:
    return [a for a in actions if isinstance(a, FullAttack)]


def get_spell_attacks(actions: list[BaseAction]) -> list[SpellAttack]:
    return [a for a in actions if isinstance(a, SpellAttack)]


def get_spell_heals(actions: list[BaseAction]) -> list[SpellHeal]:
    return [a for a in actions if isinstance(a, SpellHeal)]


def get_spell_buffs(actions: list[BaseAction]) -> list[SpellBuff]:
    return [a for a in actions if isinstance(a, SpellBuff)]


def get_spell_debuffs(actions: list[BaseAction]) -> list[SpellDebuff]:
    return [a for a in actions if isinstance(a, SpellDebuff)]


def choose_best_base_attack_action(
    npc: Character,
    enemies: list[Character],
    base_attacks: list[BaseAttack],
) -> Optional[tuple[BaseAttack, Character]]:
    """
    Chooses the best attack and target combo based on:
    - Usefulness of the attack’s effect (if any)
    - Target vulnerability (low HP)
    - Number of damage components
    """
    best_score: float = -1
    best_attack: Optional[BaseAttack] = None
    best_target: Optional[Character] = None

    for attack in base_attacks:
        # Skip if the attack is not available (e.g., on cooldown).
        if npc.is_on_cooldown(attack):
            continue
        # Sort targets based on their vulnerability to the attack.
        sorted_targets = _sort_for_base_attack(npc, attack, enemies)
        # Iterate through sorted targets to find the best one.
        for target in sorted_targets:
            # Score based on how much the effect helps and how close the target is to death
            effect_score = 0
            if attack.effect:
                if target.effect_manager.would_be_useful(attack.effect, target, 0):
                    effect_score += 10
            # HP-based vulnerability (lower is better)
            hp_ratio = target.hp / target.HP_MAX if target.HP_MAX > 0 else 1
            vulnerability_score = (1 - hp_ratio) * 10
            # Damage component count (e.g., bonus fire + necrotic)
            damage_bonus = len(attack.damage)
            # Compute the total score.
            score = effect_score + vulnerability_score + damage_bonus
            # If the score is better than the current best, update.
            if score > best_score:
                best_score = score
                best_attack = attack
                best_target = target

    if best_attack and best_target:
        return best_attack, best_target

    return None


def choose_best_full_attack_action(
    npc: Character,
    enemies: list[Character],
    full_attacks: list[FullAttack],
) -> tuple[FullAttack, list[tuple[BaseAttack, Character]]] | None:
    """It selects the best FullAttack, and it returns the association between the BaseAttack of the FullAttack and their targets.

    Args:
        npc (Character): The NPC character making the attack.
        enemies (list[Character]): The list of enemy characters to attack.
        full_attacks (list[FullAttack]): The list of FullAttack actions available to the NPC.

    Returns:
        tuple[FullAttack, list[tuple[BaseAttack, Character]]] | None: The best FullAttack and a list of tuples associating each BaseAttack with its target, or None if no viable FullAttack is found.
    """
    for full_attack in full_attacks:
        available_associations = []
        for attack in full_attack.attacks:
            result = choose_best_base_attack_action(npc, enemies, [attack])
            if result:
                _, target = result
                available_associations.append((attack, target))
        if available_associations:
            return full_attack, available_associations
    return None


def choose_best_attack_spell_action(
    npc: Character,
    enemies: list[Character],
    spells: list[SpellAttack],
) -> tuple[SpellAttack, int, list[Character]] | None:
    """
    Chooses the best SpellAttack, mind level, and list of targets based on usefulness and value.
    Returns None if no viable offensive spell can be cast.
    """
    best_score = -1
    best_spell = None
    best_level = -1
    best_targets: list[Character] = []

    for spell in spells:
        if not spell.mind_cost:
            continue

        if npc.is_on_cooldown(spell):
            continue

        sorted_targets = _sort_for_spell_attack(npc, spell, enemies)

        for mind_level in spell.mind_cost:
            if mind_level > npc.mind:
                continue

            max_targets = spell.target_count(npc, mind_level)
            if max_targets <= 0:
                continue

            candidate_targets = sorted_targets[:max_targets]

            if not candidate_targets:
                continue

            # Score = how many targets the effect would benefit + bonus for low mind usage
            usefulness = sum(
                1
                for t in candidate_targets
                if spell.effect is None
                or t.effect_manager.would_be_useful(spell.effect, t, mind_level)
            )

            # Prioritize high usefulness, low cost.
            score = usefulness * 10 - mind_level

            if score > best_score:
                best_score = score
                best_spell = spell
                best_level = mind_level
                best_targets = candidate_targets
    if best_spell:
        return best_spell, best_level, best_targets
    return None


def choose_best_healing_spell_action(
    npc: Character,
    allies: list[Character],
    spells: list[SpellHeal],
) -> tuple[SpellHeal, int, list[Character]] | None:
    """
    Chooses the best healing spell, mind level, and set of targets based on:
    - Amount of HP missing
    - Number of wounded targets
    - Usefulness of HoT effect (if any)
    - Mind cost efficiency
    """
    best_score = -1
    best_spell = None
    best_level = -1
    best_targets: list[Character] = []

    for spell in spells:
        if not spell.mind_cost:
            continue

        if npc.is_on_cooldown(spell):
            continue

        sorted_targets = _sort_for_spell_heal(npc, spell, allies)

        for mind_level in spell.mind_cost:
            if mind_level > npc.mind:
                continue

            num_targets = spell.target_count(npc, mind_level)
            if num_targets <= 0:
                continue

            candidate_targets = sorted_targets[:num_targets]
            if not candidate_targets:
                continue

            # Score = total HP missing + useful HoTs - mind cost
            total_hp_missing = sum(t.HP_MAX - t.hp for t in candidate_targets)
            useful_effects = sum(
                1
                for t in candidate_targets
                if spell.effect
                and t.effect_manager.would_be_useful(spell.effect, t, mind_level)
            )

            score = total_hp_missing + useful_effects * 10 - mind_level

            if score > best_score:
                best_score = score
                best_spell = spell
                best_level = mind_level
                best_targets = candidate_targets

    if best_spell:
        return best_spell, best_level, best_targets

    return None


def choose_best_buff_spell_action(
    npc: Character,
    allies: list[Character],
    spells: list[SpellBuff],
) -> tuple[SpellBuff, int, list[Character]] | None:
    """
    Chooses the best SpellBuff, mind level, and set of targets based on:
    - Usefulness of the buff effect
    - Number of allies affected
    - Mind cost efficiency
    """
    best_score = -1
    best_spell = None
    best_level = -1
    best_targets: list[Character] = []

    for spell in spells:
        if not spell.mind_cost:
            continue

        if npc.is_on_cooldown(spell):
            continue

        sorted_targets = _sort_for_spell_buff(npc, spell, allies)

        for mind_level in spell.mind_cost:
            if mind_level > npc.mind:
                continue

            max_targets = spell.target_count(npc, mind_level)
            if max_targets <= 0:
                continue

            candidate_targets = sorted_targets[:max_targets]
            if not candidate_targets:
                continue

            usefulness = sum(
                1
                for t in candidate_targets
                if t.effect_manager.would_be_useful(spell.effect, t, mind_level)
            )

            score = usefulness * 10 - mind_level

            if score > best_score:
                best_score = score
                best_spell = spell
                best_level = mind_level
                best_targets = candidate_targets

    if best_spell:
        return best_spell, best_level, best_targets

    return None


def choose_best_debuff_spell_action(
    npc: Character,
    enemies: list[Character],
    spells: list[SpellDebuff],
) -> tuple[SpellDebuff, int, list[Character]] | None:
    """
    Chooses the best SpellDebuff, mind level, and set of enemy targets based on:
    - Whether the effect would be useful (not already applied)
    - Number of valid targets
    - Mind cost efficiency
    """
    best_score = -1
    best_spell = None
    best_level = -1
    best_targets: list[Character] = []

    for spell in spells:
        if not spell.mind_cost:
            continue

        if npc.is_on_cooldown(spell):
            continue

        sorted_targets = _sort_for_spell_debuff(npc, spell, enemies)

        for mind_level in spell.mind_cost:
            if mind_level > npc.mind:
                continue

            max_targets = spell.target_count(npc, mind_level)
            if max_targets <= 0:
                continue

            candidate_targets = sorted_targets[:max_targets]
            if not candidate_targets:
                continue

            usefulness = sum(
                1
                for t in candidate_targets
                if spell.effect
                and t.effect_manager.would_be_useful(spell.effect, t, mind_level)
            )

            score = usefulness * 10 - mind_level

            if score > best_score:
                best_score = score
                best_spell = spell
                best_level = mind_level
                best_targets = candidate_targets

    if best_spell:
        return best_spell, best_level, best_targets

    return None
