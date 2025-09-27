"""
Module for printing character sheets and other game elements in a formatted way.
"""

from actions.abilities import AbilityBuff, AbilityHeal, AbilityOffensive, BaseAbility
from actions.attacks.base_attack import BaseAttack
from actions.base_action import BaseAction
from actions.spells import BaseSpell, SpellHeal, SpellOffensive
from character.main import Character
from combat.damage import DamageComponent
from effects.base_effect import Effect
from effects.damage_over_time_effect import DamageOverTimeEffect
from effects.healing_over_time_effect import HealingOverTimeEffect
from effects.modifier_effect import Modifier, ModifierEffect
from effects.trigger_effect import TriggerEffect
from items.armor import Armor
from items.weapon import Weapon
from rich.padding import Padding

from core.content import ContentRepository
from core.utils import cprint, crule


def modifier_to_string(modifier: Modifier) -> str:
    """
    Converts a Modifier to a formatted string representation.

    Args:
        modifier (Modifier): The modifier to format.

    Returns:
        str: Formatted string showing the modifier value and bonus type with appropriate colors.

    """
    if isinstance(modifier.value, DamageComponent):
        return str(modifier.value)
    if isinstance(modifier.value, str):
        return f"[blue]{modifier.value}[/] to {modifier.bonus_type.name.lower()}"
    return f"[green]{modifier.value}[/] to {modifier.bonus_type.name.lower()}"


def print_effect_sheet(effect: Effect, padding: int = 2) -> None:
    """
    Prints the details of an effect in a formatted way.

    Args:
        effect (Effect): The effect to display.
        padding (int): Left padding for the output. Defaults to 2.

    """
    sheet: str = f"[blue]{effect.name}[/], "
    if effect.description:
        sheet += f'[italic]"{effect.description}"[/], '
    if effect.duration:
        sheet += f"{effect.duration} turns, "
    if isinstance(effect, ModifierEffect):
        modifiers_str = ", ".join(
            [modifier_to_string(modifier) for modifier in effect.modifiers]
        )
        sheet += f"[bold]{modifiers_str}[/]"
    elif isinstance(effect, HealingOverTimeEffect):
        sheet += f"heals [green]{effect.heal_per_turn}[/] per turn"
    elif isinstance(effect, DamageOverTimeEffect):
        sheet += f"deals {effect.damage!s} per turn"
    elif isinstance(effect, TriggerEffect):
        # Handle TriggerEffect effects (like spell buffs that trigger on events)
        details = []

        # Show damage bonus if present
        if effect.damage_bonus:
            damage_strings = [str(damage) for damage in effect.damage_bonus]
            details.append(f"adds {', '.join(damage_strings)} on trigger")

        # Show trigger effects if present
        if effect.trigger_effects:
            trigger_names = [
                f"[red]{trigger.name}[/]" for trigger in effect.trigger_effects
            ]
            details.append(f"applies {', '.join(trigger_names)}")

        if details:
            sheet += ", ".join(details)
        else:
            sheet += f'[italic]"{effect.trigger_condition.description}"[/]'

    cprint(Padding(sheet, (0, padding)))

    # For TriggerEffect, also show details of the triggered effects
    if isinstance(effect, TriggerEffect):
        if effect.trigger_effects:
            for trigger_effect in effect.trigger_effects:
                print_effect_sheet(trigger_effect, padding + 2)


def print_passive_effect_sheet(effect: Effect, padding: int = 2) -> None:
    """Prints the details of a passive effect in a formatted way."""
    sheet: str = f"[{effect.color}]{effect.name}[/]"
    if effect.description:
        sheet += f' - [italic]"{effect.description}"[/]'
    cprint(Padding(sheet, (0, padding)))

    # Handle TriggerEffect effects
    if isinstance(effect, TriggerEffect):
        # Show what it triggers
        if effect.trigger_effects:
            cprint(Padding("Triggers:", (0, padding + 2)))
            for trigger_effect in effect.trigger_effects:
                print_effect_sheet(trigger_effect, padding + 4)

        # Show damage bonuses
        if effect.damage_bonus:
            damage_str = ", ".join([str(damage) for damage in effect.damage_bonus])
            cprint(Padding(f"Damage bonus: {damage_str}", (0, padding + 2)))

        # Show what it triggers
        if effect.trigger_effects:
            cprint(Padding("Triggers:", (0, padding + 2)))
            for trigger_effect in effect.trigger_effects:
                print_effect_sheet(trigger_effect, padding + 4)

        # Show damage bonuses
        if effect.damage_bonus:
            damage_str = ", ".join([str(damage) for damage in effect.damage_bonus])
            cprint(Padding(f"Damage bonus: {damage_str}", (0, padding + 2)))

    # Generic passive effect - just show description
    elif hasattr(effect, "trigger_effects"):
        trigger_effects = getattr(effect, "trigger_effects", [])
        if trigger_effects:
            cprint(Padding("Triggers:", (0, padding + 2)))
            for trigger_effect in trigger_effects:
                print_effect_sheet(trigger_effect, padding + 4)


def print_base_attack_sheet(attack: BaseAttack, padding: int = 2) -> None:
    """Prints the details of a base attack in a formatted way."""
    sheet = f"[green]{attack.name}[/], "
    sheet += f"roll: [blue]1D20+{attack.attack_roll}[/], "
    sheet += f"damage: {', '.join([str(damage) for damage in attack.damage])}"
    if attack.effects:
        cprint(Padding("Applies:", (0, padding)))
        for effect in attack.effects:
            print_effect_sheet(effect, padding + 2)
    cprint(Padding(sheet, (0, padding)))


def print_weapon_sheet(weapon: Weapon, padding: int = 2) -> None:
    """Prints the details of a weapon in a formatted way."""
    sheet: str = f"[blue]{weapon.name}[/], "
    if weapon.requires_hands():
        sheet += f"{weapon.get_required_hands()} hands, "
    sheet += f'[italic]"{weapon.description}"[/]'
    cprint(Padding(sheet, (0, padding)))
    for attack in weapon.attacks:
        print_base_attack_sheet(attack, padding + 2)


def print_armor_sheet(armor: Armor, padding: int = 2) -> None:
    """Prints the details of an armor in a formatted way."""
    sheet: str = f"[blue]{armor.name}[/], "
    sheet += f"{armor.armor_type.emoji}, "
    sheet += f"{armor.armor_slot.name}, "
    sheet += f"AC: {armor.ac}, "
    if armor.max_dex_bonus:
        sheet += f"Max Dex Bonus: {armor.max_dex_bonus}, "
    sheet += f'[italic]"{armor.description}"[/]'
    cprint(Padding(sheet, (0, padding)))
    if armor.effects:
        cprint(Padding("Applies:", (0, padding)))
        for effect in armor.effects:
            print_effect_sheet(effect, padding + 2)


def print_spell_sheet(spell: BaseSpell, padding: int = 2) -> None:
    """
    Prints the details of a spell in a formatted way.

    Args:
        spell (BaseSpell): The spell to display.
        padding (int): Left padding for the output. Defaults to 2.

    """
    sheet: str = f"{spell.category.colorize(spell.name)}, "
    sheet += f"lvl {spell.level}, "
    sheet += f"{spell.action_class.colored_name}, "
    sheet += f"mind {spell.mind_cost}, "
    if spell.has_limited_uses():
        sheet += f"max uses: {spell.get_maximum_uses()}, "
    cprint(Padding(sheet, (0, padding)))
    padding += 2
    sheet = f'[italic]"{spell.description}"[/]'
    cprint(Padding(sheet, (0, padding)))

    # Handle specific spell types
    if isinstance(spell, SpellOffensive):
        sheet = f"Deals {', '.join([str(damage) for damage in spell.damage])}"
        cprint(Padding(sheet, (0, padding)))
    elif isinstance(spell, SpellHeal):
        sheet = f"Heals [green]{spell.heal_roll}[/] HP"
        cprint(Padding(sheet, (0, padding)))

    # Handle spell effects
    if spell.effects:
        cprint(Padding("Applies:", (0, padding)))
        padding += 2
        for effect in spell.effects:
            print_effect_sheet(effect, padding)


def print_ability_sheet(ability: BaseAbility, padding: int = 2) -> None:
    """
    Prints the details of an ability in a formatted way.

    Args:
        ability (BaseAbility): The ability to display.
        padding (int): Left padding for the output. Defaults to 2.

    """
    sheet: str = f"{ability.category.colorize(ability.name)}, "
    sheet += f"{ability.action_class.colored_name}, "

    if ability.has_cooldown():
        sheet += f"cooldown: {ability.get_cooldown()}, "
    if ability.has_limited_uses():
        sheet += f"max uses: {ability.get_maximum_uses()}, "

    cprint(Padding(sheet, (0, padding)))
    padding += 2

    # Description
    sheet = f'[italic]"{ability.description}"[/]'
    cprint(Padding(sheet, (0, padding)))

    # Handle specific ability types
    if isinstance(ability, AbilityOffensive):
        if ability.damage:
            sheet = f"Deals {', '.join([str(damage) for damage in ability.damage])}"
            cprint(Padding(sheet, (0, padding)))
    elif isinstance(ability, AbilityHeal):
        sheet = f"Heals [green]{ability.heal_roll}[/] HP"
        cprint(Padding(sheet, (0, padding)))
    elif isinstance(ability, AbilityBuff):
        sheet = "Applies beneficial effect"
        cprint(Padding(sheet, (0, padding)))

    # Handle ability effects
    if ability.effects:
        cprint(Padding("Applies:", (0, padding)))
        for effect in ability.effects:
            print_effect_sheet(effect, padding + 2)


def print_action_sheet(action: BaseAction, padding: int = 2) -> None:
    """
    Prints the details of any action in a formatted way.

    Args:
        action (BaseAction): The action to display.
        padding (int): Left padding for the output. Defaults to 2.

    """
    if isinstance(action, BaseSpell):
        print_spell_sheet(action, padding)
    elif isinstance(action, BaseAbility):
        print_ability_sheet(action, padding)
    elif isinstance(action, BaseAttack):
        print_base_attack_sheet(action, padding)
    else:
        # Generic action display
        sheet: str = f"{action.category.colorize(action.name)}[/], "
        sheet += f"{action.action_class.colored_name}, "
        sheet += f'[italic]"{action.description}"[/]'
        cprint(Padding(sheet, (0, padding)))

        # Handle generic action effects if they exist
        if action.effects:
            cprint(Padding("Applies:", (0, padding)))
            for effect in action.effects:
                print_effect_sheet(effect, padding + 2)


def print_character_sheet(char: Character) -> None:
    """
    Prints the details of a character in a formatted way.

    Args:
        char (Character): The character to display.

    """
    # Header with basic character info
    class_levels = ", ".join(
        [f"[green]{cls.name} {lvl}[/]" for cls, lvl in char.levels.items()]
    )
    cprint(
        f"{char.char_type.emoji} [{char.char_type.color}]{char.name}[/], "
        f"[blue]{char.race.name}[/], {class_levels}"
    )

    # Core stats
    cprint(
        f"  HP: [green]{char.hp}/{char.HP_MAX}[/], AC: [yellow]{char.AC}[/], Initiative: [cyan]{char.INITIATIVE}[/]"
    )

    if char.MIND_MAX > 0:
        cprint(f"  Mind: [blue]{char.mind}/{char.MIND_MAX}[/]")

    if char.spellcasting_ability:
        # Convert full ability name to 3-letter abbreviation
        ability_abbrev = char.spellcasting_ability[:3].upper()
        spell_mod = getattr(char, ability_abbrev)
        cprint(
            f"  Spellcasting: [magenta]{char.spellcasting_ability} ({spell_mod:+d})[/]"
        )

    # Ability scores and modifiers
    stat_display = []
    for stat_name, stat_value in char.stats.items():
        modifier = getattr(char, stat_name[:3].upper())
        stat_display.append(f"{stat_name.capitalize()}: {stat_value} ({modifier:+d})")
    cprint(f"  {', '.join(stat_display)}")

    # Character details
    if char.total_hands != 2:
        cprint(f"  Hands: {char.total_hands}")
    if char.number_of_attacks != 1:
        cprint(f"  Attacks per turn: {char.number_of_attacks}")

    # Equipment
    if char.equipped_weapons:
        cprint("  [blue]Equipped Weapons[/]:")
        for weapon in char.equipped_weapons:
            print_weapon_sheet(weapon, 4)

    if char.natural_weapons:
        cprint("  [blue]Natural Weapons[/]:")
        for weapon in char.natural_weapons:
            print_weapon_sheet(weapon, 4)

    if char.equipped_armor:
        cprint("  [blue]Armor[/]:")
        for armor in char.equipped_armor:
            print_armor_sheet(armor, 4)

    # Actions and Abilities
    if char.actions:
        cprint("  [cyan]Actions & Abilities[/]:")
        for action in char.actions.values():
            print_action_sheet(action, 4)

    # Spells
    if char.spells:
        cprint("  [magenta]Spells[/]:")
        for spell in char.spells.values():
            print_spell_sheet(spell, 4)

    # Resistances and Vulnerabilities
    if char.resistances:
        rlist = [f"{r.colorize(r.name)}" for r in char.resistances]
        cprint(f"  [green]Resistances[/]: {', '.join(rlist)}")

    if char.vulnerabilities:
        vlist = [f"[{v.colorize(v.name)}]" for v in char.vulnerabilities]
        cprint(f"  [red]Vulnerabilities[/]: {', '.join(vlist)}")

    # Active Effects
    if char._effects_module.active_effects:
        cprint("  [yellow]Active Effects[/]:")
        for active_effect in char._effects_module.active_effects:
            effect_info = (
                f"[{active_effect.effect.color}]{active_effect.effect.name}[/]"
            )
            if active_effect.duration and active_effect.duration > 0:
                effect_info += f" ({active_effect.duration} turns remaining)"
            cprint(Padding(effect_info, (0, 4)))

    # Trigger Effects
    if char._effects_module.trigger_effects:
        cprint("  [yellow]Trigger Effects[/]:")
        for trigger_effect in char._effects_module.trigger_effects:
            effect_info = (
                f"[{trigger_effect.effect.color}]{trigger_effect.effect.name}[/]"
            )
            cprint(Padding(effect_info, (0, 4)))

    # Passive Effects (if any)
    if hasattr(char, "passive_effects") and char.passive_effects:
        cprint("  [dim]Passive Effects[/]:")
        for effect in char.passive_effects:
            print_passive_effect_sheet(effect, 4)

    # Cooldowns and uses
    active_cooldowns = {
        name: turns
        for name, turns in char._actions_module.cooldowns.items()
        if turns > 0
    }
    if active_cooldowns:
        cprint("  [orange1]Active Cooldowns[/]:")
        for action_name, turns in active_cooldowns.items():
            cprint(Padding(f"{action_name}: {turns} turns", (0, 4)))

    active_uses = {
        name: uses for name, uses in char._actions_module.uses.items() if uses > 0
    }
    if active_uses:
        cprint("  [orange1]Used Abilities[/]:")
        for action_name, uses in active_uses.items():
            cprint(Padding(f"{action_name}: {uses} uses", (0, 4)))


def print_content_repository_summary() -> None:
    """
    Prints a summary of all available content in the repository.

    Displays counts and basic information for each content category.
    """
    repo = ContentRepository()

    cprint("\n[bold cyan]📚 Content Repository Summary[/bold cyan]")
    cprint("=" * 50)

    # Character Classes
    if hasattr(repo, "classes") and repo.classes:
        cprint(f"\n[green]Character Classes ({len(repo.classes)})[/green]:")
        for name, char_class in repo.classes.items():
            class_info = f"[blue]{name}[/] - HP×{char_class.hp_mult}, Mind×{char_class.mind_mult}"
            cprint(Padding(class_info, (0, 2)))

    # Character Races
    if hasattr(repo, "races") and repo.races:
        cprint(f"\n[green]Character Races ({len(repo.races)})[/green]:")
        for name, race in repo.races.items():
            race_info = f"[blue]{name}[/]"
            if race.natural_ac > 0:
                race_info += f" - AC +{race.natural_ac}"
            cprint(Padding(race_info, (0, 2)))

    # Weapons
    if hasattr(repo, "weapons") and repo.weapons:
        cprint(f"\n[green]Weapons ({len(repo.weapons)})[/green]:")
        for name, weapon in repo.weapons.items():
            weapon_info = f"[blue]{name}[/]"
            if weapon.requires_hands():
                weapon_info += f" - {weapon.get_required_hands()}H"
            cprint(Padding(weapon_info, (0, 2)))

    # Armor
    if hasattr(repo, "armors") and repo.armors:
        cprint(f"\n[green]Armor ({len(repo.armors)})[/green]:")
        for name, armor in repo.armors.items():
            armor_info = f"[blue]{name}[/] - AC {armor.ac} ({armor.armor_type.name}, {armor.armor_slot.name})"
            cprint(Padding(armor_info, (0, 2)))

    # Actions
    if hasattr(repo, "actions") and repo.actions:
        cprint(f"\n[green]Actions & Abilities ({len(repo.actions)})[/green]:")
        for name, action in repo.actions.items():
            action_info = f"{action.category.colorize(name)} "
            action_info += f"({action.action_class.colored_name})"
            cprint(Padding(action_info, (0, 2)))

    # Spells
    if hasattr(repo, "spells") and repo.spells:
        cprint(f"\n[green]Spells ({len(repo.spells)})[/green]:")
        spell_types: dict[str, list[tuple[str, BaseSpell]]] = {}
        for name, spell in repo.spells.items():
            spell_type = type(spell).__name__
            if spell_type not in spell_types:
                spell_types[spell_type] = []
            spell_types[spell_type].append((name, spell))

        for spell_type, spells in spell_types.items():
            cprint(
                f"  {spells[0][1].category.colorize(spell_type)} ({len(spells)})[/]:"
            )
            for name, spell in spells:
                spell_info = f"[blue]{name}[/] - Lvl {spell.level}"
                cprint(Padding(spell_info, (0, 4)))

    # Calculate total if we have the attributes
    total_items = 0
    for attr_name in ["classes", "races", "weapons", "armors", "actions", "spells"]:
        if hasattr(repo, attr_name):
            collection = getattr(repo, attr_name)
            if isinstance(collection, dict):
                total_items += len(collection)

    if total_items > 0:
        cprint(f"\n[dim]Total Items: {total_items}[/dim]")
    else:
        cprint(
            "\n[yellow]⚠️  Repository not loaded. Try running the main simulator first to load content.[/yellow]"
        )


def print_all_available_content() -> None:
    """
    Prints detailed information about all available content in the repository.

    Displays comprehensive information for each item in all content categories.
    """
    from core.content import ContentRepository

    repo = ContentRepository()

    crule("📚 Complete Content Catalog", style="bold blue", characters="=")

    # Print detailed information for each category
    if hasattr(repo, "classes") and repo.classes:
        crule(f"🏛️ Character Classes ({len(repo.classes)})", style="bold green")
        for name, char_class in sorted(repo.classes.items()):
            cprint(
                f"[blue]{name}[/], "
                f"hp-mult: {char_class.hp_mult}, "
                f"mind-mult: {char_class.mind_mult}"
            )
            if char_class.actions_by_level:
                cprint("  [magenta]Actions[/]:")
                for level, actions in char_class.actions_by_level.items():
                    cprint(f"    Level {level}: {actions}")
            if char_class.spells_by_level:
                cprint("  [cyan]Abilities[/]:")
                for level, spells in char_class.spells_by_level.items():
                    cprint(f"    Level {level}: {spells}")

    if hasattr(repo, "races") and repo.races:
        crule(f"🧬 Character Races ({len(repo.races)})", style="bold green")
        for name, race in sorted(repo.races.items()):
            cprint(f"[blue]{name:16}[/] natural ac: +{race.natural_ac}")
            if race.default_actions:
                cprint("  [magenta]Actions[/]:")
                for action in race.default_actions:
                    cprint(f"    {action}")
            if race.default_spells:
                cprint("  [cyan]BaseSpell[/]:")
                for spell in race.default_spells:
                    cprint(f"    {spell}")

    if hasattr(repo, "weapons") and repo.weapons:
        crule(f"⚔️ Weapons ({len(repo.weapons)})", style="bold green")
        for name, weapon in sorted(repo.weapons.items()):
            print_weapon_sheet(weapon, 0)

    if hasattr(repo, "armors") and repo.armors:
        crule(f"🛡️ Armor ({len(repo.armors)})", style="bold green")
        for name, armor in sorted(repo.armors.items()):
            print_armor_sheet(armor, 0)

    if hasattr(repo, "actions") and repo.actions:
        crule(f"⚡ Actions & Abilities ({len(repo.actions)})", style="bold green")
        for name, action in sorted(repo.actions.items()):
            print_action_sheet(action, 0)

    if hasattr(repo, "spells") and repo.spells:
        crule(f"🔮 Spells ({len(repo.spells)})", style="bold green")
        for name, spell in sorted(repo.spells.items()):
            print_spell_sheet(spell, 0)
    crule("", style="bold blue", characters="=")


def print_damage_types_reference() -> None:
    """
    Print a reference of all damage types with colors.

    Displays all available damage types with their visual styling.
    """
    from core.constants import DamageType

    cprint("\n[bold cyan]💥 Damage Types Reference[/bold cyan]")
    cprint("=" * 40)

    for damage_type in DamageType:
        cprint(f"{damage_type.emoji} {damage_type.display_name}")


def print_action_classes_reference() -> None:
    """
    Print a reference of all action classes and categories with colors.

    Displays all available action classes and categories with their visual styling.
    """
    from core.constants import ActionCategory, ActionClass

    cprint("\n[bold cyan]⚡ Action System Reference[/bold cyan]")
    cprint("=" * 40)

    cprint("\n[green]action classes:[/green]")
    for action_class in ActionClass:
        if action_class != ActionClass.NONE:
            cprint(f"  {action_class.colored_name}")

    cprint("\n[green]Action Categories:[/green]")
    for category in ActionCategory:
        cprint(f"  {category.emoji} {category.colored_name}")
