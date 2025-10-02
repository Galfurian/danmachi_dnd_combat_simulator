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
from core.logging import setup_logging
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

ring_of_last_stand = Armor(**json.loads(ring_of_last_stand_data))
player.inventory.add_armor(ring_of_last_stand)
player.take_damage(player.HP_MAX - 1, DamageType.BLUDGEONING)
