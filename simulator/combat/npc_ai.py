from typing import Any

from actions.abilities import (
    AbilityBuff,
    AbilityDebuff,
    AbilityHeal,
    AbilityOffensive,
)
from actions.abilities.base_ability import BaseAbility
from actions.attacks import BaseAttack, NaturalAttack, WeaponAttack
from actions.base_action import BaseAction, ValidActionEffect
from actions.spells import SpellBuff, SpellDebuff, SpellHeal, SpellOffensive
from actions.spells.base_spell import BaseSpell
from character import Character
from core.utils import VarInfo
from pydantic import BaseModel, Field

# =============================================================================
# Support Functions
# =============================================================================


class AttackSelection(BaseModel):
    attack: BaseAttack = Field(
        description="The attack being considered.",
    )
    targets: list[Character] = Field(
        default_factory=list,
        description="List of selected targets for the spell.",
    )
    score: float = Field(
        description="Score of the selection (higher is better).",
    )


class SpellSelection(BaseModel):
    """
    Represents a selected spell along with its rank, mind level, targets, and
    score.
    """

    spell: BaseSpell = Field(
        description="The spell being considered.",
    )
    rank: int = Field(
        description="The rank of the spell being considered.",
    )
    mind_level: int = Field(
        description="The mind level to cast the spell at.",
    )
    targets: list[Character] = Field(
        default_factory=list,
        description="List of selected targets for the spell.",
    )
    score: float = Field(
        description="Score of the selection (higher is better).",
    )


class AbilitySelection(BaseModel):
    """
    Represents a selected ability along with its targets and score.
    """

    ability: BaseAbility = Field(
        description="The ability being considered.",
    )
    targets: list[Character] = Field(
        default_factory=list,
        description="List of selected targets for the ability.",
    )
    score: float = Field(
        description="Score of the selection (higher is better).",
    )


def _hp_ratio(character: Character, missing: bool = False) -> float:
    """
    Helper function to calculate HP ratio.

    Args:
        character (Character):
            The character whose HP ratio to calculate.
        missing (bool):
            If True, returns the missing HP ratio (1 - current HP / max HP).

    Returns:
        float:
            The HP ratio (0.0 to 1.0), or missing HP ratio if specified.

    """
    ratio = (character.hp / character.HP_MAX) if character.HP_MAX > 0 else 1.0
    return 1.0 - ratio if missing else ratio


def _can_apply_any_effect(
    source: Character,
    target: Character,
    effects: list[ValidActionEffect],
    variables: list[VarInfo] = [],
) -> bool:
    """
    Checks if any effect can be applied to the target.

    Args:
        source (Character):
            The character applying the effect.
        target (Character):
            The character receiving the effect.
        effects (list[ValidActionEffect]):
            List of effects to evaluate.
        variables (list[VarInfo]):
            List of variables to use for evaluating usefulness.

    Returns:
        bool:
            True if at least one effect can be applied, False otherwise.

    """
    if not effects:
        return False
    return any(
        target.can_add_effect(
            source=source,
            effect=effect,
            variables=variables,
        )
        for effect in effects
    )


# =============================================================================
# TARGETS SORTING FUNCTIONS
# =============================================================================


def _sort_targets_by_usefulness_and_hp_offensive(
    action: BaseAttack | AbilityOffensive | SpellOffensive,
    source: Character,
    targets: list[Character],
    variables: list[VarInfo] = [],
    max_targets: int = 0,
) -> list[Character]:
    """
    Generic sorting function that prioritizes:
        1. Targets where the effect would be useful.
        2. Lower HP ratio within each group.

    Args:
        source (Character):
            The character performing the action.
        targets (list[Character]):
            List of potential targets.
        action (Any):
            The action being considered for the targets. Can be a spell, attack,
            or other action.
        variables (list[VarInfo]):
            List of variables to use for evaluating usefulness. Defaults to an
            empty list.
        max_targets (int):
            The maximum number of targets to return. If 0 or less, returns all
            sorted targets. Defaults to 0.

    Returns:
        list[Character]:
            Sorted list of targets based on usefulness and HP ratio.

    """
    # So here is the order of importance:
    # 1. Targets that have higher HP ratio (primary).
    # 2. Targets that can benefit from the effect (secondary).
    sorted_targets = sorted(
        targets,
        key=lambda target: (
            _hp_ratio(target),
            _can_apply_any_effect(
                source,
                target,
                action.effects,
                variables,
            ),
        ),
    )
    if max_targets > 0 and len(sorted_targets) > max_targets:
        return sorted_targets[:max_targets]
    return sorted_targets


def _sort_targets_by_usefulness_and_hp_healing(
    action: AbilityHeal | SpellHeal,
    source: Character,
    targets: list[Character],
    variables: list[VarInfo] = [],
    max_targets: int = 0,
) -> list[Character]:
    """
    Generic sorting function for healing actions.
    Prioritizes targets that need healing or where the effect would be useful.

    Args:
        source (Character):
            The character performing the action.
        targets (list[Character]):
            List of potential targets.
        action (Any):
            The healing action being considered for the targets. Can be a spell,
            ability, or other action.
        variables (list[VarInfo]):
            List of variables to use for evaluating usefulness. Defaults to an
            empty list.
        max_targets (int):
            The maximum number of targets to return. If 0 or less, returns all
            sorted targets. Defaults to 0.

    Returns:
        list[Character]:
            Sorted list of targets based on usefulness and HP ratio.

    """
    # So here is the order of importance:
    # 1. Targets that has a low HP ratio (primary).
    # 2. Targets that can benefit from the effect (secondary).
    sorted_targets = sorted(
        targets,
        key=lambda target: (
            _hp_ratio(target, missing=True),
            _can_apply_any_effect(
                source,
                target,
                action.effects,
                variables,
            ),
        ),
    )
    if max_targets > 0 and len(sorted_targets) > max_targets:
        return sorted_targets[:max_targets]
    return sorted_targets


def _sort_targets_by_usefulness_and_buff(
    action: AbilityBuff | AbilityDebuff | SpellBuff | SpellDebuff,
    source: Character,
    targets: list[Character],
    variables: list[VarInfo] = [],
    max_targets: int = 0,
) -> list[Character]:
    """
    Generic sorting function for buff actions.
    Prioritizes targets that would benefit from the buff.

    Args:
        source (Character):
            The character performing the action.
        targets (list[Character]):
            List of potential targets.
        action (Any):
            The buff action being considered for the targets.
        variables (list[VarInfo]):
            List of variables to use for evaluating usefulness. Defaults to an
            empty list.
        max_targets (int):
            The maximum number of targets to return. If 0 or less, returns all
            sorted targets. Defaults to 0.

    Returns:
        list[Character]:
            Sorted list of targets based on usefulness.

    """
    # So here is the order of importance:
    # 1. Targets that can benefit from the effect (primary).
    sorted_targets = sorted(
        targets,
        key=lambda target: _can_apply_any_effect(
            source,
            target,
            action.effects,
            variables,
        ),
    )
    if max_targets > 0 and len(sorted_targets) > max_targets:
        return sorted_targets[:max_targets]
    return sorted_targets


# =============================================================================
# ACTION-SPECIFIC SORTING FUNCTIONS
# =============================================================================


def _get_best_base_attack(
    attack: BaseAttack,
    source: Character,
    targets: list[Character],
    variables: list[VarInfo] = [],
) -> AttackSelection | None:
    """
    Prioritizes targets for base attacks.

    Args:
        attack (BaseAttack):
            The base attack being considered.
        source (Character):
            The character performing the attack.
        targets (list[Character]):
            List of potential targets.
        variables (list[VarInfo]):
            List of variables to use for evaluating usefulness. Defaults to an
            empty list.

    Returns:
        AttackSelection | None:
            The best attack and targets, or None if no valid targets are found.

    """
    variables = source.get_expression_variables()

    max_targets = attack.target_count(variables)
    if max_targets <= 0:
        return None

    sorted_targets = _sort_targets_by_usefulness_and_hp_offensive(
        action=attack,
        source=source,
        targets=targets,
        variables=variables,
        max_targets=max_targets,
    )
    if not sorted_targets:
        return None
    total_affected = len(sorted_targets)
    score = total_affected
    return AttackSelection(
        attack=attack,
        targets=sorted_targets,
        score=score,
    )


def _get_best_spell_attack(
    spell: SpellOffensive,
    source: Character,
    targets: list[Character],
) -> SpellSelection | None:
    """
    Optimizes both mind_level and targets for offensive spells.

    Args:
        source (Character):
            The character casting the spell.
        spell (SpellOffensive):
            The offensive spell being considered.
        targets (list[Character]):
            List of potential targets.

    Returns:
        SpellSelection | None:
            The best spell the source can cast.

    """
    best_spell: SpellSelection | None = None

    for rank, mind_level in enumerate(spell.mind_cost, 0):
        variables = spell.spell_get_variables(source, rank)

        if mind_level > source.mind:
            continue

        max_targets = spell.target_count(variables)
        if max_targets <= 0:
            continue

        sorted_targets = _sort_targets_by_usefulness_and_hp_offensive(
            action=spell,
            source=source,
            targets=targets,
            variables=variables,
            max_targets=max_targets,
        )
        if not sorted_targets:
            continue
        total_affected = len(sorted_targets)
        score = total_affected * 10 - mind_level
        if not best_spell or score > best_spell.score:
            best_spell = SpellSelection(
                spell=spell,
                rank=rank,
                mind_level=mind_level,
                targets=sorted_targets,
                score=score,
            )

    return best_spell


def _get_best_spell_heal(
    spell: SpellHeal,
    source: Character,
    targets: list[Character],
) -> SpellSelection | None:
    """
    Returns targets sorted by usefulness and HP for healing spells.

    Args:
        source (Character):
            The character casting the healing spell.
        spell (SpellHeal):
            The healing spell being considered.
        targets (list[Character]):
            List of potential targets.

    Returns:
        SpellSelection | None:
            The best spell the source can cast.

    """
    best_spell: SpellSelection | None = None

    for rank, mind_level in enumerate(spell.mind_cost, 0):
        variables = spell.spell_get_variables(source, rank)

        if mind_level > source.mind:
            continue

        max_targets = spell.target_count(variables)
        if max_targets <= 0:
            continue

        sorted_targets = _sort_targets_by_usefulness_and_hp_healing(
            action=spell,
            source=source,
            targets=targets,
            variables=variables,
            max_targets=max_targets,
        )
        if not sorted_targets:
            continue

        total_hp_missing = sum(t.HP_MAX - t.hp for t in sorted_targets)
        total_affected = len(sorted_targets)
        score = total_hp_missing + total_affected * 10 - mind_level

        if not best_spell or score > best_spell.score:
            best_spell = SpellSelection(
                spell=spell,
                rank=rank,
                mind_level=mind_level,
                targets=sorted_targets,
                score=score,
            )

    return best_spell


def _get_best_spell_buff_or_debuff(
    spell: SpellBuff | SpellDebuff,
    source: Character,
    targets: list[Character],
) -> SpellSelection | None:
    """
    Returns targets sorted by usefulness and HP for buff spells.

    Args:
        spell (SpellBuff | SpellDebuff):
            The buff or debuff spell being considered.
        source (Character):
            The character casting the buff or debuff spell.
        targets (list[Character]):
            List of potential targets.

    Returns:
        SpellSelection | None:
            The best spell the source can cast.

    """
    best_spell: SpellSelection | None = None

    for rank, mind_level in enumerate(spell.mind_cost, 0):
        variables = spell.spell_get_variables(source, rank)

        if mind_level > source.mind:
            continue

        max_targets = spell.target_count(variables)
        if max_targets <= 0:
            continue

        sorted_targets = _sort_targets_by_usefulness_and_buff(
            action=spell,
            source=source,
            targets=targets,
            variables=variables,
            max_targets=max_targets,
        )
        if not sorted_targets:
            continue

        total_affected = len(sorted_targets)
        score = total_affected * 10 - mind_level

        if not best_spell or score > best_spell.score:
            best_spell = SpellSelection(
                spell=spell,
                rank=rank,
                mind_level=mind_level,
                targets=sorted_targets,
                score=score,
            )

    return best_spell


def _get_best_ability_attack(
    ability: AbilityOffensive,
    source: Character,
    targets: list[Character],
    variables: list[VarInfo] = [],
    max_targets: int = 0,
) -> AbilitySelection | None:
    """
    Prioritizes targets for offensive abilities.

    Args:
        ability (AbilityOffensive):
            The offensive ability being considered.
        source (Character):
            The character using the ability.
        targets (list[Character]):
            List of potential targets.
        variables (list[VarInfo], optional):
            List of variables to consider for the ability.
        max_targets (int, optional):
            Maximum number of targets to consider.

    Returns:
        AbilitySelection | None:
            The best ability the source can use, or None if no valid targets
            are found.

    """
    variables = source.get_expression_variables()

    max_targets = ability.target_count(variables)
    if max_targets <= 0:
        return None

    sorted_targets = _sort_targets_by_usefulness_and_hp_offensive(
        action=ability,
        source=source,
        targets=targets,
        variables=variables,
        max_targets=max_targets,
    )
    if not sorted_targets:
        return None

    total_affected = len(sorted_targets)
    score = total_affected
    return AbilitySelection(
        ability=ability,
        targets=sorted_targets,
        score=score,
    )


def _get_best_ability_heal(
    ability: AbilityHeal,
    source: Character,
    targets: list[Character],
) -> AbilitySelection | None:
    """
    Returns targets sorted by usefulness and HP for healing abilities.

    Args:
        ability (AbilityHeal):
            The healing ability being considered.
        source (Character):
            The character using the ability.
        targets (list[Character]):
            List of potential targets.

    Returns:
        AbilitySelection | None:
            The best ability the source can use, or None if no valid targets
            are found.

    """
    variables = source.get_expression_variables()

    max_targets = ability.target_count(variables)
    if max_targets <= 0:
        return None

    sorted_targets = _sort_targets_by_usefulness_and_hp_healing(
        action=ability,
        source=source,
        targets=targets,
        variables=variables,
        max_targets=max_targets,
    )
    if not sorted_targets:
        return None

    total_affected = len(sorted_targets)
    score = total_affected
    return AbilitySelection(
        ability=ability,
        targets=sorted_targets,
        score=score,
    )


def _get_best_ability_buff_or_debuff(
    ability: AbilityBuff | AbilityDebuff,
    source: Character,
    targets: list[Character],
) -> AbilitySelection | None:
    """
    Returns targets sorted by usefulness for buff or debuff abilities.

    Args:
        ability (AbilityBuff | AbilityDebuff):
            The buff or debuff ability being considered.
        source (Character):
            The character using the ability.
        targets (list[Character]):
            List of potential targets.

    Returns:
        AbilitySelection | None:
            The best ability the source can use, or None if no valid targets
            are found.

    """
    variables = source.get_expression_variables()

    max_targets = ability.target_count(variables)
    if max_targets <= 0:
        return None

    sorted_targets = _sort_targets_by_usefulness_and_buff(
        action=ability,
        source=source,
        targets=targets,
        variables=variables,
        max_targets=max_targets,
    )
    if not sorted_targets:
        return None

    total_affected = len(sorted_targets)
    score = total_affected
    return AbilitySelection(
        ability=ability,
        targets=sorted_targets,
        score=score,
    )


# =============================================================================
# Improved AI Functions - Split Weapon and Target Selection
# =============================================================================


def get_weapon_attacks(source: Character) -> list["WeaponAttack"]:
    """
    Get available weapon attacks for a character.

    Args:
        source (Character): The character to get weapon attacks for.

    Returns:
        list[WeaponAttack]: List of available weapon attacks.

    """
    return source.get_available_weapon_attacks()


def get_natural_attacks(source: Character) -> list["NaturalAttack"]:
    """
    Get available natural attacks for a character.

    Args:
        source (Character): The character to get natural attacks for.

    Returns:
        list[NaturalAttack]: List of available natural attacks.

    """
    return source.get_available_natural_weapon_attacks()


# =============================================================================
# Public API
# =============================================================================


def get_all_combat_actions(source: Character) -> list[BaseAction]:
    """
    Get all available combat actions for a character.

    Args:
        source (Character): The character to get combat actions for.

    Returns:
        list[BaseAction]: List of all available combat actions including attacks, actions, and spells.

    """
    return (
        source.get_available_attacks()
        + source.get_available_actions()
        + source.get_available_spells()
    )


def get_actions_by_type(source: Character, action_class: type) -> list[Any]:
    """
    Generic function to get actions of a specific type.

    Args:
        source (Character): The character to get actions for.
        action_class (type): The class of action to filter for.

    Returns:
        list[Any]: List of actions of the specified type.

    """
    return [a for a in get_all_combat_actions(source) if isinstance(a, action_class)]


def choose_best_weapon_for_situation(
    source: Character,
    weapons: list[WeaponAttack],
    enemies: list[Character],
) -> WeaponAttack | None:
    """
    Choose the best weapon type based on overall battlefield effectiveness.

    This separates weapon selection from target selection for better performance.

    Args:
        source (Character):
            The NPC making the decision.
        weapons (list[WeaponAttack]):
            List of available weapon attacks.
        enemies (list[Character]):
            List of enemy characters.

    Returns:
        WeaponAttack | None:
            The best weapon for the situation, or None if no valid weapon is found.

    """
    if not weapons or not enemies:
        return None

    best_weapon = None
    best_score = -1

    for weapon in weapons:
        # Skip if weapon is on cooldown
        if source.is_on_cooldown(weapon):
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
            if _can_apply_any_effect(
                source=source,
                target=target,
                effects=weapon.effects,
            ):
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
    source: Character,
    attack: BaseAttack,
    enemies: list[Character],
) -> Character | None:
    """
    Choose the best target for a specific attack.

    Args:
        source (Character):
            The NPC making the decision.
        attack (BaseAttack):
            The attack being used.
        enemies (list[Character]):
            List of enemy characters.

    Returns:
        Character | None:
            The best target for the attack, or None if no valid target is found.

    """
    if not attack or not enemies:
        return None

    # Use existing sorting logic but only for this attack
    best_attack = _get_best_base_attack(
        attack=attack,
        source=source,
        targets=enemies,
    )
    if not best_attack:
        return None

    # Find the first alive target.
    for target in best_attack.targets:
        if target.is_alive():
            return target

    return None


def choose_best_base_attack_action(
    source: Character,
    enemies: list[Character],
    base_attacks: list[BaseAttack],
) -> AttackSelection | None:
    """
    Chooses the best attack and target combo based on:
        - Usefulness of the attack's effect (if any)
        - Target vulnerability (low HP)
        - Number of damage components

    Args:
        source (Character):
            The NPC making the decision.
        enemies (list[Character]):
            List of enemy characters.
        base_attacks (list[BaseAttack]):
            List of available base attacks.

    Returns:
        tuple[BaseAttack, Character] | None:
            The best attack and target combo, or None if no valid combo is found.

    """
    best_attack: AttackSelection | None = None

    for attack in base_attacks:
        if source.is_on_cooldown(attack):
            continue
        candidate_attack = _get_best_base_attack(
            attack=attack,
            source=source,
            targets=enemies,
        )
        if not candidate_attack:
            continue
        if not best_attack or candidate_attack.score > best_attack.score:
            best_attack = candidate_attack

    return best_attack


def choose_best_attack_spell_action(
    source: Character,
    enemies: list[Character],
    spells: list[SpellOffensive],
) -> SpellSelection | None:
    """
    Chooses the best SpellOffensive, mind level, and list of targets based on
    usefulness and value.

    Args:
        source (Character):
            The NPC making the decision.
        enemies (list[Character]):
            List of enemy characters.
        spells (list[SpellOffensive]):
            List of available offensive spells.

    Returns:
        SpellSelection | None:
            The best spell the source can cast, or None if no viable spell
            is found.

    """
    best_spell: SpellSelection | None = None

    for spell in spells:
        if source.is_on_cooldown(spell):
            continue
        candidate_spell = _get_best_spell_attack(
            spell=spell,
            source=source,
            targets=enemies,
        )
        if not candidate_spell:
            continue
        if not best_spell or candidate_spell.score > best_spell.score:
            best_spell = candidate_spell

    return best_spell


def choose_best_healing_spell_action(
    source: Character,
    allies: list[Character],
    spells: list[SpellHeal],
) -> SpellSelection | None:
    """
    Chooses the best healing spell, mind level, and set of targets based on:
    - Amount of HP missing.
    - Number of wounded targets.
    - Usefulness of HoT effect (if any).
    - Mind cost efficiency.

    Args:
        source (Character): The NPC making the decision.
        allies (list[Character]): List of friendly characters.
        spells (list[SpellHeal]): List of available healing spells.

    Returns:
        SpellSelection | None:
            The best spell the source can cast, or None if no viable spell is found.

    """
    best_spell: SpellSelection | None = None

    for spell in spells:
        if not spell.mind_cost:
            continue
        if source.is_on_cooldown(spell):
            continue
        candidate_spell = _get_best_spell_heal(
            spell=spell,
            source=source,
            targets=allies,
        )
        if not candidate_spell:
            continue
        if not best_spell or candidate_spell.score > best_spell.score:
            best_spell = candidate_spell

    return best_spell


def choose_best_buff_or_debuff_spell_action(
    source: Character,
    targets: list[Character],
    spells: list[SpellBuff] | list[SpellDebuff],
) -> SpellSelection | None:
    """
    Chooses the best SpellBuff or SpellDebuff, mind level, and set of targets
    based on:
        - Usefulness of the buff effect.
        - Number of allies affected.
        - Mind cost efficiency.

    Args:
        source (Character):
            The NPC making the decision.
        allies (list[Character]):
            List of friendly characters.
        spells (list[SpellBuff] | list[SpellDebuff]):
            List of available buff spells.

    Returns:
        SpellSelection | None:
            The best spell the source can cast, or None if no viable spell is
            found.

    """
    best_spell: SpellSelection | None = None

    for spell in spells:
        if not spell.mind_cost:
            continue
        if source.is_on_cooldown(spell):
            continue
        candidate_spell = _get_best_spell_buff_or_debuff(
            spell=spell,
            source=source,
            targets=targets,
        )
        if not candidate_spell:
            continue
        if not best_spell or candidate_spell.score > best_spell.score:
            best_spell = candidate_spell

    return best_spell


# =============================================================================
# Ability AI Functions
# =============================================================================


def choose_best_offensive_ability_action(
    source: Character,
    enemies: list[Character],
    abilities: list[AbilityOffensive],
) -> AbilitySelection | None:
    """
    Chooses the best offensive ability and targets (no mind cost).

    Args:
        source (Character):
            The NPC making the decision.
        enemies (list[Character]):
            List of enemy characters.
        abilities (list[AbilityOffensive]):
            List of available offensive abilities.

    Returns:
        AbilitySelection | None:
            The best ability the source can use, or None if no viable ability is
            found.

    """
    best_ability: AbilitySelection | None = None

    for ability in abilities:
        if source.is_on_cooldown(ability):
            continue
        candidate_ability = _get_best_ability_attack(
            ability=ability,
            source=source,
            targets=enemies,
        )
        if not candidate_ability:
            continue
        if not best_ability or candidate_ability.score > best_ability.score:
            best_ability = candidate_ability

    return best_ability


def choose_best_healing_ability_action(
    source: Character,
    allies: list[Character],
    abilities: list[AbilityHeal],
) -> AbilitySelection | None:
    """
    Chooses the best healing ability and targets (no mind cost).

    Args:
        source (Character):
            The NPC making the decision.
        allies (list[Character]):
            List of friendly characters.
        abilities (list[AbilityHeal]):
            List of available healing abilities.

    Returns:
        AbilitySelection | None:
            The best ability the source can use, or None if no viable ability is
            found.

    """
    best_ability: AbilitySelection | None = None

    for ability in abilities:
        if source.is_on_cooldown(ability):
            continue
        candidate_ability = _get_best_ability_heal(
            ability=ability,
            source=source,
            targets=allies,
        )
        if not candidate_ability:
            continue
        if not best_ability or candidate_ability.score > best_ability.score:
            best_ability = candidate_ability

    return best_ability


def choose_best_buff_or_debuff_ability_action(
    source: Character,
    targets: list[Character],
    abilities: list[AbilityBuff] | list[AbilityDebuff],
) -> AbilitySelection | None:
    """
    Chooses the best buff or debuff ability and targets (no mind cost).

    Args:
        source (Character):
            The NPC making the decision.
        targets (list[Character]):
            List of potential targets (allies or enemies).
        abilities (list[AbilityBuff] | list[AbilityDebuff]):
            List of available buff or debuff abilities.

    Returns:
        AbilitySelection | None:
            The best ability the source can use, or None if no viable ability is
            found.

    """
    best_ability: AbilitySelection | None = None

    for ability in abilities:
        if source.is_on_cooldown(ability):
            continue
        candidate_ability = _get_best_ability_buff_or_debuff(
            ability=ability,
            source=source,
            targets=targets,
        )
        if not candidate_ability:
            continue
        if not best_ability or candidate_ability.score > best_ability.score:
            best_ability = candidate_ability

    return best_ability
