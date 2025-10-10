"""
Test on hit effects module for the simulator.

Contains tests and examples for on_hit and on_damage_taken effects,
including Thorns effect.
"""

import logging
from pathlib import Path

from character.character_class import CharacterClass
from character.character_race import CharacterRace
from character.character_serialization import load_character, load_characters
from character.main import Character
from core.constants import CharacterType
from core.content import ContentRepository
from core.logging import logger, setup_logging
from core.utils import crule
from effects.base_effect import EventResponse
from effects.event_system import (
    CombatEvent,
    DamageTakenEvent,
    HitEvent,
)

# Set up logging
setup_logging(logging.DEBUG)


# Initialize the ContentRepository for tests
# This is necessary because Character's model_validator and model_post_init
# methods access the ContentRepository.
repo = ContentRepository(data_dir=Path("./data"))

construct_race = CharacterRace(
    name="Construct",
    natural_ac=0,
    default_actions=[],
    default_spells=[],
)

construct_class = CharacterClass(
    name="Construct",
    hp_mult=10,
    mind_mult=0,
    actions_by_level={},
    spells_by_level={},
)


training_dummy = Character(
    char_type=CharacterType.ENEMY,
    name="Training Dummy",
    race=construct_race,
    levels={construct_class: 1},
    stats={
        "STRENGTH": 14,
        "DEXTERITY": 15,
        "CONSTITUTION": 15,
        "INTELLIGENCE": 16,
        "WISDOM": 14,
        "CHARISMA": 18,
    },
    spellcasting_ability=None,
    total_hands=0,
    immunities=set(),
    resistances=set(),
    vulnerabilities=set(),
    number_of_attacks=0,
    passive_effects=[],
)

characters = load_characters(Path("./data/characters.json"))
player = characters.get("Zephyros")


assert player, "Failed to load player character from JSON."


def resolve_target(
    event: CombatEvent, applies_to: str, active_effect_target: Character
):
    """
    Resolve the target for an effect based on applies_to.

    Args:
        event: The combat event
        applies_to: "TARGET", "SOURCE", or "SELF"
        active_effect_target: The character with the active effect

    Returns:
        The resolved target character

    """
    if applies_to == "TARGET":
        target_attr = getattr(event, "target", None)
        if target_attr:
            return target_attr
        return active_effect_target
    if applies_to == "SOURCE":
        return event.source
    if applies_to == "SELF":
        return active_effect_target
    return active_effect_target


def on_event(character: Character, event: CombatEvent):
    responses: list[EventResponse] = character.on_event(event)
    for response in responses:
        if response.message:
            logger.info(response.message)
        for damage_bonus in response.damage_bonus:
            logger.info(
                f"  Damage bonus applied to {character.colored_name}: {damage_bonus}"
            )
        for new_effect in response.new_effects:
            # Resolve the target based on applies_to
            target = resolve_target(event, new_effect.applies_to, character)
            logger.info(
                f"  Applying {new_effect.name} to {target.colored_name} (applies_to: {new_effect.applies_to})"
            )
            success = new_effect.apply_effect(
                actor=character,  # The character with the effect
                target=target,
                variables=character.get_expression_variables(),
            )
            if not success:
                logger.info(f"  Failed to apply {new_effect.name}")


def print_active_effects(character: Character):
    if not character.effects.active_effects:
        logger.info(f"{character.colored_name} has no active effects.")
        return
    logger.info(f"Active effects for {character.colored_name}:")
    for effect in character.effects.active_effects:
        logger.info(f"  {effect}")


# =============================================================================

crule("Thorns Effect Test")

print()
print_active_effects(player)
print()

# Create Thorns effect: When damaged, deal 1d4 piercing damage back to attacker
thorns_data = {
    "effect_type": "TriggerEffect",
    "name": "Thorns",
    "description": "Deals damage back to attackers when hit.",
    "duration": 5,  # 5 turns
    "trigger_condition": {"event_type": "on_damage_taken"},
    "trigger_effects": [
        {
            "effect_type": "InstantDamageEffect",
            "name": "Thorns Damage",
            "description": "Instant damage from thorns",
            "duration": 0,  # Instant
            "damage": {"damage_roll": "1d4", "damage_type": "PIERCING"},
            "applies_to": "SOURCE",  # Apply to the source of the damage (attacker)
        }
    ],
}

from effects.trigger_effect import TriggerEffect

thorns_effect = TriggerEffect(**thorns_data)

# Apply Thorns to player
success = thorns_effect.apply_effect(
    actor=player, target=player, variables=player.get_expression_variables()
)
if success:
    logger.info("Thorns effect applied to player")
else:
    logger.info("Failed to apply Thorns effect")

print()
print_active_effects(player)
print()

# Simulate damage from training dummy
damage_amount = 10
logger.info(f"Training dummy attacks player for {damage_amount} damage")

# First, the hit event
hit_event = HitEvent(source=training_dummy, target=player)
on_event(player, hit_event)

# Then, damage taken event
damage_event = DamageTakenEvent(
    source=training_dummy, target=player, amount=damage_amount
)
on_event(player, damage_event)

print()
print_active_effects(player)
print()

# Check if damage was dealt back
logger.info(f"Player HP: {player.stats.hp}/{player.HP_MAX}")
logger.info(f"Training Dummy HP: {training_dummy.stats.hp}/{training_dummy.HP_MAX}")

crule("")

# =============================================================================
