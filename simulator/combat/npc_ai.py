from typing import Optional, Tuple

from actions.attack_action import BaseAttack, NaturalAttack, WeaponAttack
from actions.base_action import BaseAction
from actions.spell_action import SpellAttack, SpellBuff, SpellDebuff, SpellHeal
from entities.character import Character

# =============================================================================
# Sorting Functions
# =============================================================================

def _hp_ratio(character: Character) -> float:
    """Helper function to calculate HP ratio."""
    return character.hp / character.HP_MAX if character.HP_MAX > 0 else 1.0

def _sort_targets_by_usefulness_and_hp(targets: list[Character], action, mind_level: int = 0) -> list[Character]:
    """
    Generic sorting function that prioritizes:
    1. Targets where the effect would be useful
    2. Lower HP ratio within each group
    """
    useful = [
        t for t in targets
        if action.effect is None or t.effect_manager.can_add_effect(action.effect, t, mind_level)
    ]
    not_useful = [t for t in targets if t not in useful]
    
    useful_sorted = sorted(useful, key=_hp_ratio)
    not_useful_sorted = sorted(not_useful, key=_hp_ratio)
    
    return useful_sorted + not_useful_sorted

def _sort_for_base_attack(
    actor: Character, action: BaseAttack, targets: list[Character]
) -> list[Character]:
    """Prioritizes targets for base attacks."""
    return _sort_targets_by_usefulness_and_hp(targets, action, 0)

def _sort_for_spell_attack(
    actor: Character, spell: SpellAttack, targets: list[Character]
) -> list[Character]:
    """Prioritizes targets for offensive spells."""
    return _sort_targets_by_usefulness_and_hp(targets, spell, spell.mind_cost[0])

def _sort_for_spell_heal(
    actor: Character, spell: SpellHeal, targets: list[Character]
) -> list[Character]:
    """Prioritizes targets by how much they need healing."""
    wounded = [t for t in targets if t.hp < t.HP_MAX]
    
    def priority_key(t: Character) -> Tuple[float, bool]:
        hp_ratio = _hp_ratio(t)
        usefulness = spell.effect is None or t.effect_manager.can_add_effect(
            spell.effect, t, spell.mind_cost[0]
        )
        return (hp_ratio, not usefulness)
    
    return sorted(wounded, key=priority_key)

def _sort_for_spell_buff(
    actor: Character, action: SpellBuff, targets: list[Character]
) -> list[Character]:
    """Returns targets sorted by whether the effect would be useful."""
    return _sort_targets_by_usefulness_and_hp(targets, action, action.mind_cost[0])

def _sort_for_spell_debuff(
    actor: Character, spell: SpellDebuff, targets: list[Character]
) -> list[Character]:
    """Sorts debuff targets by usefulness and HP."""
    return _sort_targets_by_usefulness_and_hp(targets, spell, spell.mind_cost[0])


# =============================================================================
# Improved AI Functions - Split Weapon and Target Selection
# =============================================================================

def choose_best_weapon_for_situation(
    npc: Character, 
    weapons: list["WeaponAttack"], 
    enemies: list[Character]
) -> Optional["WeaponAttack"]:
    """
    Choose the best weapon type based on overall battlefield effectiveness.
    This separates weapon selection from target selection for better performance.
    """
    if not weapons or not enemies:
        return None
    
    best_weapon = None
    best_score = -1
    
    for weapon in weapons:
        # Skip if weapon is on cooldown
        if npc.is_on_cooldown(weapon):
            continue
            
        # Calculate weapon effectiveness against all available targets
        total_score = 0
        valid_target_count = 0
        
        for target in enemies:
            # Skip dead targets
            if not target.is_alive():
                continue
                
            valid_target_count += 1
            
            # Effect score
            effect_score = 0
            if weapon.effect and target.effect_manager.can_add_effect(weapon.effect, target, 0):
                effect_score = 10
            
            # Damage potential score
            damage_score = len(weapon.damage) * 2
            
            # Weapon versatility score
            target_score = effect_score + damage_score
            total_score += target_score
        
        if valid_target_count > 0:
            # Average effectiveness across all targets
            avg_score = total_score / valid_target_count
            if avg_score > best_score:
                best_score = avg_score
                best_weapon = weapon
    
    return best_weapon

def choose_best_target_for_weapon(
    npc: Character, 
    weapon: "WeaponAttack", 
    enemies: list[Character]
) -> Optional[Character]:
    """
    Choose the best target for a specific weapon.
    This is much faster than re-evaluating all weapon-target combinations.
    """
    if not weapon or not enemies:
        return None
    
    # Use existing sorting logic but only for this weapon
    sorted_targets = _sort_for_base_attack(npc, weapon, enemies)
    
    # Find the first alive target
    for target in sorted_targets:
        if target.is_alive():
            return target
    
    return None

def get_weapon_attacks(npc: Character) -> list["WeaponAttack"]:
    """Get available weapon attacks for a character."""
    return npc.get_available_weapon_attacks()

def get_natural_attacks(npc: Character) -> list["NaturalAttack"]:
    """Get available natural attacks for a character.""" 
    return npc.get_available_natural_weapon_attacks()


# =============================================================================
# Public API
# =============================================================================


def get_all_combat_actions(npc: Character) -> list[BaseAction]:
    return (
        npc.get_available_attacks()
        + npc.get_available_actions()
        + npc.get_available_spells()
    )


def get_actions_by_type(npc: Character, action_type: type) -> list:
    """Generic function to get actions of a specific type."""
    return [a for a in get_all_combat_actions(npc) if isinstance(a, action_type)]


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
                if target.effect_manager.can_add_effect(attack.effect, target, 0):
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
                or t.effect_manager.can_add_effect(spell.effect, t, mind_level)
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
                and t.effect_manager.can_add_effect(spell.effect, t, mind_level)
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
                if t.effect_manager.can_add_effect(spell.effect, t, mind_level)
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
                and t.effect_manager.can_add_effect(spell.effect, t, mind_level)
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
