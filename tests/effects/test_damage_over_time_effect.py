"""
Tests for damage over time effects in the effects system.
"""

import pytest
from character.character_class import CharacterClass
from character.character_race import CharacterRace
from character.main import Character
from combat.damage import DamageComponent
from core.constants import CharacterType, DamageType
from effects.damage_over_time_effect import (
    ActiveDamageOverTimeEffect,
    DamageOverTimeEffect,
)
from effects.event_system import CombatEvent, EventType, TurnEndEvent


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
            "STRENGTH": 14,
            "DEXTERITY": 15,
            "CONSTITUTION": 15,
            "INTELLIGENCE": 16,
            "WISDOM": 14,
            "CHARISMA": 18,
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
            "STRENGTH": 14,
            "DEXTERITY": 15,
            "CONSTITUTION": 15,
            "INTELLIGENCE": 16,
            "WISDOM": 14,
            "CHARISMA": 18,
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
def poison_dot():
    """A sample poison damage over time effect."""
    damage = DamageComponent(
        damage_roll="2d6",
        damage_type=DamageType.POISON,
    )
    return DamageOverTimeEffect(
        name="Poison",
        description="Deals poison damage each turn",
        duration=3,
        damage=damage,
    )


@pytest.fixture
def fire_dot():
    """A sample fire damage over time effect."""
    damage = DamageComponent(
        damage_roll="1d4+1",
        damage_type=DamageType.FIRE,
    )
    return DamageOverTimeEffect(
        name="Burning",
        description="Deals fire damage each turn",
        duration=2,
        damage=damage,
    )


def test_can_apply_dot_success(attacker, target, poison_dot):
    """
    Test that a DoT effect can be applied successfully under normal conditions.
    """
    variables = attacker.get_expression_variables()
    assert poison_dot.can_apply(attacker, target, variables)


def test_can_apply_dot_self_targeting_fails(attacker, poison_dot):
    """
    Test that a DoT effect cannot be applied to self.
    """
    variables = attacker.get_expression_variables()
    assert not poison_dot.can_apply(attacker, attacker, variables)


def test_can_apply_dot_immunity_fails(attacker, target, poison_dot):
    """
    Test that a DoT effect cannot be applied if target is immune to the damage type.
    """
    target.immunities.add(DamageType.POISON)
    variables = attacker.get_expression_variables()
    assert not poison_dot.can_apply(attacker, target, variables)


def test_can_apply_dot_stacking_limit_fails(attacker, target, poison_dot, fire_dot):
    """
    Test that a DoT effect cannot be applied if target already has 3 or more DoT effects.
    """
    # Apply 3 different DoT effects first
    poison_dot.apply_effect(attacker, target, attacker.get_expression_variables())
    fire_dot.apply_effect(attacker, target, attacker.get_expression_variables())

    # Create and apply a third DoT effect
    damage3 = DamageComponent(damage_roll="1", damage_type=DamageType.COLD)
    dot3 = DamageOverTimeEffect(
        name="Cold", description="Cold damage", duration=1, damage=damage3
    )
    dot3.apply_effect(attacker, target, attacker.get_expression_variables())

    # Now try to apply a fourth - should fail
    damage4 = DamageComponent(damage_roll="1", damage_type=DamageType.ACID)
    dot4 = DamageOverTimeEffect(
        name="Acid", description="Acid damage", duration=1, damage=damage4
    )
    variables = attacker.get_expression_variables()
    assert not dot4.can_apply(attacker, target, variables)


def test_can_apply_dot_refresh_existing_success(attacker, target, poison_dot):
    """
    Test that applying the same DoT effect again refreshes its duration.
    """
    variables = attacker.get_expression_variables()

    # Apply once
    assert poison_dot.can_apply(attacker, target, variables)
    poison_dot.apply_effect(attacker, target, variables)

    # Should still be able to apply (refresh)
    assert poison_dot.can_apply(attacker, target, variables)


def test_apply_dot_success(attacker, target, poison_dot):
    """
    Test successful application of a DoT effect.
    """
    variables = attacker.get_expression_variables()
    success = poison_dot.apply_effect(attacker, target, variables)
    assert success

    # Check that an ActiveDamageOverTimeEffect was added
    dot_effects = list(target.effects.damage_over_time_effects)
    assert len(dot_effects) == 1
    assert dot_effects[0].effect == poison_dot
    assert dot_effects[0].duration == 3


def test_apply_dot_refresh_duration(attacker, target, poison_dot):
    """
    Test that applying the same DoT effect refreshes its duration.
    """
    variables = attacker.get_expression_variables()

    # Apply once
    poison_dot.apply_effect(attacker, target, variables)
    initial_active = list(target.effects.damage_over_time_effects)[0]

    # Apply again - should refresh duration
    success = poison_dot.apply_effect(attacker, target, variables)
    assert success

    # Should still have only one effect, with refreshed duration
    dot_effects = list(target.effects.damage_over_time_effects)
    assert len(dot_effects) == 1
    assert dot_effects[0] is initial_active  # Same instance
    assert dot_effects[0].duration == 3  # Refreshed


def test_active_dot_on_turn_end_deals_damage(attacker, target, poison_dot, mocker):
    """
    Test that active DoT effect deals damage on turn end.
    """
    # Mock roll_and_describe to return a fixed damage
    mock_outcome = mocker.Mock()
    mock_outcome.value = 5
    mock_outcome.description = "5"
    mocker.patch(
        "effects.damage_over_time_effect.roll_and_describe", return_value=mock_outcome
    )

    # Mock target's take_damage method
    mock_take_damage = mocker.patch.object(
        target, "take_damage", return_value=(5, 5, 5)
    )

    # Apply the effect
    variables = attacker.get_expression_variables()
    poison_dot.apply_effect(attacker, target, variables)
    active_dot = list(target.effects.damage_over_time_effects)[0]

    # Create TurnEndEvent
    turn_end_event = TurnEndEvent(source=target, turn_number=1)

    # Trigger on_event
    response = active_dot.on_event(turn_end_event)

    # Verify damage was dealt
    mock_take_damage.assert_called_once_with(5, DamageType.POISON)

    # Verify response
    assert response is not None
    assert not response.remove_effect
    assert response.new_effects == []
    assert response.damage_bonus == []
    assert response.message == ""

    # Duration should decrement
    assert active_dot.duration == 2


def test_active_dot_expires_after_duration(attacker, target, poison_dot, mocker):
    """
    Test that DoT effect expires after its duration.
    """
    # Mock roll_and_describe
    mock_outcome = mocker.Mock()
    mock_outcome.value = 3
    mock_outcome.description = "3"
    mocker.patch(
        "effects.damage_over_time_effect.roll_and_describe", return_value=mock_outcome
    )

    mocker.patch.object(target, "take_damage", return_value=(3, 3, 3))

    # Apply effect with duration 1
    poison_dot.duration = 1
    variables = attacker.get_expression_variables()
    poison_dot.apply_effect(attacker, target, variables)
    active_dot = list(target.effects.damage_over_time_effects)[0]

    # Trigger turn end
    turn_end_event = TurnEndEvent(source=target, turn_number=1)
    response = active_dot.on_event(turn_end_event)

    # Should remove effect
    assert response.remove_effect
    assert active_dot.duration == 0


def test_active_dot_no_response_to_other_events(attacker, target, poison_dot):
    """
    Test that active DoT effect only responds to TurnEndEvent.
    """
    variables = attacker.get_expression_variables()
    poison_dot.apply_effect(attacker, target, variables)
    active_dot = list(target.effects.damage_over_time_effects)[0]

    # Create a mock event that is not TurnEndEvent
    mock_event = CombatEvent(event_type=EventType.ON_HIT, source=target)
    response = active_dot.on_event(mock_event)
    assert response is None


def test_dot_damage_validation_negative_damage(attacker, target, poison_dot, mocker):
    """
    Test that negative damage from roll raises ValueError.
    """
    mock_outcome = mocker.Mock()
    mock_outcome.value = -1
    mocker.patch(
        "effects.damage_over_time_effect.roll_and_describe", return_value=mock_outcome
    )

    variables = attacker.get_expression_variables()
    poison_dot.apply_effect(attacker, target, variables)
    active_dot = list(target.effects.damage_over_time_effects)[0]

    turn_end_event = TurnEndEvent(source=target, turn_number=1)

    with pytest.raises(ValueError, match="Damage value must be non-negative"):
        active_dot.on_event(turn_end_event)


def test_dot_model_validation_invalid_duration():
    """
    Test that DoT effect with invalid duration raises ValueError.
    """
    damage = DamageComponent(damage_roll="1d6", damage_type=DamageType.POISON)

    with pytest.raises(ValueError, match="Duration must be a positive integer"):
        DamageOverTimeEffect(
            name="Test",
            description="Test",
            duration=0,
            damage=damage,
        )


def test_dot_model_validation_invalid_damage():
    """
    Test that DoT effect with invalid damage raises ValueError.
    """
    with pytest.raises(ValueError):
        DamageOverTimeEffect(
            name="Test",
            description="Test",
            duration=1,
            damage="invalid",  # type: ignore
        )
