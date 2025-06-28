from abc import abstractmethod
from asyncio import shield
from logging import error, warning, info, debug
import logging

from cli_prompt import PromptToolkitCLI

"""Sets up basic logging configuration."""
logging.basicConfig(
    level=logging.INFO,  # Set the minimum level of messages to be handled
    format="[%(name)s:%(levelname)-12s] %(message)s",
    handlers=[logging.StreamHandler()],
)

from character import Character
from effect import *
from actions import *
from combat_manager import CombatManager


paladin = Class("Paladin", hp_mult=8, mind_mult=2)
sorcerer = Class("Sorcerer", hp_mult=6, mind_mult=6)
warrior = Class("Warrior", hp_mult=10, mind_mult=0)


def create_player() -> Character:
    player = Character(
        "Zephyros", {paladin: 1, sorcerer: 1}, 18, 12, 16, 10, 14, 10, "wisdom"
    )
    # Set the player's nature.
    player.is_player = True
    # Add the player's armor.
    player.add_armor(Armor("Armor", 16))
    player.add_armor(Armor("Shield", 2))
    player.add_armor(Armor("Defense Style", 1))
    # Add long sword as a weapon.
    player.learn_action(
        WeaponAttack(
            "Longsword",
            ActionType.STANDARD,
            damage_type=DamageType.SLASHING,
            attack_roll="1D20+STR",
            damage_roll="1D8+STR",
        )
    )
    player.learn_spell(
        SpellAttack(
            "Sacred Flame",
            ActionType.STANDARD,
            level=1,
            mind=1,
            damage_type=DamageType.RADIANT,
            damage_roll="[MIND]D8",
            effect=None,
            multi_target_expr="[MIND]",
        )
    )
    player.learn_spell(
        SpellHeal(
            "Healing Touch",
            ActionType.STANDARD,
            level=1,
            mind=1,
            heal_roll="[MIND]D8",
        )
    )
    player.learn_spell(
        BuffSpell(
            name="Bless",
            type=ActionType.STANDARD,
            level=1,
            mind=1,
            effect=Buff(
                name="Bless",
                mind=1,
                duration=3,
                modifiers={BonusType.ATTACK_BONUS: "1d4"},
            ),
            multi_target_expr="[MIND]",
            upscale_choices=[1, 2, 3, 4, 5],
        )
    )
    return player


def create_goblin() -> Character:
    goblin = Character(
        name="Goblin",
        levels={warrior: 1},
        strength=10,
        dexterity=14,
        constitution=12,
        intelligence=8,
        wisdom=8,
        charisma=6,
        spellcasting_ability="none",
    )
    goblin.add_armor(Armor("Leather Armor", 16))
    goblin.learn_action(
        WeaponAttack(
            "Shortsword",
            ActionType.STANDARD,
            DamageType.SLASHING,
            "1D20 + DEX",
            "1D6 + DEX",
        )
    )
    return goblin


def create_orc() -> Character:
    orc = Character(
        name="Orc",
        levels={warrior: 2},
        strength=16,
        dexterity=12,
        constitution=14,
        intelligence=6,
        wisdom=7,
        charisma=7,
        spellcasting_ability="none",
    )
    orc.add_armor(Armor("Hide Armor", 12))
    orc.learn_action(
        WeaponAttack(
            "Greataxe",
            ActionType.STANDARD,
            DamageType.SLASHING,
            "1D20 + STR",
            "1D12 + STR",
        )
    )
    return orc


if __name__ == "__main__":

    player = create_player()
    goblin = create_goblin()
    orc = create_orc()

    ui = PromptToolkitCLI()

    combat_manager = CombatManager(ui, player, [goblin, orc], [])

    while not combat_manager.is_combat_over():

        combat_manager.run_turn()
