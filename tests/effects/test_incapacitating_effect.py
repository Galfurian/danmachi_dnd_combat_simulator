"""
Tests for incapacitating effects in the effects system.
"""

import pytest
from character.character_class import CharacterClass
from character.character_race import CharacterRace
from character.main import Character
from core.constants import StatType, CharacterType, IncapacitationType
from effects.event_system import CombatEvent, DamageTakenEvent, EventType, TurnEndEvent
from effects.incapacitating_effect import (
    ActiveIncapacitatingEffect,
    IncapacitatingEffect,
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
def sleep_effect():
    """A sample sleep incapacitating effect."""
    return IncapacitatingEffect(
        name="Sleep",
        description="Target falls asleep",
        duration=3,
        incapacitation_type=IncapacitationType.SLEEP,
    )


@pytest.fixture
def stun_effect():
    """A sample stun incapacitating effect."""
    return IncapacitatingEffect(
        name="Stunned",
        description="Target is stunned",
        duration=1,
        incapacitation_type=IncapacitationType.STUNNED,
    )


@pytest.fixture
def paralysis_effect():
    """A sample paralysis incapacitating effect."""
    return IncapacitatingEffect(
        name="Paralyzed",
        description="Target is paralyzed",
        duration=2,
        incapacitation_type=IncapacitationType.PARALYZED,
    )


def test_can_apply_incapacitating_success(attacker, target, sleep_effect):
    """
    Test that an incapacitating effect can be applied successfully under normal conditions.
    """
    variables = attacker.get_expression_variables()
    assert sleep_effect.can_apply(attacker, target, variables)


def test_can_apply_incapacitating_self_targeting_fails(attacker, sleep_effect):
    """
    Test that an incapacitating effect cannot be applied to self.
    """
    variables = attacker.get_expression_variables()
    assert not sleep_effect.can_apply(attacker, attacker, variables)


def test_can_apply_incapacitating_stacking_fails(
    attacker, target, sleep_effect, stun_effect
):
    """
    Test that incapacitating effects cannot stack (only one allowed).
    """
    # Apply first effect
    sleep_effect.apply_effect(attacker, target, attacker.get_expression_variables())

    # Try to apply second - should fail
    variables = attacker.get_expression_variables()
    assert not stun_effect.can_apply(attacker, target, variables)


def test_apply_incapacitating_success(attacker, target, sleep_effect):
    """
    Test successful application of an incapacitating effect.
    """
    variables = attacker.get_expression_variables()
    success = sleep_effect.apply_effect(attacker, target, variables)
    assert success

    # Check that an ActiveIncapacitatingEffect was added
    incap_effects = list(target.effects.incapacitating_effects)
    assert len(incap_effects) == 1
    assert incap_effects[0].effect == sleep_effect
    assert incap_effects[0].duration == 3


def test_incapacitating_properties_sleep(sleep_effect):
    """
    Test properties of sleep incapacitating effect.
    """
    assert sleep_effect.prevents_actions()
    assert sleep_effect.prevents_movement()  # sleep prevents movement
    assert sleep_effect.breaks_on_damage()  # sleep breaks on damage


def test_incapacitating_properties_stun(stun_effect):
    """
    Test properties of stun incapacitating effect.
    """
    assert stun_effect.prevents_actions()
    assert stun_effect.prevents_movement()  # stun prevents movement
    assert not stun_effect.breaks_on_damage()  # stun doesn't break on damage


def test_incapacitating_properties_paralysis(paralysis_effect):
    """
    Test properties of paralysis incapacitating effect.
    """
    assert paralysis_effect.prevents_actions()
    assert paralysis_effect.prevents_movement()  # paralysis prevents movement
    assert not paralysis_effect.breaks_on_damage()  # paralysis doesn't break on damage


def test_active_incapacitating_on_turn_end_decrements_duration(
    attacker, target, sleep_effect
):
    """
    Test that active incapacitating effect decrements duration on turn end.
    """
    variables = attacker.get_expression_variables()
    sleep_effect.apply_effect(attacker, target, variables)
    active_incap = list(target.effects.incapacitating_effects)[0]

    # Create TurnEndEvent
    turn_end_event = TurnEndEvent(source=target, turn_number=1)

    # Trigger on_event
    response = active_incap.on_event(turn_end_event)

    # Verify response
    assert response is not None
    assert not response.remove_effect  # duration was 3, now 2
    assert response.new_effects == []
    assert response.damage_bonus == []
    assert "no longer affected" in response.message

    # Duration should decrement
    assert active_incap.duration == 2


def test_active_incapacitating_expires_after_duration(attacker, target, stun_effect):
    """
    Test that incapacitating effect expires after its duration.
    """
    # Apply effect with duration 1
    stun_effect.duration = 1
    variables = attacker.get_expression_variables()
    stun_effect.apply_effect(attacker, target, variables)
    active_incap = list(target.effects.incapacitating_effects)[0]

    # Trigger turn end
    turn_end_event = TurnEndEvent(source=target, turn_number=1)
    response = active_incap.on_event(turn_end_event)

    # Should remove effect
    assert response.remove_effect
    assert active_incap.duration == 0


def test_active_incapacitating_breaks_on_damage_sleep(attacker, target, sleep_effect):
    """
    Test that sleep effect breaks when target takes damage.
    """
    variables = attacker.get_expression_variables()
    sleep_effect.apply_effect(attacker, target, variables)
    active_incap = list(target.effects.incapacitating_effects)[0]

    # Create DamageTakenEvent
    damage_event = DamageTakenEvent(source=attacker, target=target, amount=5)

    # Trigger on_event
    response = active_incap.on_event(damage_event)

    # Should remove effect (sleep breaks on damage)
    assert response is not None
    assert response.remove_effect
    assert "wakes up" in response.message


def test_active_incapacitating_does_not_break_on_damage_stun(
    attacker, target, stun_effect
):
    """
    Test that stun effect does not break when target takes damage.
    """
    variables = attacker.get_expression_variables()
    stun_effect.apply_effect(attacker, target, variables)
    active_incap = list(target.effects.incapacitating_effects)[0]

    # Create DamageTakenEvent
    damage_event = DamageTakenEvent(source=attacker, target=target, amount=10)

    # Trigger on_event
    response = active_incap.on_event(damage_event)

    # Should not remove effect (stun doesn't break on damage)
    assert response is not None
    assert not response.remove_effect


def test_active_incapacitating_no_response_to_other_events(
    attacker, target, sleep_effect
):
    """
    Test that active incapacitating effect only responds to TurnEndEvent and DamageTakenEvent.
    """
    variables = attacker.get_expression_variables()
    sleep_effect.apply_effect(attacker, target, variables)
    active_incap = list(target.effects.incapacitating_effects)[0]

    # Create a different event
    other_event = CombatEvent(event_type=EventType.ON_HIT, source=target)
    response = active_incap.on_event(other_event)
    assert response is None


def test_incapacitating_breaks_on_damage_types():
    """
    Test that different incapacitation types break on damage appropriately.
    """
    # Sleep breaks on damage
    sleep_effect = IncapacitatingEffect(
        name="Sleep",
        description="Deep sleep",
        duration=5,
        incapacitation_type=IncapacitationType.SLEEP,
    )
    assert sleep_effect.breaks_on_damage()
    
    # Charmed breaks on damage
    charmed_effect = IncapacitatingEffect(
        name="Charmed",
        description="Charmed",
        duration=5,
        incapacitation_type=IncapacitationType.CHARMED,
    )
    assert charmed_effect.breaks_on_damage()
    
    # Stunned doesn't break on damage
    stun_effect = IncapacitatingEffect(
        name="Stunned",
        description="Stunned",
        duration=1,
        incapacitation_type=IncapacitationType.STUNNED,
    )
    assert not stun_effect.breaks_on_damage()


def test_incapacitating_model_validation():
    """
    Test that incapacitating effect validates properly.
    """
    # Valid effect should work
    effect = IncapacitatingEffect(
        name="Test",
        description="Test",
        duration=1,
        incapacitation_type=IncapacitationType.SLEEP,
    )
    assert effect.incapacitation_type == IncapacitationType.SLEEP


def test_incapacitating_effect_with_saving_throw(attacker, target):
    """
    Test incapacitating effect with saving throw mechanics.
    """
    from core.constants import StatType
    
    # Create an effect with saving throws
    effect = IncapacitatingEffect(
        name="Test Stun",
        description="Test stun with saves",
        duration=3,
        incapacitation_type=IncapacitationType.STUNNED,
        save_dc="13",
        save_type=StatType.CONSTITUTION,
        save_timing="end_of_turn",
    )
    
    # Apply the effect
    success = effect.apply_effect(attacker, target, [])
    assert success
    
    # Get the active effect
    active_effects = list(target.effects.incapacitating_effects)
    assert len(active_effects) == 1
    active_effect = active_effects[0]
    
    # Test that saving throw is attempted on turn end
    event = TurnEndEvent(source=target, turn_number=1)
    response = active_effect.on_event(event)
    
    # Response should exist (either effect continues or ends due to save/duration)
    assert response is not None
