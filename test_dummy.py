"""
Test dummy module for the simulator.

Contains dummy tests and examples for verifying simulator functionality.
"""

from pathlib import Path

from character.character_class import CharacterClass
from character.character_race import CharacterRace
from character.main import Character
from core.constants import CharacterType
from core.content import ContentRepository

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
    resistances=set(),
    vulnerabilities=set(),
    number_of_attacks=0,
    passive_effects=[],
)

