from copy import deepcopy
from logging import error, warning
from cli_prompt import PromptToolkitCLI
from character import *
from effect import *
from actions import *
from combat_manager import CombatManager
from rich.console import Console
from rich.rule import Rule
from collections import Counter

import logging

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


# =============================================================================

console.print(Rule("Loading Weapons", style="bold green"))

# Load weapons.
weapons = load_actions("data/weapon_data.json")
for weapon_name, weapon in weapons.items():
    print(f"    Loaded weapon: {weapon_name}")

# =============================================================================

console.print(Rule("Loading Armor", style="bold green"))

# Load armor data.
armors = load_effects("data/armor_data.json")
for armor_name, armor in armors.items():
    print(f"    Loaded armor: {armor_name}")

# =============================================================================

console.print(Rule("Loading Spells", style="bold green"))

# Load spells.
spells: dict[str, BaseAction] = {}

# Load SpellAttack.
spells.update(load_actions("data/spell_attack_data.json"))
# Load SpellHeal.
spells.update(load_actions("data/spell_heal_data.json"))
# Load SpellBuff.
spells.update(load_actions("data/spell_buff_data.json"))
# Load SpellDebuff.
spells.update(load_actions("data/spell_debuff_data.json"))

for spell_name, spell in spells.items():
    print(f"    Loaded spell {spell.type:<12}: {spell_name}")

# =============================================================================

console.print(Rule("Loading Character Classes", style="bold green"))

# Load character classes.
classes = load_character_classes("data/character_classes.json")
for class_name, class_data in classes.items():
    print(
        f"    Loaded class: {class_name} (hp_mult: {class_data.hp_mult}, mind_mult: {class_data.mind_mult})"
    )

# =============================================================================

console.print(Rule("Loading Character Races", style="bold green"))

# Load character races.
races = load_character_races("data/character_races.json")
for race_name, race_data in races.items():
    print(f"    Loaded race: {race_name} (natural_ac: {race_data.natural_ac})")

# =============================================================================

registries: dict[str, Any] = {
    "weapons": weapons,
    "armors": armors,
    "spells": spells,
    "classes": classes,
    "races": races,
    "actions": {},
}

# =============================================================================

console.print(Rule("Loading Enemies", style="bold green"))

# Load the enemies.
enemies = load_characters("data/enemies_danmachi_f1_f10.json", registries)
for enemy_name, enemy in enemies.items():
    print(f"    Loaded enemy: {enemy_name} (hp: {enemy.hp}, ac: {enemy.AC})")

# =============================================================================

console.print(Rule("Loading Player Character", style="bold green"))

# Load the player character.
player = load_player_character("data/player.json", registries)
if player is None:
    error("Failed to load player character. Please check the data file.")
    exit(1)

# =============================================================================

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
    seen: Counter[str] = Counter()
    for opponent in opponents:
        base = opponent.name
        if name_counts[base] > 1:
            seen[base] += 1
            opponent.name = f"{base} ({seen[base]})"


if __name__ == "__main__":

    ui = PromptToolkitCLI()

    # add_opponent("Goblin")
    # add_opponent("Goblin")
    # add_opponent("Goblin")
    add_opponent("Infant Dragon")

    make_opponents_names_unique()

    combat_manager = CombatManager(ui, player, opponents, [])

    while not combat_manager.is_combat_over():

        combat_manager.run_turn()
