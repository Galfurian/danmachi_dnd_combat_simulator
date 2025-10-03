"""
Tests for modifier effects in the effects system.
"""

import pytest
from character.character_class import CharacterClass
from character.character_race import CharacterRace
from character.main import Character
from combat.damage import DamageComponent
from core.constants import BonusType, CharacterType, DamageType
from effects.event_system import CombatEvent, EventType, TurnEndEvent
from effects.modifier_effect import (
    ActiveModifierEffect,
    Modifier,
    ModifierEffect,
)


@pytest.fixture
def sample_race():
    return CharacterRace(
        name="Human",
        natural_ac=0,
        default_actions=[],
        default_spells=[],
    )


@pytest.fixture
def sample_class():
    return CharacterClass(
        name="Fighter",
        hp_mult=10,
        mind_mult=0,
        actions_by_level={},
        spells_by_level={},
    )


@pytest.fixture
def attacker(sample_race, sample_class):
    return Character(
        char_type=CharacterType.PLAYER,
        name="Attacker",
        race=sample_race,
        levels={sample_class: 1},
        stats={
            "strength": 14,
            "dexterity": 15,
            "constitution": 15,
            "intelligence": 16,
            "wisdom": 14,
            "charisma": 18,
        },
        spellcasting_ability=None,
        total_hands=2,
        immunities=set(),
        resistances=set(),
        vulnerabilities=set(),
        number_of_attacks=1,
        passive_effects=[],
    )


@pytest.fixture
def target(sample_race, sample_class):
    return Character(
        char_type=CharacterType.ENEMY,
        name="Target",
        race=sample_race,
        levels={sample_class: 1},
        stats={
            "strength": 14,
            "dexterity": 15,
            "constitution": 15,
            "intelligence": 16,
            "wisdom": 14,
            "charisma": 18,
        },
        spellcasting_ability=None,
        total_hands=2,
        immunities=set(),
        resistances=set(),
        vulnerabilities=set(),
        number_of_attacks=1,
        passive_effects=[],
    )


@pytest.fixture
def ac_modifier():
    """A sample AC modifier."""
    return Modifier(bonus_type=BonusType.AC, value="2")


@pytest.fixture
def hp_modifier():
    """A sample HP modifier."""
    return Modifier(bonus_type=BonusType.HP, value="10")


@pytest.fixture
def damage_modifier():
    """A sample damage modifier."""
    return Modifier(
        bonus_type=BonusType.DAMAGE,
        value=DamageComponent(damage_roll="1d6", damage_type=DamageType.FIRE),
    )


@pytest.fixture
def ac_buff(ac_modifier):
    """A sample AC buff effect."""
    return ModifierEffect(
        name="Shield of Faith",
        description="AC bonus from divine protection",
        duration=3,
        modifiers=[ac_modifier],
    )


@pytest.fixture
def hp_buff(hp_modifier):
    """A sample HP buff effect."""
    return ModifierEffect(
        name="Blessing",
        description="HP bonus from blessing",
        duration=2,
        modifiers=[hp_modifier],
    )


@pytest.fixture
def damage_buff(damage_modifier):
    """A sample damage buff effect."""
    return ModifierEffect(
        name="Fire Weapon",
        description="Weapon deals extra fire damage",
        duration=5,
        modifiers=[damage_modifier],
    )


def test_modifier_creation_string_value(ac_modifier):
    """Test creating a modifier with string value."""
    assert ac_modifier.bonus_type == BonusType.AC
    assert ac_modifier.value == "2"
    assert ac_modifier.stacks is False  # AC modifiers don't stack


def test_modifier_creation_damage_component(damage_modifier):
    """Test creating a modifier with DamageComponent value."""
    assert damage_modifier.bonus_type == BonusType.DAMAGE
    assert isinstance(damage_modifier.value, DamageComponent)
    assert damage_modifier.stacks is True  # Damage modifiers stack


def test_modifier_stacking_rules():
    """Test that different bonus types have different stacking rules."""
    ac_mod = Modifier(bonus_type=BonusType.AC, value="1")
    attack_mod = Modifier(bonus_type=BonusType.ATTACK, value="1")
    damage_mod = Modifier(
        bonus_type=BonusType.DAMAGE,
        value=DamageComponent(damage_roll="1", damage_type=DamageType.FIRE),
    )

    assert not ac_mod.stacks  # AC doesn't stack
    assert attack_mod.stacks  # Attack stacks
    assert damage_mod.stacks  # Damage stacks


def test_modifier_validation_invalid_damage_type():
    """Test that DAMAGE bonus type requires DamageComponent."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Modifier(bonus_type=BonusType.DAMAGE, value="1d6")


def test_modifier_validation_non_damage_string():
    """Test that non-DAMAGE bonus types require string values."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        damage_comp = DamageComponent(damage_roll="1d6", damage_type=DamageType.FIRE)
        Modifier(bonus_type=BonusType.AC, value=damage_comp)


def test_modifier_projected_strength_string(mocker):
    """Test projected strength calculation for string modifiers."""
    modifier = Modifier(bonus_type=BonusType.AC, value="2d6+3")
    variables = []

    mock_get_max_roll = mocker.patch(
        "effects.modifier_effect.get_max_roll", return_value=15
    )
    strength = modifier.get_projected_strength(variables)

    mock_get_max_roll.assert_called_once_with("2d6+3", variables)
    assert strength == 15


def test_modifier_projected_strength_damage_component(mocker):
    """Test projected strength calculation for DamageComponent modifiers."""
    damage_comp = DamageComponent(damage_roll="1d8+2", damage_type=DamageType.FIRE)
    modifier = Modifier(bonus_type=BonusType.DAMAGE, value=damage_comp)
    variables = []

    mock_get_max_roll = mocker.patch(
        "effects.modifier_effect.get_max_roll", return_value=10
    )
    strength = modifier.get_projected_strength(variables)

    mock_get_max_roll.assert_called_once_with("1d8+2", variables)
    assert strength == 10


def test_modifier_equality():
    """Test modifier equality comparison."""
    mod1 = Modifier(bonus_type=BonusType.AC, value="2")
    mod2 = Modifier(bonus_type=BonusType.AC, value="2")
    mod3 = Modifier(bonus_type=BonusType.AC, value="3")

    assert mod1 == mod2
    assert mod1 != mod3
    assert mod1 != "not a modifier"


def test_modifier_hash():
    """Test modifier hashing for use in sets/dicts."""
    mod1 = Modifier(bonus_type=BonusType.AC, value="2")
    mod2 = Modifier(bonus_type=BonusType.AC, value="2")
    mod3 = Modifier(bonus_type=BonusType.AC, value="3")

    # Same modifiers should have same hash
    assert hash(mod1) == hash(mod2)
    assert hash(mod1) != hash(mod3)

    # Should work in sets
    mod_set = {mod1, mod2, mod3}
    assert len(mod_set) == 2  # mod1 and mod2 are the same


def test_modifier_effect_creation(ac_buff):
    """Test creating a modifier effect."""
    assert ac_buff.name == "Shield of Faith"
    assert ac_buff.duration == 3
    assert len(ac_buff.modifiers) == 1
    assert ac_buff.modifiers[0].bonus_type == BonusType.AC


def test_modifier_effect_validation_empty_modifiers():
    """Test that modifier effect requires at least one modifier."""
    with pytest.raises(ValueError, match="Modifiers list cannot be empty"):
        ModifierEffect(
            name="Empty",
            description="No modifiers",
            duration=1,
            modifiers=[],
        )


def test_modifier_effect_validation_invalid_modifier():
    """Test that modifier effect validates modifier types."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ModifierEffect(
            name="Invalid",
            description="Invalid modifier",
            duration=1,
            modifiers=["not a modifier"],  # type: ignore
        )


def test_modifier_effect_get_projected_strength(ac_buff):
    """Test getting projected strength for a bonus type."""
    variables = []
    strength = ac_buff.get_projected_strength(BonusType.AC, variables)
    assert strength == 2  # "2" evaluates to 2

    # Non-existent bonus type should return 0
    strength = ac_buff.get_projected_strength(BonusType.ATTACK, variables)
    assert strength == 0


def test_modifier_effect_is_stronger_than(ac_buff, hp_buff, mocker):
    """Test comparing strength between modifier effects."""
    variables = []

    # Mock get_max_roll to control strength values
    mock_get_max_roll = mocker.patch("effects.modifier_effect.get_max_roll")
    mock_get_max_roll.side_effect = lambda expr, vars: (
        int(expr) if expr.isdigit() else 5
    )

    # ac_buff has AC +2, hp_buff has HP +10
    # Both are stronger than each other because each has a unique modifier
    assert ac_buff.is_stronger_than(hp_buff, variables)
    assert hp_buff.is_stronger_than(ac_buff, variables)

    # Create effects with same bonus type but different strengths
    weak_ac = ModifierEffect(
        name="Weak AC",
        description="Weak AC buff",
        duration=1,
        modifiers=[Modifier(bonus_type=BonusType.AC, value="1")],
    )
    strong_ac = ModifierEffect(
        name="Strong AC",
        description="Strong AC buff",
        duration=1,
        modifiers=[Modifier(bonus_type=BonusType.AC, value="3")],
    )

    assert strong_ac.is_stronger_than(weak_ac, variables)
    assert not weak_ac.is_stronger_than(strong_ac, variables)


def test_can_apply_modifier_success(attacker, target, ac_buff):
    """Test that modifier effect can be applied successfully."""
    variables = attacker.get_expression_variables()
    assert ac_buff.can_apply(attacker, target, variables)


def test_can_apply_modifier_stacking_limit(attacker, target, ac_buff):
    """Test that modifier effects have a stacking limit of 5."""
    variables = attacker.get_expression_variables()

    # Apply 5 modifier effects
    for i in range(5):
        effect = ModifierEffect(
            name=f"Buff {i}",
            description=f"Buff {i}",
            duration=1,
            modifiers=[Modifier(bonus_type=BonusType.AC, value="1")],
        )
        effect.apply_effect(attacker, target, variables)

    # Sixth effect should fail
    assert not ac_buff.can_apply(attacker, target, variables)


def test_apply_modifier_success(attacker, target, ac_buff):
    """Test successful application of modifier effect."""
    variables = attacker.get_expression_variables()
    success = ac_buff.apply_effect(attacker, target, variables)
    assert success

    # Check that an ActiveModifierEffect was added
    mod_effects = list(target.effects.modifier_effects)
    assert len(mod_effects) == 1
    assert mod_effects[0].effect == ac_buff
    assert mod_effects[0].duration == 3


def test_active_modifier_get_projected_strength(ac_buff, attacker, target):
    """Test active modifier effect strength calculation."""
    variables = attacker.get_expression_variables()
    ac_buff.apply_effect(attacker, target, variables)

    active_mod = list(target.effects.modifier_effects)[0]
    strength = active_mod.get_projected_strength(BonusType.AC)
    assert strength == 2


def test_active_modifier_on_turn_end_duration(attacker, target, ac_buff):
    """Test that active modifier decrements duration on turn end."""
    variables = attacker.get_expression_variables()
    ac_buff.apply_effect(attacker, target, variables)
    active_mod = list(target.effects.modifier_effects)[0]

    # Create TurnEndEvent
    turn_end_event = TurnEndEvent(source=target, turn_number=1)

    # Trigger on_event
    response = active_mod.on_event(turn_end_event)

    # Verify response
    assert response is not None
    assert not response.remove_effect  # duration was 3, now 2
    assert response.new_effects == []
    assert response.damage_bonus == []

    # Duration should decrement
    assert active_mod.duration == 2


def test_active_modifier_expires_after_duration(attacker, target, ac_buff):
    """Test that modifier effect expires after duration."""
    variables = attacker.get_expression_variables()

    # Apply effect with duration 1
    ac_buff.duration = 1
    ac_buff.apply_effect(attacker, target, variables)
    active_mod = list(target.effects.modifier_effects)[0]

    # Trigger turn end
    turn_end_event = TurnEndEvent(source=target, turn_number=1)
    response = active_mod.on_event(turn_end_event)

    # Should remove effect
    assert response.remove_effect
    assert active_mod.duration == 0


def test_active_modifier_no_response_to_other_events(attacker, target, ac_buff):
    """Test that active modifier effect only responds to TurnEndEvent."""
    variables = attacker.get_expression_variables()
    ac_buff.apply_effect(attacker, target, variables)
    active_mod = list(target.effects.modifier_effects)[0]

    # Create a different event
    other_event = CombatEvent(event_type=EventType.ON_HIT, source=target)
    response = active_mod.on_event(other_event)
    assert response is None


def test_modifier_effect_multiple_modifiers():
    """Test modifier effect with multiple modifiers."""
    modifiers = [
        Modifier(bonus_type=BonusType.AC, value="2"),
        Modifier(bonus_type=BonusType.ATTACK, value="1"),
    ]

    effect = ModifierEffect(
        name="Multi Buff",
        description="Multiple bonuses",
        duration=3,
        modifiers=modifiers,
    )

    assert len(effect.modifiers) == 2

    # Test strength for different bonus types
    variables = []
    assert effect.get_projected_strength(BonusType.AC, variables) == 2
    assert effect.get_projected_strength(BonusType.ATTACK, variables) == 1
    assert effect.get_projected_strength(BonusType.HP, variables) == 0


def test_modifier_damage_component_hash():
    """Test that damage component modifiers hash correctly."""
    damage1 = DamageComponent(damage_roll="1d6", damage_type=DamageType.FIRE)
    damage2 = DamageComponent(damage_roll="1d6", damage_type=DamageType.FIRE)
    damage3 = DamageComponent(damage_roll="1d8", damage_type=DamageType.FIRE)

    mod1 = Modifier(bonus_type=BonusType.DAMAGE, value=damage1)
    mod2 = Modifier(bonus_type=BonusType.DAMAGE, value=damage2)
    mod3 = Modifier(bonus_type=BonusType.DAMAGE, value=damage3)

    # Same damage components should hash the same
    assert hash(mod1) == hash(mod2)
    assert hash(mod1) != hash(mod3)
