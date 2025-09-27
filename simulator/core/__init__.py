"""
Core system module for the DanMachi D&D Combat Simulator.

This module contains the fundamental components and utilities that power the combat simulator,
including game constants, dice rolling mechanics, content loading, and display utilities.
"""

from .constants import (
    CharacterType,
    BonusType,
    ActionClass,
    DamageType,
    ActionCategory,
    ArmorSlot,
    ArmorType,
    is_oponent,
)
from .content import (
    ContentRepository,
    _load_json_file,
)

from .dice_parser import (
    DiceParser,
)

from .sheets import (
    modifier_to_string,
    print_effect_sheet,
    print_passive_effect_sheet,
    print_base_attack_sheet,
    print_weapon_sheet,
    print_armor_sheet,
    print_spell_sheet,
    print_ability_sheet,
    print_action_sheet,
    print_character_sheet,
    print_content_repository_summary,
    print_all_available_content,
    print_damage_types_reference,
    print_action_classes_reference,
)

from .utils import (
    GameException,
    Singleton,
    VarInfo,
    RollBreakdown,
    cprint,
    crule,
    ccapture,
    get_stat_modifier,
    substitute_variables,
    extract_dice_terms,
    parse_term_and_roll_dice,
    parse_term_and_assume_min_dice,
    parse_term_and_assume_max_dice,
    roll_dice,
    roll_dice_expression,
    parse_expr_and_assume_min_roll,
    parse_expr_and_assume_max_roll,
    roll_expression,
    get_max_roll,
    roll_and_describe,
    evaluate_expression,
    simplify_expression,
    make_bar,
)

__all__ = [
    # Inport from constants.py
    "CharacterType",
    "BonusType",
    "ActionClass",
    "DamageType",
    "ActionCategory",
    "ArmorSlot",
    "ArmorType",
    "is_oponent",
    # Import from content.py
    "ContentRepository",
    "_load_json_file",
    # Import from dice_parser.py
    "DiceParser",
    # Import from sheets.py
    "modifier_to_string",
    "print_effect_sheet",
    "print_passive_effect_sheet",
    "print_base_attack_sheet",
    "print_weapon_sheet",
    "print_armor_sheet",
    "print_spell_sheet",
    "print_ability_sheet",
    "print_action_sheet",
    "print_character_sheet",
    "print_content_repository_summary",
    "print_all_available_content",
    "print_damage_types_reference",
    "print_action_classes_reference",
    # Import from utils.py
    "GameException",
    "Singleton",
    "VarInfo",
    "RollBreakdown",
    "cprint",
    "crule",
    "ccapture",
    "get_stat_modifier",
    "substitute_variables",
    "extract_dice_terms",
    "parse_term_and_roll_dice",
    "parse_term_and_assume_min_dice",
    "parse_term_and_assume_max_dice",
    "roll_dice",
    "roll_dice_expression",
    "parse_expr_and_assume_min_roll",
    "parse_expr_and_assume_max_roll",
    "roll_expression",
    "get_max_roll",
    "roll_and_describe",
    "evaluate_expression",
    "simplify_expression",
    "make_bar",
]
