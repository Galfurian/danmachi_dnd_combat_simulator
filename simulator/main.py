from abc import abstractmethod
from asyncio import shield
from copy import deepcopy
from logging import error, warning, info, debug
import logging
import json
from cli_prompt import PromptToolkitCLI
from character import Character
from effect import *
from actions import *
from combat_manager import CombatManager
from rich.console import Console
from rich.rule import Rule
from collections import Counter, defaultdict

"""Sets up basic logging configuration."""
logging.basicConfig(
    level=logging.INFO,  # Set the minimum level of messages to be handled
    format="[%(name)s:%(levelname)-12s] %(message)s",
    handlers=[logging.StreamHandler()],
)


console = Console()

console.print(Rule("Combat Simulator", style="bold green"))

console.print(
    "Welcome to the Combat Simulator! This is a simple combat simulator for tabletop RPGs. "
    "You can create characters, equip them with weapons and armor, and engage in combat. "
    "The combat system is turn-based, and you can use various actions such as attacks, spells, and effects. "
    "The combat manager will handle the turn order and combat logic. "
    "You can also create custom characters and actions by modifying the data files in the 'data' directory. "
    "Have fun!"
    "\n\n",
    style="bold blue",
)

console.print(Rule("Loading Weapons", style="bold green"))

# Load weapons.
weapons: dict[str, WeaponAttack] = {}
with open("data/weapon_data.json", "r") as f:
    weapon_data = json.load(f)
    for entry in weapon_data:
        weapon = BaseAction.from_dict(entry)
        weapons[weapon.name] = weapon
        print(f"Loaded weapon: {weapon.name}")

console.print(Rule("Loading Armor", style="bold green"))

# Load armor data.
armors: dict[str, Armor] = {}
with open("data/armor_data.json", "r") as f:
    armor_data = json.load(f)
    for entry in armor_data:
        armor = Armor.from_dict(entry)
        armors[armor.name] = armor
        print(f"Loaded armor: {armor.name}")

console.print(Rule("Loading Spells", style="bold green"))

# Load spells.
spells: dict[str, Spell] = {}

# Load SpellAttack.
with open("data/spell_attack_data.json", "r") as f:
    spell_attack_data = json.load(f)
    for entry in spell_attack_data:
        spell = SpellAttack.from_dict(entry)
        spells[spell.name] = spell
        print(f"Loaded spell attack: {spell.name}")

# Load SpellHeal.
with open("data/spell_heal_data.json", "r") as f:
    spell_heal_data = json.load(f)
    for entry in spell_heal_data:
        spell = SpellHeal.from_dict(entry)
        spells[spell.name] = spell
        print(f"Loaded spell heal: {spell.name}")

# Load SpellBuff.
with open("data/spell_buff_data.json", "r") as f:
    spell_buff_data = json.load(f)
    for entry in spell_buff_data:
        spell = SpellBuff.from_dict(entry)
        spells[spell.name] = spell
        print(f"Loaded spell buff: {spell.name}")

# Load SpellDebuff.
with open("data/spell_debuff_data.json", "r") as f:
    spell_debuff_data = json.load(f)
    for entry in spell_debuff_data:
        spell = SpellDebuff.from_dict(entry)
        spells[spell.name] = spell
        print(f"Loaded spell debuff: {spell.name}")

console.print(Rule("Loading Character Classes", style="bold green"))

# Load character classes.
classes: dict[str, CharacterClass] = {}
with open("data/character_classes.json", "r") as f:
    class_data = json.load(f)
    for entry in class_data:
        character_class = CharacterClass.from_dict(entry)
        classes[character_class.name] = character_class
        print(f"Loaded character class: {character_class.name}")

registries = {
    "weapons": weapons,
    "armors": armors,
    "spells": spells,
    "classes": classes,
    "actions": {},
}

# Load the enemies.
enemies: dict[str, Character] = {}
with open("data/enemies.json", "r") as f:
    enemy_data = json.load(f)
    for entry in enemy_data:
        enemy = Character.from_dict(entry, registries)
        enemies[enemy.name] = enemy
        print(f"Loaded enemy: {enemy.name}")

# Load the player character.
player: Character = None
with open("data/player.json", "r") as f:
    player_data = json.load(f)
    player = Character.from_dict(player_data, registries)
    print(f"Loaded player character: {player.name}")

if player is None:
    error("Player character could not be loaded. Please check the player data file.")
    exit(1)

# Initialize the list of opponents, and a supporting function to add them.
opponents: list[Character] = []


def add_opponent(name: str):
    """
    Adds an opponent to the combat.
    """
    if name in enemies:
        opponents.append(deepcopy(enemies[name]))
    else:
        warning(f"Opponent '{name}' not found in enemies data.")


def make_opponents_names_unique():
    """
    Ensures all opponent names are unique by appending a number if necessary, starting from (1).
    """
    # Count how many times each base name appears
    name_counts = Counter(o.name for o in opponents)
    # Track how many times we've seen each base name so far
    seen = Counter()
    for opponent in opponents:
        base = opponent.name
        if name_counts[base] > 1:
            seen[base] += 1
            opponent.name = f"{base} ({seen[base]})"


if __name__ == "__main__":

    ui = PromptToolkitCLI()

    add_opponent("Goblin")
    add_opponent("Goblin")
    add_opponent("Goblin")
    add_opponent("Orc Shaman")

    make_opponents_names_unique()

    combat_manager = CombatManager(ui, player, opponents, [])

    while not combat_manager.is_combat_over():

        combat_manager.run_turn()
