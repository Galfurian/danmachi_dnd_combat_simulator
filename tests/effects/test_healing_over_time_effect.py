"""
Tests for healing over time effects in the effects system.
"""

import pytest
from character.character_class import CharacterClass
from character.character_race import CharacterRace
from character.main import Character
from core.constants import CharacterType
from effects.event_system import CombatEvent, EventType, TurnEndEvent
from effects.healing_over_time_effect import (
    ActiveHealingOverTimeEffect,
    HealingOverTimeEffect,
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
def regeneration_hot():
    """A sample regeneration healing over time effect."""
    return HealingOverTimeEffect(
        name="Regeneration",
        description="Heals the target each turn",
        duration=3,
        heal_per_turn="2d6",
    )


@pytest.fixture
def cure_wounds_hot():
    """A sample cure wounds healing over time effect."""
    return HealingOverTimeEffect(
        name="Cure Wounds",
        description="Ongoing healing",
        duration=2,
        heal_per_turn="1d4+1",
    )


def test_can_apply_hot_success(attacker, target, regeneration_hot):
    """
    Test that a HoT effect can be applied successfully under normal conditions.
    """
    variables = attacker.get_expression_variables()
    assert regeneration_hot.can_apply(attacker, target, variables)


def test_can_apply_hot_stacking_limit_fails(
    attacker, target, regeneration_hot, cure_wounds_hot
):
    """
    Test that a HoT effect cannot be applied if target already has 3 or more HoT effects.
    """
    # Apply 3 different HoT effects first
    regeneration_hot.apply_effect(attacker, target, attacker.get_expression_variables())
    cure_wounds_hot.apply_effect(attacker, target, attacker.get_expression_variables())

    # Create and apply a third HoT effect
    hot3 = HealingOverTimeEffect(
        name="Blessing", description="Divine healing", duration=1, heal_per_turn="1"
    )
    hot3.apply_effect(attacker, target, attacker.get_expression_variables())

    # Now try to apply a fourth - should fail
    hot4 = HealingOverTimeEffect(
        name="Salve", description="Herbal healing", duration=1, heal_per_turn="1"
    )
    variables = attacker.get_expression_variables()
    assert not hot4.can_apply(attacker, target, variables)


def test_can_apply_hot_refresh_existing_success(attacker, target, regeneration_hot):
    """
    Test that applying the same HoT effect again refreshes its duration.
    """
    variables = attacker.get_expression_variables()

    # Apply once
    assert regeneration_hot.can_apply(attacker, target, variables)
    regeneration_hot.apply_effect(attacker, target, variables)

    # Should still be able to apply (refresh)
    assert regeneration_hot.can_apply(attacker, target, variables)


def test_apply_hot_success(attacker, target, regeneration_hot):
    """
    Test successful application of a HoT effect.
    """
    variables = attacker.get_expression_variables()
    success = regeneration_hot.apply_effect(attacker, target, variables)
    assert success

    # Check that an ActiveHealingOverTimeEffect was added
    hot_effects = list(target.effects.healing_over_time_effects)
    assert len(hot_effects) == 1
    assert hot_effects[0].effect == regeneration_hot
    assert hot_effects[0].duration == 3


def test_apply_hot_refresh_duration(attacker, target, regeneration_hot):
    """
    Test that applying the same HoT effect refreshes its duration.
    """
    variables = attacker.get_expression_variables()

    # Apply once
    regeneration_hot.apply_effect(attacker, target, variables)
    initial_active = list(target.effects.healing_over_time_effects)[0]

    # Apply again - should refresh duration
    success = regeneration_hot.apply_effect(attacker, target, variables)
    assert success

    # Should still have only one effect, with refreshed duration
    hot_effects = list(target.effects.healing_over_time_effects)
    assert len(hot_effects) == 1
    assert hot_effects[0] is initial_active  # Same instance
    assert hot_effects[0].duration == 3  # Refreshed


def test_active_hot_on_turn_end_heals_target(
    attacker, target, regeneration_hot, mocker
):
    """
    Test that active HoT effect heals the target on turn end.
    """
    # Mock roll_and_describe to return a fixed heal
    mock_outcome = mocker.Mock()
    mock_outcome.value = 5
    mock_outcome.description = "5"
    mocker.patch(
        "effects.healing_over_time_effect.roll_and_describe", return_value=mock_outcome
    )

    # Mock target's heal method
    mock_heal = mocker.patch.object(target, "heal", return_value=5)

    # Apply the effect
    variables = attacker.get_expression_variables()
    regeneration_hot.apply_effect(attacker, target, variables)
    active_hot = list(target.effects.healing_over_time_effects)[0]

    # Create TurnEndEvent
    turn_end_event = TurnEndEvent(source=target, turn_number=1)

    # Trigger on_event
    response = active_hot.on_event(turn_end_event)

    # Verify healing was applied
    mock_heal.assert_called_once_with(5)

    # Verify response
    assert response is not None
    assert not response.remove_effect
    assert response.new_effects == []
    assert response.damage_bonus == []
    assert response.message == ""

    # Duration should decrement
    assert active_hot.duration == 2


def test_active_hot_expires_after_duration(attacker, target, regeneration_hot, mocker):
    """
    Test that HoT effect expires after its duration.
    """
    # Mock roll_and_describe
    mock_outcome = mocker.Mock()
    mock_outcome.value = 3
    mock_outcome.description = "3"
    mocker.patch(
        "effects.healing_over_time_effect.roll_and_describe", return_value=mock_outcome
    )

    mocker.patch.object(target, "heal", return_value=3)

    # Apply effect with duration 1
    regeneration_hot.duration = 1
    variables = attacker.get_expression_variables()
    regeneration_hot.apply_effect(attacker, target, variables)
    active_hot = list(target.effects.healing_over_time_effects)[0]

    # Trigger turn end
    turn_end_event = TurnEndEvent(source=target, turn_number=1)
    response = active_hot.on_event(turn_end_event)

    # Should remove effect
    assert response.remove_effect
    assert active_hot.duration == 0


def test_active_hot_no_response_to_other_events(attacker, target, regeneration_hot):
    """
    Test that active HoT effect only responds to TurnEndEvent.
    """
    variables = attacker.get_expression_variables()
    regeneration_hot.apply_effect(attacker, target, variables)
    active_hot = list(target.effects.healing_over_time_effects)[0]

    # Create a mock event that is not TurnEndEvent
    mock_event = CombatEvent(event_type=EventType.ON_HIT, source=target)
    response = active_hot.on_event(mock_event)
    assert response is None


def test_hot_heal_validation_negative_heal(attacker, target, regeneration_hot, mocker):
    """
    Test that negative heal from roll raises ValueError.
    """
    mock_outcome = mocker.Mock()
    mock_outcome.value = -1
    mocker.patch(
        "effects.healing_over_time_effect.roll_and_describe", return_value=mock_outcome
    )

    variables = attacker.get_expression_variables()
    regeneration_hot.apply_effect(attacker, target, variables)
    active_hot = list(target.effects.healing_over_time_effects)[0]

    turn_end_event = TurnEndEvent(source=target, turn_number=1)

    with pytest.raises(ValueError, match="Heal value must be non-negative"):
        active_hot.on_event(turn_end_event)


def test_hot_model_validation_invalid_duration():
    """
    Test that HoT effect with invalid duration raises ValueError.
    """
    with pytest.raises(ValueError, match="Duration must be a positive integer"):
        HealingOverTimeEffect(
            name="Test",
            description="Test",
            duration=0,
            heal_per_turn="1d6",
        )
