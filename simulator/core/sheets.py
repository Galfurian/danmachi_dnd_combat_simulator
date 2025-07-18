from core.constants import *
from core.utils import *
from entities.character import *
from actions.spell_action import *
from items.weapon import *
from items.armor import *
from effects.effect import *

from rich.padding import Padding


def damage_to_string(damage: DamageComponent):
    damage_color = get_damage_type_color(damage.damage_type)
    return f"[{damage_color}]{damage.damage_roll} {damage.damage_type.name.lower()}[/]"

def modifier_to_string(modifier: Modifier):
    """Converts a Modifier to a formatted string representation."""
    if isinstance(modifier.value, DamageComponent):
        return f"[{get_damage_type_color(modifier.value.damage_type)}]{modifier.value.damage_roll} {modifier.value.damage_type.name.lower()}[/] to {modifier.bonus_type.name.lower()}"
    elif isinstance(modifier.value, str):
        return f"[blue]{modifier.value}[/] to {modifier.bonus_type.name.lower()}"
    else:
        return f"[green]{modifier.value}[/] to {modifier.bonus_type.name.lower()}"

def print_effect_sheet(effect: Effect, padding: int = 2):
    """Prints the details of an effect in a formatted way."""
    sheet: str = f"[blue]{effect.name}[/], "
    if effect.description:
        sheet += f"[italic]{effect.description}[/], "
    if effect.max_duration:
        sheet += f"{effect.max_duration} turns, "
    if isinstance(effect, Buff):
        modifiers_str = ", ".join([modifier_to_string(modifier) for modifier in effect.modifiers])
        sheet += f"[green]{modifiers_str}[/]"
    elif isinstance(effect, Debuff):
        modifiers_str = ", ".join([modifier_to_string(modifier) for modifier in effect.modifiers])
        sheet += f"[red]{modifiers_str}[/]"
    elif isinstance(effect, HoT):
        sheet += f"heals [green]{effect.heal_per_turn}[/] per turn"
    elif isinstance(effect, DoT):
        sheet += f"deals {damage_to_string(effect.damage)} per turn"
    cprint(Padding(sheet, (0, padding)))


def print_base_attack_sheet(attack: BaseAttack, padding: int = 2):
    """Prints the details of a base attack in a formatted way."""
    sheet = f"[green]{attack.name}[/], "
    sheet += f"roll: [blue]1D20+{attack.attack_roll}[/], "
    sheet += f"damage: {', '.join([damage_to_string(damage) for damage in attack.damage])}"
    if attack.effect:
        print_effect_sheet(attack.effect, padding + 2)
    cprint(Padding(sheet, (0, padding)))


def print_weapon_sheet(weapon: Weapon, padding: int = 2):
    """Prints the details of a weapon in a formatted way."""
    sheet: str = f"[blue]{weapon.name}[/], "
    if weapon.hands_required:
        sheet += f"{weapon.hands_required} hands, "
    sheet += f"[italic]{weapon.description}[/]"
    cprint(Padding(sheet, (0, padding)))
    for attack in weapon.attacks:
        print_base_attack_sheet(attack, padding + 2)


def print_armor_sheet(armor: Armor, padding: int = 2):
    """Prints the details of an armor in a formatted way."""
    sheet: str = f"[blue]{armor.name}[/], "
    sheet += f"{get_armor_type_emoji(armor.armor_type)}, "
    sheet += f"{armor.armor_slot.name}, "
    sheet += f"AC: {armor.ac}, "
    if armor.max_dex_bonus:
        sheet += f"Max Dex Bonus: {armor.max_dex_bonus}, "
    sheet += f"[italic]{armor.description}[/]"
    cprint(Padding(sheet, (0, padding)))
    if armor.effect:
        print_effect_sheet(armor.effect, padding + 2)


def print_spell_sheet(spell: Spell, padding: int = 2):
    """Prints the details of a spell in a formatted way."""
    sheet: str = f"[{get_action_category_color(spell.category)}]{spell.name}[/], "
    sheet += f"lvl {spell.level}, "
    sheet += f"[{get_action_type_color(spell.type)}]{spell.type.name}[/], "
    sheet += f"mind {spell.mind_cost}, "
    if spell.maximum_uses > 0:
        sheet += f"max uses: {spell.maximum_uses}, "
    cprint(Padding(sheet, (0, padding)))
    padding += 2
    sheet = f"[italic]{spell.description}[/]"
    cprint(Padding(sheet, (0, padding)))
    if isinstance(spell, SpellAttack):
        sheet = f"Deals {', '.join([damage_to_string(damage) for damage in spell.damage])}"
        cprint(Padding(sheet, (0, padding)))
    if spell.effect:
        cprint(Padding("Applies:", (0, padding)))
        padding += 2
        print_effect_sheet(spell.effect, padding)


def print_action_sheet(action: BaseAction, padding: int = 2):
    if isinstance(action, Spell):
        print_spell_sheet(action, padding)
    elif isinstance(action, BaseAttack):
        print_base_attack_sheet(action, padding)
    else:
        sheet: str = f"[blue]{action.name}[/], "
        sheet += f"Type: [{get_action_type_color(action.type)}]{action.type.name}[/], "
        sheet += f"[italic]{action.description}[/]"
        cprint(Padding(sheet, (0, padding)))
        if action.effect:
            print_effect_sheet(action.effect, padding + 2)


def print_character_sheet(char: Character):
    """Prints the details of a character in a formatted way."""

    cprint(
        f"{get_character_type_emoji(char.type)} [{get_character_type_color(char.type)}]{char.name}[/], [blue]{char.race.name}[/], {', '.join([f'[green]{cls.name} {lvl}[/]' for cls, lvl in char.levels.items()])}, hp: {char.hp}/{char.HP_MAX}, ac: {char.AC}"
    )

    if char.spellcasting_ability:
        cprint(f"  Spellcasting ability: {char.spellcasting_ability}")

    cprint(f"  {', '.join([f'{stat}: {value}' for stat, value in char.stats.items()])}")

    if char.equipped_weapons:
        cprint(f"  [blue]Equipped[/] Weapons:")
        for weapon in char.equipped_weapons:
            print_weapon_sheet(weapon, 4)

    if char.natural_weapons:
        cprint(f"  [blue]Natural[/] Weapons:")
        for weapon in char.natural_weapons:
            print_weapon_sheet(weapon, 4)

    if char.equipped_armor:
        cprint(f"  [blue]Armor[/]:")
        for armor in char.equipped_armor:
            print_armor_sheet(armor, 4)

    if char.actions:
        cprint(f"  Actions:")
        for action in char.actions.values():
            print_action_sheet(action, 4)

    if char.spells:
        cprint(f"  Spells:")
        for spell in char.spells.values():
            print_spell_sheet(spell, 4)
    if char.resistances:
        cprint(
            f"  Resistances: "
            ", ".join([f"[{get_damage_type_color(r)}]{r.name}[/]" for r in char.resistances])
        )
    if char.vulnerabilities:
        cprint(
            f"  Vulnerabilities: "
            ", ".join([f"[{get_damage_type_color(v)}]{v.name}[/]" for v in char.vulnerabilities])
        )
