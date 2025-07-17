from copy import deepcopy
from logging import error, warning
from rich.console import Console
from rich.rule import Rule
from collections import Counter
from core.content import ContentRepository
from pathlib import Path

import logging

from combat.combat_manager import *
from entities.character import *


"""Sets up basic logging configuration."""
logging.basicConfig(
    level=logging.INFO,  # Set the minimum level of messages to be handled
    format="[%(name)s:%(levelname)-12s] %(message)s",
    handlers=[logging.StreamHandler()],
)

# Get the path to the data folder.
data_dir = Path(__file__).with_suffix("").parent / "../data"

console = Console()

console.print(Rule("Combat Simulator", style="bold green"))

console.print(
    "Welcome to the Combat Simulator! This is a simple combat simulator for tabletop RPGs. "
    "You can create characters, equip them with weapons and armor, and engage in combat. "
    "The combat system is turn-based, and you can use various actions such as attacks, spells, and effects. "
    "The combat manager will handle the turn order and combat logic. "
    "You can also create custom characters and actions by modifying the data files in the 'data' directory. "
    "Have fun!"
    "\n",
    style="bold blue",
)

# =============================================================================

console.print(Rule("Loading Repository", style="bold green"))

# Load the repository of content.
repo = ContentRepository(data_dir)

# =============================================================================

console.print(Rule("Loading Enemies", style="bold green"))

# Load the enemies.
enemies: dict[str, Character] = load_characters(
    data_dir / "enemies_danmachi_f1_f10.json"
)
print("Enemies loaded:")
for enemy in enemies.values():
    print_character_details(enemy)
    console.print("\n")


# =============================================================================

console.print(Rule("Loading Characters", style="bold green"))

# Load the characters.
characters: dict[str, Character] = load_characters(data_dir / "characters.json")
for character in characters.values():
    print_character_details(character)
    console.print("\n")

# =============================================================================

console.print(Rule("Loading Player Character", style="bold green"))

# Load the player character.
player = load_character(data_dir / "player.json")
if player is None:
    error("Failed to load player character. Please check the data file.")
    exit(1)

print_character_details(player)
console.print("\n")

# =============================================================================

# Initialize the list of opponents and allies.
opponents: list[Character] = []
allies: list[Character] = []


def add_to_list(from_group: dict[str, Character], to_list: list[Character], name: str):
    """
    Adds an opponent to the combat.
    """
    if name in from_group:
        to_list.append(deepcopy(from_group[name]))
    else:
        warning(f"Opponent '{name}' not found in enemies data.")


def make_names_unique(in_list: list[Character]):
    """
    Ensures all opponent names are unique by appending a number if necessary, starting from (1).
    """
    # Count how many times each base name appears
    name_counts = Counter(o.name for o in in_list)
    # Track how many times we've seen each base name so far
    seen: Counter[str] = Counter()
    for opponent in in_list:
        base = opponent.name
        if name_counts[base] > 1:
            seen[base] += 1
            opponent.name = f"{base} ({seen[base]})"


if __name__ == "__main__":

    # add_to_list(enemies, opponents, "Infant Dragon")
    add_to_list(enemies, opponents, "Orc")
    # add_to_list(enemies, opponents, "Goblin")
    # add_to_list(enemies, opponents, "Goblin")
    # add_to_list(enemies, opponents, "Goblin")
    # add_to_list(enemies, opponents, "Goblin")
    # add_to_list(enemies, opponents, "Goblin")
    # add_to_list(enemies, opponents, "Dungeon Worm")
    # add_to_list(characters, allies, "Naerin")
    # add_to_list(characters, allies, "Naerin")
    make_names_unique(opponents)
    make_names_unique(allies)

    combat_manager = CombatManager(player, opponents, allies)

    console.print(Rule(":crossed_swords:  Initializing Combat", style="bold green"))
    # Call the new initialize method.
    combat_manager.initialize()

    try:
        combat_manager.pre_combat_phase()
        console.print(Rule(":crossed_swords:  Combat Started", style="bold green"))
        while not combat_manager.is_combat_over():
            combat_manager.run_turn()
        combat_manager.post_combat_phase()
        combat_manager.final_report()
        console.print(Rule(":crossed_swords:  Combat Finished", style="bold green"))
    except KeyboardInterrupt:
        console.print("")
        console.print(Rule(":crossed_swords:  Combat Interrupted", style="bold red"))
