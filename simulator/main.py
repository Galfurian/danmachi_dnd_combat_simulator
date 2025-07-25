import logging
from collections import Counter
from copy import deepcopy
from pathlib import Path

from combat.combat_manager import CombatManager
from core.content import ContentRepository
from core.error_handling import log_error, log_warning
from core.sheets import crule, print_character_sheet
from core.utils import cprint
from character import Character, load_character, load_characters


"""
Main entry point for the DanMachi D&D Combat Simulator.

This script loads character data, enemy data, and content repositories, then
initializes and runs combat scenarios. It demonstrates the combat system with
turn-based mechanics, character actions, spells, and effects.

The combat simulator supports:
- Loading characters, enemies, and player data from JSON files
- Managing combat turns and initiative
- Handling various action types (attacks, spells, abilities)
- Character effects and status conditions
- Combat logging and reporting
"""

# Sets up basic logging configuration.
logging.basicConfig(
    level=logging.INFO,  # Set the minimum level of messages to be handled
    format="%(message)s",  # Clean format - our error handler already includes severity and location
    handlers=[logging.StreamHandler()],
)

# Get the path to the data folder.
data_dir = Path(__file__).with_suffix("").parent / "../data"

crule("Combat Simulator", style="bold green")

cprint(
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

crule("Loading Repository", style="bold green")

# Load the repository of content.
repo = ContentRepository(data_dir)

# =============================================================================

crule("Loading Enemies", style="bold green")

# Load the enemies.
enemies: dict[str, Character] = load_characters(
    data_dir / "enemies_danmachi_f1_f10.json"
)
print("Enemies loaded:")
for enemy in enemies.values():
    print_character_sheet(enemy)
    cprint("\n")


# =============================================================================

crule("Loading Characters", style="bold green")

# Load the characters.
characters: dict[str, Character] = load_characters(data_dir / "characters.json")
for character in characters.values():
    print_character_sheet(character)
    cprint("\n")

# =============================================================================

crule("Loading Player Character", style="bold green")

# Load the player character.
player = load_character(data_dir / "player.json")
if player is None:
    log_error(
        "Failed to load player character. Please check the data file",
        {"data_file": str(data_dir / "player.json"), "context": "main_startup"}
    )
    exit(1)

print_character_sheet(player)
cprint("\n")

# =============================================================================

# Initialize the list of opponents and allies.
opponents: list[Character] = []
allies: list[Character] = []


def add_to_list(from_group: dict[str, Character], to_list: list[Character], name: str) -> None:
    """
    Add a character from a source group to a destination list for combat.
    
    Creates a deep copy of the character to avoid modifying the original data.
    Logs a warning if the character name is not found in the source group.
    
    Args:
        from_group (dict[str, Character]): Source dictionary of available characters.
        to_list (list[Character]): Destination list to add the character to.
        name (str): Name of the character to add from the source group.
    """
    if name in from_group:
        to_list.append(deepcopy(from_group[name]))
    else:
        log_warning(
            f"Opponent '{name}' not found in enemies data",
            {"opponent_name": name, "available_opponents": list(from_group.keys()), "context": "combat_setup"}
        )


def make_names_unique(in_list: list[Character]) -> None:
    """
    Ensure all character names in a list are unique by appending numbers.
    
    Modifies character names in-place by appending (1), (2), etc. to duplicate names.
    Only adds numbers when duplicates exist - single instances keep original names.
    
    Args:
        in_list (list[Character]): List of characters to make names unique for.
        
    Example:
        Input: ["Goblin", "Goblin", "Orc"]
        Output: ["Goblin (1)", "Goblin (2)", "Orc"]
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

    # Test the new incapacitation system with Sleep Powder
    add_to_list(enemies, opponents, "Purple Moth")
    # add_to_list(enemies, opponents, "Minotaur Boss")
    # add_to_list(enemies, opponents, "Infant Dragon")
    # add_to_list(enemies, opponents, "Orc")
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

    crule(":crossed_swords:  Initializing Combat", style="bold green")
    # Call the new initialize method.
    combat_manager.initialize()

    try:
        combat_manager.pre_combat_phase()
        crule(":crossed_swords:  Combat Started", style="bold green")
        while not combat_manager.is_combat_over():
            combat_manager.run_turn()
        combat_manager.post_combat_phase()
        combat_manager.final_report()
        crule(":crossed_swords:  Combat Finished", style="bold green")
    except KeyboardInterrupt:
        cprint("")
        crule(":crossed_swords:  Combat Interrupted", style="bold red")
