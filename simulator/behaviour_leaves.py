from typing import Any, Iterable
from behaviour_tree import Action, Condition, BTStatus
from constants import *
from character import Character
from actions import *


def _can_cast_spell(character: Character, spell: Spell, mind_level: int = -1) -> bool:
    mind_level = mind_level if mind_level >= 0 else spell.mind_cost[0]
    return character.mind >= mind_level


def _find_healing_spell(
    character: Character, single_target: bool
) -> Optional[SpellHeal]:
    return next(
        (
            s
            for s in character.spells.values()
            if isinstance(s, SpellHeal)
            and s.is_single_target() is single_target
            and _can_cast_spell(character, s)
        ),
        None,
    )


def _ideal_heal_mind(caster: Character, target: Character, spell: SpellHeal) -> int:
    """
    Returns the cheapest Mind level that fully heals *target*,
    or -1 if the caster cannot afford any level.
    """
    # Bail early if the base level is unaffordable
    if not _can_cast_spell(caster, spell):
        return -1
    best_affordable = -1
    for mind_level in spell.mind_cost:
        if _can_cast_spell(caster, spell, mind_level):
            heal = get_max_roll(spell.heal_roll, caster, mind_level)
            if target.hp <= heal:
                return mind_level
            # Remember highest we can pay.
            best_affordable = mind_level
    return best_affordable


def _ideal_group_heal_mind(
    caster: Character,
    targets: Iterable[Character],
    spell: SpellHeal,
) -> int:
    """
    Returns the cheapest Mind level that will fully heal *every*
    wounded ally in *targets*.  If none of the affordable levels
    achieve that, returns the highest affordable level instead.
    A value of -1 means the caster cannot pay even the base cost.
    """
    # Build a list of injured allies only
    injured = [t for t in targets if t.hp < t.HP_MAX]
    # nothing to heal.
    if not injured:
        return -1
    # Largest single deficit drives the requirement
    max_missing = max(t.HP_MAX - t.hp for t in injured)
    # Candidate Mind levels, ascending (base cost first)
    best_affordable = -1
    for mind_level in spell.mind_cost:
        if not _can_cast_spell(caster, spell, mind_level):
            continue  # can’t pay this one
        best_affordable = mind_level  # remember latest
        heal_amt = get_max_roll(spell.heal_roll, caster, mind_level)
        if heal_amt >= max_missing:  # ✔ covers everybody
            return mind_level
    return best_affordable  # strongest we can afford


def _find_weapon(character: Character) -> WeaponAttack | None:
    for weapon in character.equipped_weapons:
        if isinstance(weapon, WeaponAttack):
            return weapon
    return None


def hp_below_30(ctx: Any) -> bool:
    self = ctx["self"]
    return self.hp <= 0.3 * self.HP_MAX


def hp_below_70(ctx: Any) -> bool:
    self = ctx["self"]
    return self.hp <= 0.7 * self.HP_MAX


def pick_lowest_hp_target(ctx: Any) -> BTStatus:
    enemies: list[Character] = ctx["enemies"]
    if not enemies:
        return BTStatus.FAILURE
    ctx["bb"]["target"] = min(enemies, key=lambda f: f.hp)
    return BTStatus.SUCCESS


def pick_highest_hp_target(ctx: Any) -> BTStatus:
    enemies: list[Character] = ctx["enemies"]
    if not enemies:
        return BTStatus.FAILURE
    ctx["bb"]["target"] = max(enemies, key=lambda f: f.hp)
    return BTStatus.SUCCESS


def filter_lowest_hp_candidates(ctx: Any) -> BTStatus:
    enemies = ctx["bb"].get("candidates", [])
    if not enemies:
        enemies: list[Character] = ctx["enemies"]
        if not enemies:
            return BTStatus.FAILURE
    min_hp = min(f.hp for f in enemies)
    ctx["bb"]["candidates"] = [f for f in enemies if f.hp == min_hp]
    return BTStatus.SUCCESS


def filter_highest_hp_candidates(ctx: Any) -> BTStatus:
    enemies = ctx["bb"].get("candidates", [])
    if not enemies:
        enemies: list[Character] = ctx["enemies"]
        if not enemies:
            return BTStatus.FAILURE
    max_hp = max(f.hp for f in enemies)
    ctx["bb"]["candidates"] = [f for f in enemies if f.hp == max_hp]
    return BTStatus.SUCCESS


def filter_lowest_ac_candidates(ctx: Any) -> BTStatus:
    enemies = ctx["bb"].get("candidates", [])
    if not enemies:
        enemies: list[Character] = ctx["enemies"]
        if not enemies:
            return BTStatus.FAILURE
    min_ac = min(f.AC for f in enemies)
    ctx["bb"]["candidates"] = [f for f in enemies if f.AC == min_ac]
    return BTStatus.SUCCESS


def filter_highest_ac_candidates(ctx: Any) -> BTStatus:
    enemies = ctx["bb"].get("candidates", [])
    if not enemies:
        enemies: list[Character] = ctx["enemies"]
        if not enemies:
            return BTStatus.FAILURE
    max_ac = max(f.AC for f in enemies)
    ctx["bb"]["candidates"] = [f for f in enemies if f.AC == max_ac]
    return BTStatus.SUCCESS


def heal_self(ctx: Any) -> BTStatus:
    self = ctx["self"]
    # Find a self-heal spell.
    spell = _find_healing_spell(self, True)
    if not spell:
        return BTStatus.FAILURE
    # Get the ideal Mind level for the heal.
    mind_level = _ideal_heal_mind(self, self, spell)
    if mind_level == -1:
        return BTStatus.FAILURE
    # Cast the spell on self.
    spell.cast_spell(self, self, mind_level)
    # Remove the mind.
    self.mind -= mind_level
    return BTStatus.SUCCESS


def group_heal(ctx: Any) -> BTStatus:
    self = ctx["self"]
    allies = ctx["allies"]
    # Find a group heal spell.
    spell = _find_healing_spell(self, False)
    if not spell:
        return BTStatus.FAILURE
    # Get the ideal Mind level for the group heal.
    mind_level = _ideal_group_heal_mind(self, allies, spell)
    if mind_level == -1:
        return BTStatus.FAILURE
    # Get the number of targets that we can heal.
    max_targets = evaluate_expression(spell.multi_target_expr, self, mind_level)
    # Get the targets with the lowest HP.
    targets = sorted(allies, key=lambda f: f.hp)[:max_targets]
    if not targets:
        return BTStatus.FAILURE
    # Heal each target.
    for target in targets:
        spell.cast_spell(self, target, mind_level)
    # Remove the mind.
    self.mind -= mind_level
    return BTStatus.SUCCESS


def swing_weapon_current_target(ctx: Any) -> BTStatus:
    self = ctx["self"]
    weapon = _find_weapon(self)
    if not weapon:
        return BTStatus.FAILURE
    target = ctx["bb"].get("target")
    if not target:
        return BTStatus.FAILURE
    weapon.execute(self, target)
    return BTStatus.SUCCESS


COND_LOW_HP = Condition(hp_below_30, "Low HP?")
COND_HIGH_HP = Condition(hp_below_70, "High HP?")

ACT_HEAL_SELF = Action(heal_self, "Heal Self")
ACT_GROUP_HEAL = Action(group_heal, "Group Heal")

ACT_SWING_WEAPON = Action(swing_weapon_current_target, "Swing Weapon")

PICK_LOWEST_HP_TARGET = Action(pick_lowest_hp_target, "Pick Min HP")
PICK_HIGHEST_HP_TARGET = Action(pick_highest_hp_target, "Pick Max HP")

FILTER_LOWEST_HP_CANDIDATES = Action(filter_lowest_hp_candidates, "Filter Min HP")
FILTER_HIGHEST_HP_CANDIDATES = Action(filter_highest_hp_candidates, "Filter Max HP")
FILTER_LOWEST_AC_CANDIDATES = Action(filter_lowest_ac_candidates, "Filter Min AC")
FILTER_HIGHEST_AC_CANDIDATES = Action(filter_highest_ac_candidates, "Filter Max AC")
