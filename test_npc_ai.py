"""
Test script to verify the new score-based NPC AI is working correctly.
"""

import logging
from pathlib import Path

from character.character_class import CharacterClass
from character.character_race import CharacterRace
from character.main import Character
from combat.combat_manager import CombatManager
from core.constants import CharacterType
from core.content import ContentRepository
from core.logging import setup_logging

# Set up logging
setup_logging(logging.INFO)

# Initialize the ContentRepository
repo = ContentRepository(data_dir=Path("./data"))

# Create a simple test character class and race
test_race = CharacterRace(
    name="Human",
    natural_ac=10,
    default_actions=[],
    default_spells=[],
)

test_class = CharacterClass(
    name="Fighter",
    hp_mult=8,
    mind_mult=0,
    actions_by_level={},
    spells_by_level={},
)

# Create test characters
player = Character(
    char_type=CharacterType.PLAYER,
    name="Test Player",
    race=test_race,
    levels={test_class: 1},
    stats={
        "STRENGTH": 14,
        "DEXTERITY": 15,
        "CONSTITUTION": 15,
        "INTELLIGENCE": 10,
        "WISDOM": 12,
        "CHARISMA": 13,
    },
    spellcasting_ability=None,
    total_hands=2,
    immunities=set(),
    resistances=set(),
    vulnerabilities=set(),
    number_of_attacks=1,
    passive_effects=[],
)

enemy = Character(
    char_type=CharacterType.ENEMY,
    name="Test Enemy",
    race=test_race,
    levels={test_class: 1},
    stats={
        "STRENGTH": 12,
        "DEXTERITY": 12,
        "CONSTITUTION": 12,
        "INTELLIGENCE": 10,
        "WISDOM": 10,
        "CHARISMA": 10,
    },
    spellcasting_ability=None,
    total_hands=2,
    immunities=set(),
    resistances=set(),
    vulnerabilities=set(),
    number_of_attacks=1,
    passive_effects=[],
)

# Create combat manager and test NPC action execution
combat_manager = CombatManager([player, enemy])
combat_manager.initialize()

print("Testing NPC action execution with score-based AI...")
print(f"Enemy HP before action: {enemy.stats.hp}")

# Test the NPC action execution
combat_manager.execute_npc_action(enemy)

print(f"Enemy HP after action: {enemy.stats.hp}")
print("NPC action execution test completed successfully!")