"""
Main entry point for the DanMachi D&D Combat Simulator.

This script loads character data, enemy data, and content repositories, then
initializes and runs combat scenarios. It demonstrates the combat system with
turn-based mechanics, character actions, spells, and effects.

The combat simulator supports:
- Loading characters, enemies, and player data from JSON files
- Managing combat turns and initiative
- Handling various action classes (attacks, spells, abilities)
- Character effects and status conditions
- Combat logging and reporting
"""

import argparse
import logging
from collections import Counter
from copy import deepcopy
from pathlib import Path

from character.character_serialization import load_character, load_characters
from character.main import Character
from combat.combat_manager import CombatManager
from core.constants import CharacterType
from core.content import ContentRepository
from core.logging import setup_logging
from core.sheets import crule, print_character_sheet
from core.utils import cprint

# Get the path to the data folder.
DATA_DIR = Path(__file__).with_suffix("").parent / "../data"
ENEMIES_F01_F10_FILE = DATA_DIR / "enemies_danmachi_f1_f10.json"
CHARACTERS_FILE = DATA_DIR / "characters.json"


def add_to_list(
    from_group: dict[str, Character],
    to_list: list[Character],
    name: str,
) -> None:
    """
    Add a character from a source group to a destination list for combat.

    Creates a deep copy of the character to avoid modifying the original data.
    Logs a warning if the character name is not found in the source group.

    Args:
        from_group (dict[str, Character]):
            Source dictionary of available characters.
        to_list (list[Character]):
            Destination list to add the character to.
        name (str):
            Name of the character to add from the source group.

    """
    if name in from_group:
        to_list.append(deepcopy(from_group[name]))
    else:
        print(
            f"Opponent '{name}' not found in enemies data",
            {
                "opponent_name": name,
                "available_opponents": list(from_group.keys()),
                "context": "combat_setup",
            },
        )


def make_names_unique(in_list: list[Character]) -> None:
    """
    Ensure all character names in a list are unique by appending numbers.

    Modifies character names in-place by appending (1), (2), etc. to duplicate
    names. Only adds numbers when duplicates exist - single instances keep
    original names.

    Args:
        in_list (list[Character]):
            List of characters to make names unique for.

    Example:
        Input:
            ["Goblin", "Goblin", "Orc"]
        Output:
            ["Goblin (1)", "Goblin (2)", "Orc"]

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


def get_log_Level(log_level: str) -> int:
    """
    Convert a log level string to a logging level integer.

    Args:
        log_level (str):
            Log level as a string (e.g., "DEBUG", "INFO").
    Returns:
        int:
            Corresponding logging level integer.
    """
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(log_level.upper(), logging.INFO)


def main(args: argparse.Namespace) -> None:
    """
    Main function for the combat simulator.

    Args:
        args (argparse.Namespace):
            Parsed command-line arguments containing log_level and effects_log_level.

    """

    # Configure logger-specific levels
    logger_levels = {
        "simulator": get_log_Level(args.log_level),
        "simulator.effects": get_log_Level(args.effects_log_level),
        "simulator.character": get_log_Level(args.character_log_level),
    }
    setup_logging(logger_levels)

    # =========================================================================

    crule("Initiliaze Data", style="bold green")

    ContentRepository(DATA_DIR)

    cprint("Loading enemies...", style="bold green")
    enemies_f01_f10 = load_characters(ENEMIES_F01_F10_FILE)

    cprint("Loading characters...", style="bold green")
    characters = load_characters(CHARACTERS_FILE)

    if args.log_level == logging.DEBUG:
        crule("Enemies", style="bold green", characters="=")
        for enemy_name, enemy in enemies_f01_f10.items():
            logging.debug(f"Enemy data: {enemy_name}")
            print_character_sheet(enemy)

    if args.log_level == logging.DEBUG:
        crule("Character", style="bold green", characters="=")
        for char_name, char in characters.items():
            logging.debug(f"Character data: {char_name}")
            print_character_sheet(char)

    # =========================================================================

    # Initialize the list of opponents and allies.
    opponents: list[Character] = []
    allies: list[Character] = []
    players: list[Character] = []

    # Add opponents.
    # add_to_list(enemies_f01_f10, opponents, "Purple Moth")
    # add_to_list(enemies_f01_f10, opponents, "Minotaur Boss")
    # add_to_list(enemies_f01_f10, opponents, "Infant Dragon")
    # add_to_list(enemies_f01_f10, opponents, "Orc")
    add_to_list(enemies_f01_f10, opponents, "Goblin")
    add_to_list(enemies_f01_f10, opponents, "Goblin")
    add_to_list(enemies_f01_f10, opponents, "Goblin")
    # add_to_list(enemies_f01_f10, opponents, "Goblin")
    # add_to_list(enemies_f01_f10, opponents, "Goblin")
    # add_to_list(enemies_f01_f10, opponents, "Goblin")
    # add_to_list(enemies_f01_f10, opponents, "Goblin")
    # add_to_list(enemies_f01_f10, opponents, "Goblin")
    # add_to_list(enemies_f01_f10, opponents, "Goblin")
    # add_to_list(enemies_f01_f10, opponents, "Goblin")
    # add_to_list(enemies_f01_f10, opponents, "Dungeon Worm")

    # Add allies.
    add_to_list(characters, allies, "Naerin")
    add_to_list(characters, allies, "Elara")
    add_to_list(characters, allies, "Thrain")

    # Add player characters.
    # add_to_list(characters, players, "Zephyros")

    # Make names unique by appending numbers to duplicates.
    make_names_unique(players)
    make_names_unique(opponents)
    make_names_unique(allies)

    # Turn all the characters in players, into PLAYER.
    for pc in players:
        pc.char_type = CharacterType.PLAYER

    # Initialize the combat manager with all participants.
    combat_manager = CombatManager(players + opponents + allies)

    cprint()
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="DanMachi D&D Combat Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-ll",
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the default logging level (default: INFO)",
    )
    parser.add_argument(
        "-el",
        "--effects-log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level specifically for effects (default: INFO)",
    )
    parser.add_argument(
        "-cl",
        "--character-log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level specifically for characters (default: INFO)",
    )

    args = parser.parse_args()

    main(args)
