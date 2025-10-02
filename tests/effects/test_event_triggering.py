"""
Tests for event triggering in the effects system.
"""

import pytest
from character.character_class import CharacterClass
from character.character_race import CharacterRace
from character.main import Character
from core.constants import BonusType, CharacterType
from effects.event_system import EventType, HitEvent, MissEvent
from effects.modifier_effect import Modifier, ModifierEffect
from effects.trigger_effect import TriggerCondition, TriggerEffect


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


def test_hit_event_triggering(attacker: Character, target: Character):
    """
    Test that a trigger effect responds correctly to a HitEvent.
    """
    # Create a simple modifier effect to be triggered
    modifier = Modifier(
        bonus_type=BonusType.AC,
        value="2",
    )
    triggered_effect = ModifierEffect(
        name="Triggered Buff",
        description="AC buff from hit",
        duration=1,
        modifiers=[modifier],
    )

    # Create a trigger condition for on_hit
    trigger_condition = TriggerCondition(
        event_type=EventType.ON_HIT,
        description="On hit trigger",
    )

    # Create the trigger effect
    trigger_effect = TriggerEffect(
        name="Hit Trigger",
        description="Triggers on hit",
        duration=1,
        trigger_condition=trigger_condition,
        trigger_effects=[triggered_effect],
        damage_bonus=[],
        consumes_on_trigger=False,
        cooldown_turns=None,
        max_triggers=None,
    )

    # Apply the trigger effect to the target
    success = trigger_effect.apply_effect(attacker, target, [])
    assert success, "Trigger effect should apply successfully"

    # Create a HitEvent
    hit_event = HitEvent(
        source=attacker,
        target=target,
    )

    # Call on_event on the target's effects
    responses = target.effects.on_event(hit_event)

    # Check that we got a response
    assert len(responses) == 1, "Should have one event response"
    response = responses[0]

    # Check the response
    assert (
        response.effect == trigger_effect
    ), "Response should reference the trigger effect"
    assert (
        not response.remove_effect
    ), "Effect should not be removed since consumes_on_trigger=False"
    assert len(response.new_effects) == 1, "Should have one new effect"
    assert (
        response.new_effects[0] == triggered_effect
    ), "New effect should be the triggered buff"
    assert response.message, "Should have a message"


def test_no_trigger_on_miss(attacker: Character, target: Character):
    """
    Test that trigger effects do not respond to non-matching events.
    """
    # Similar setup as above
    modifier = Modifier(
        bonus_type=BonusType.AC,
        value="2",
    )
    triggered_effect = ModifierEffect(
        name="Triggered Buff",
        description="AC buff from hit",
        duration=1,
        modifiers=[modifier],
    )

    trigger_condition = TriggerCondition(
        event_type=EventType.ON_HIT,
        description="On hit trigger",
    )

    trigger_effect = TriggerEffect(
        name="Hit Trigger",
        description="Triggers on hit",
        duration=1,
        trigger_condition=trigger_condition,
        trigger_effects=[triggered_effect],
        damage_bonus=[],
        consumes_on_trigger=False,
        cooldown_turns=None,
        max_triggers=None,
    )

    trigger_effect.apply_effect(attacker, target, [])

    # Create a MissEvent instead
    miss_event = MissEvent(
        source=attacker,
        target=target,
    )

    # Call on_event
    responses = target.effects.on_event(miss_event)

    # Should have no responses
    assert len(responses) == 0, "Should have no responses for non-matching event"
