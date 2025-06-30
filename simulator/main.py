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
    "classes": classes,
    "races": races,
}

# =============================================================================

console.print(Rule("Loading Enemies", style="bold green"))

# Load the enemies.
enemies = load_characters("data/enemies_danmachi_f1_f10.json", registries)
for enemy_name, enemy in enemies.items():
    print(f"    Loaded enemy: {enemy_name} (hp: {enemy.hp}, ac: {enemy.AC})")

# =============================================================================

console.print(Rule("Loading Characters", style="bold green"))

# Load the characters.
characters = load_characters("data/characters.json", registries)
for character_name, character in characters.items():
    print(
        f"    Loaded character: {character_name} (hp: {character.hp}, ac: {character.AC})"
    )

# =============================================================================

console.print(Rule("Loading Player Character", style="bold green"))

# Load the player character.
player = load_player_character("data/player.json", registries)
if player is None:
    error("Failed to load player character. Please check the data file.")
    exit(1)

# =============================================================================

# Initialize the list of opponents and allies.
opponents: list[Character] = []
allies: list[Character] = []


def add_to_list(from_list: list[Character], to_list: list[Character], name: str):
    """
    Adds an opponent to the combat.
    """
    if name in from_list:
        to_list.append(deepcopy(from_list[name]))
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

    ui = PromptToolkitCLI()
    add_to_list(enemies, opponents, "Goblin")
    add_to_list(enemies, opponents, "Goblin")
    add_to_list(enemies, opponents, "Goblin")

    add_to_list(characters, allies, "Naerin")

    make_names_unique(opponents)
    make_names_unique(allies)

    for enemy in opponents:
        enemy.is_ally = False
    for ally in allies:
        ally.is_ally = True

    combat_manager = CombatManager(ui, player, opponents, allies)

    try:
        while not combat_manager.is_combat_over():
            combat_manager.run_turn()
    except KeyboardInterrupt:
        console.print("")
        console.print(Rule("Combat Interrupted", style="bold red"))
