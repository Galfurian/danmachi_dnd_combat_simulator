"""
Test dummy module for the simulator.

Contains dummy tests and examples for verifying simulator functionality.
"""

import json
import logging
from pathlib import Path

from character.character_class import CharacterClass
from character.character_race import CharacterRace
from character.character_serialization import load_character
from character.main import Character
from core.constants import CharacterType, DamageType
from core.content import ContentRepository
from core.logging import log_info, setup_logging
from core.utils import crule
from effects.base_effect import EventResponse
from effects.event_system import (
    CombatEvent,
    DamageTakenEvent,
    EventType,
    HitEvent,
    LowHealthEvent,
    TurnEndEvent,
)
from effects.event_system import EventType
from items.armor import Armor

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
        "strength": 14,
        "dexterity": 15,
        "constitution": 15,
        "intelligence": 16,
        "wisdom": 14,
        "charisma": 18,
    },
    spellcasting_ability=None,
    total_hands=0,
    immunities=set(),
    resistances=set(),
    vulnerabilities=set(),
    number_of_attacks=0,
    passive_effects=[],
)

player = load_character(Path("./data/player.json"))

assert player, "Failed to load player character from JSON."

ring_of_last_stand_data: str = """
{
    "name": "Ring of Last Stand",
    "description": "A mystical ring that grants the wearer a second chance at life.",
    "ac": 0,
    "armor_slot": "RING",
    "armor_type": "OTHER",
    "effects": [
        {
            "action_type": "TriggerEffect",
            "name": "Last Stand",
            "description": "When below 25% HP, it enchances the wearer's armor class.",
            "trigger_condition": {
                "event_type": "on_low_health",
                "threshold": 0.25
            },
            "trigger_effects": [
                {
                    "name": "Last Stand Buff",
                    "effect_type": "ModifierEffect",
                    "description": "Increases AC by 2 for 3 turns.",
                    "duration": 3,
                    "modifiers": [
                        {
                            "bonus_type": "AC",
                            "value": "2"
                        }
                    ]
                }
            ]
        }
    ]
}
"""


def on_event(character: Character, event: CombatEvent):
    responses: list[EventResponse] = character.on_event(event)
    for response in responses:
        if response.message:
            log_info(response.message)
        for damage_bonus in response.damage_bonus:
            log_info(
                f"  Damage bonus applied to {character.colored_name}: {damage_bonus}"
            )
        for new_effect in response.new_effects:
            if isinstance(event, HitEvent):
                new_effect.apply_effect(
                    actor=event.source,
                    target=event.target,
                    variables=event.source.get_expression_variables(),
                )
            elif isinstance(event, DamageTakenEvent):
                new_effect.apply_effect(
                    actor=event.source,
                    target=event.target,
                    variables=event.source.get_expression_variables(),
                )
            elif isinstance(event, LowHealthEvent):
                new_effect.apply_effect(
                    actor=event.source,
                    target=event.source,
                    variables=event.source.get_expression_variables(),
                )


def print_active_effects(character: Character):
    if not character.effects.active_effects:
        log_info(f"{character.colored_name} has no active effects.")
        return
    log_info(f"Active effects for {character.colored_name}:")
    for effect in character.effects.active_effects:
        log_info(f"  {effect}")


# =============================================================================

crule("Armor Effects")

print()
print_active_effects(player)
print()

ring_of_last_stand = Armor(**json.loads(ring_of_last_stand_data))
player.inventory.add_armor(ring_of_last_stand)

print()
print_active_effects(player)
print()

base, adjusted, actual = player.take_damage(player.HP_MAX - 1, DamageType.BLUDGEONING)
if actual > 0:
    on_event(
        player,
        HitEvent(
            source=training_dummy,
            target=player,
        ),
    )
    on_event(
        player,
        DamageTakenEvent(
            source=training_dummy,
            target=player,
            amount=actual,
        ),
    )
    on_event(
        player,
        LowHealthEvent(
            source=player,
        ),
    )

print()
print_active_effects(player)
print()

for turn_number in range(1, 5):
    log_info(f"--- Turn {turn_number} ---")
    player.on_event(TurnEndEvent(source=player, turn_number=turn_number))

print()
print_active_effects(player)
print()

crule("")

# =============================================================================


for spell_name, spell in player.actions.spells.items():
    key = f"'{spell_name}'"
    log_info(f"{key:22} -> ranks: {[rank for rank in spell.mind_cost]}")

mage_armor = player.actions.spells["mage armor"]
blurr = player.actions.spells["blurr"]

log_info(f"Player AC before mage armor: {player.AC}")

mage_armor.cast_spell(actor=player, target=player, rank=0)
log_info(f"Player AC after mage armor: {player.AC}")

blurr.cast_spell(actor=player, target=player, rank=0)
log_info(f"Player AC after blurr: {player.AC}")
