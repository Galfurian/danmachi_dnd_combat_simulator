import json
from logging import debug, warning
from typing import Any
from rich.console import Console

from constants import *
from actions import BaseAction, Spell, SpellAttack, SpellBuff, SpellHeal, WeaponAttack
from effect import Buff, DoT, Effect, HoT
from utils import *


console = Console()


class ActiveEffect:
    def __init__(self, source: "Character", effect: "Effect", mind_level: int) -> None:
        self.source: "Character" = source
        self.effect: "Effect" = effect
        self.mind_level: int = mind_level
        self.duration: int = effect.max_duration

        assert self.duration > 0, "ActiveEffect duration must be greater than 0."


class CharacterClass:
    def __init__(self, name: str, hp_mult: int, mind_mult: int):
        self.name: str = name
        self.hp_mult: int = hp_mult
        self.mind_mult: int = mind_mult

    def to_dict(self) -> dict[str, Any]:
        """Converts the CharacterClass instance to a dictionary.

        Returns:
            dict[str, Any]: The dictionary representation of the CharacterClass instance.
        """
        return {
            "name": self.name,
            "hp_mult": self.hp_mult,
            "mind_mult": self.mind_mult,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "CharacterClass":
        """Creates a CharacterClass instance from a dictionary.

        Args:
            data (dict): _description_

        Returns:
            _type_: _description_
        """
        return CharacterClass(
            name=data["name"],
            hp_mult=data.get("hp_mult", 0),
            mind_mult=data.get("mind_mult", 0),
        )


class CharacterRace:
    def __init__(self, name: str, natural_ac: int = 0):
        self.name = name
        self.natural_ac = natural_ac

    def to_dict(self) -> dict[str, Any]:
        """Converts the CharacterRace instance to a dictionary.

        Returns:
            dict[str, Any]: The dictionary representation of the CharacterRace instance.
        """
        return {
            "name": self.name,
            "natural_ac": self.natural_ac,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "CharacterRace":
        """Creates a CharacterRace instance from a dictionary.

        Args:
            data (dict): The dictionary representation of the CharacterRace.

        Returns:
            CharacterRace: The CharacterRace instance.
        """
        return CharacterRace(
            name=data["name"],
            natural_ac=data.get("natural_ac", 0),
        )


class Character:
    def __init__(
        self,
        name: str,
        race: CharacterRace,
        levels: dict[CharacterClass, int],
        strength: int,
        dexterity: int,
        constitution: int,
        intelligence: int,
        wisdom: int,
        charisma: int,
        spellcasting_ability: Optional[str] = None,
    ):
        # Determines if the character is a player or an NPC.
        self.type: CharacterType = CharacterType.ENEMY
        # Name of the character.
        self.name: str = name
        # The character race.
        self.race: CharacterRace = race
        # The character's class levels.
        self.levels: dict[CharacterClass, int] = levels
        # Stats.
        self.stats: dict[str, int] = {
            "strength": strength,
            "dexterity": dexterity,
            "constitution": constitution,
            "intelligence": intelligence,
            "wisdom": wisdom,
            "charisma": charisma,
        }
        # Spellcasting Ability.
        self.spellcasting_ability: Optional[str] = spellcasting_ability
        # List of equipped weapons.
        self.equipped_weapons: list[Any] = []
        self.total_hands: int = 2
        self.hands_used: int = 0
        # List of equipped armor.
        self.equipped_armor: list[Any] = []
        # List of active effects.
        self.active_effects: list[ActiveEffect] = []
        # List of actions.
        self.actions: dict[str, BaseAction] = {}
        # List of spells
        self.spells: dict[str, Spell] = {}
        # Turn flags to track used actions.
        self.turn_flags: dict[str, bool] = {
            "standard_action_used": False,
            "bonus_action_used": False,
        }

        # Maximum HP and Mind.
        self.hp: int = self.HP_MAX
        self.mind: int = self.MIND_MAX

    @property
    def HP_MAX(self) -> int:
        """Returns the maximum HP of the character."""
        hp_max: int = 0
        # Add the class levels' HP multipliers to the max HP.
        for cls, cls_level in self.levels.items():
            hp_max += max(1, (cls.hp_mult + self.CON)) * cls_level
        # Add the effect modifiers to the max HP.
        hp_max += self.get_total_bonus_from_effects(BonusType.HP)
        return hp_max

    @property
    def MIND_MAX(self) -> int:
        """Returns the maximum Mind of the character."""
        mind_max: int = 0
        # Add the class levels' Mind multipliers to the max Mind.
        for cls, cls_level in self.levels.items():
            mind_max += max(0, (cls.mind_mult + self.SPELLCASTING)) * cls_level
        # Add the effect modifiers to the max Mind.
        mind_max += self.get_total_bonus_from_effects(BonusType.MIND)
        return mind_max

    @property
    def STR(self):
        """Returns the DnD strength modifier."""
        return get_stat_modifier(self.stats["strength"])

    @property
    def DEX(self):
        """Returns the DnD dexterity modifier."""
        return get_stat_modifier(self.stats["dexterity"])

    @property
    def CON(self):
        """Returns the DnD constitution modifier."""
        return get_stat_modifier(self.stats["constitution"])

    @property
    def INT(self):
        """Returns the DnD intelligence modifier."""
        return get_stat_modifier(self.stats["intelligence"])

    @property
    def WIS(self):
        """Returns the DnD wisdom modifier."""
        return get_stat_modifier(self.stats["wisdom"])

    @property
    def CHA(self):
        """Returns the DnD charisma modifier."""
        return get_stat_modifier(self.stats["charisma"])

    @property
    def SPELLCASTING(self):
        """Returns the DnD spellcasting ability modifier."""
        if self.spellcasting_ability and self.spellcasting_ability in self.stats:
            return get_stat_modifier(self.stats[self.spellcasting_ability])
        return 0

    @property
    def AC(self) -> int:
        """
        Calculates Armor Class (AC) using DnD 5e rules:
        - If wearing body armor, AC = armor.base + DEX modifier (if allowed by type)
        - Shields stack with body armor or base AC
        - If no armor is worn, AC = 10 + DEX + race bonus
        """
        # Base AC is 10 + DEX modifier.
        base_ac = 10 + self.DEX

        # Add armor and shield AC.
        armor_ac = None
        shield_ac = 0
        for armor in self.equipped_armor:
            slot: ArmorSlot = getattr(armor, "armor_slot")
            if slot == ArmorSlot.TORSO:
                armor_type: ArmorType = getattr(armor, "armor_type")
                assert (
                    armor_type in ArmorType
                ), f"Invalid armor type: {armor_type} for armor {armor.name}"
                if armor_type == ArmorType.LIGHT:
                    armor_ac = armor.ac + self.DEX
                elif armor_type == ArmorType.MEDIUM:
                    armor_ac = armor.ac + min(self.DEX, 2)
                elif armor_type == ArmorType.HEAVY:
                    armor_ac = armor.ac
                else:
                    armor_ac = armor.ac
            elif slot == ArmorSlot.SHIELD:
                shield_ac += armor.ac

        # Add effect bonuses to AC.
        effect_ac = self.get_total_bonus_from_effects(BonusType.AC)

        # Determine final AC.
        if armor_ac is not None:
            return armor_ac + shield_ac + effect_ac
        race_bonus = self.race.natural_ac if self.race else 0
        return base_ac + race_bonus + shield_ac + effect_ac

    @property
    def INITIATIVE(self) -> int:
        """Calculates the character's initiative based on dexterity and any active effects.

        Returns:
            int: The total initiative value.
        """
        # Base initiative is DEX modifier.
        initiative = self.DEX
        # Add any initiative bonuses from active effects.
        initiative += self.get_total_bonus_from_effects(BonusType.INITIATIVE)
        return initiative

    def reset_turn_flags(self):
        """Resets the turn flags for the character."""
        self.turn_flags["standard_action_used"] = False
        self.turn_flags["bonus_action_used"] = False

    def use_action_type(self, action_type: ActionType):
        """Marks an action type as used for the current turn."""
        if action_type == ActionType.STANDARD:
            self.turn_flags["standard_action_used"] = True
        elif action_type == ActionType.BONUS:
            self.turn_flags["bonus_action_used"] = True

    def has_action_type(self, action_type: ActionType):
        """Checks if the character can use a specific action type this turn."""
        if action_type == ActionType.STANDARD:
            return not self.turn_flags["standard_action_used"]
        elif action_type == ActionType.BONUS:
            return not self.turn_flags["bonus_action_used"]
        return True

    def turn_done(self) -> bool:
        """
        Checks if the character has used both a standard and bonus action this turn.
        Returns True if both actions are used, False otherwise.
        """
        # Check if the character has any bonus actions available
        has_bonus_actions = False
        for action in list(self.actions.values()) + list(self.spells.values()):
            if action.type == ActionType.BONUS:
                has_bonus_actions = True
                break
        if has_bonus_actions:
            return (
                self.turn_flags["standard_action_used"]
                and self.turn_flags["bonus_action_used"]
            )
        else:
            return self.turn_flags["standard_action_used"]

    def take_damage(self, amount: int, damage_type: DamageType):
        """Reduces the character's hp by the given amount, applying damage reduction if applicable.

        Args:
            amount (int): The amount of damage to deal.
            damage_type (DamageType): The type of damage being dealt.

        Returns:
            int: The actual amount of damage taken.
        """
        # Ensure the amount is non-negative.
        amount = max(amount, 0)
        # Apply damage reduction from armor or effects.
        # Remove the amount of damage from the character's hp.
        self.hp = max(self.hp - amount, 0)
        # Return the actual damage we removed.
        return amount

    def heal(self, amount: int) -> int:
        """Increases the character's hp by the given amount, up to max_hp.

        Args:
            amount (int): The amount of healing to apply.

        Returns:
            int: The actual amount healed, which may be less than the requested amount if it exceeds max_hp.
        """
        # Compute the actual amount we can heal.
        amount = max(0, min(amount, self.HP_MAX - self.hp))
        # Ensure we don't exceed the maximum hp.
        self.hp += amount
        # Return the actual amount healed.
        return amount

    def use_mind(self, amount: int) -> bool:
        """Reduces the character's mind by the given amount, if they have enough mind points.

        Args:
            amount (int): The amount of mind points to use.

        Returns:
            bool: True if the mind points were successfully used, False otherwise.
        """
        if self.mind >= amount:
            self.mind -= amount
            return True
        return False

    def is_alive(self) -> bool:
        """Checks if the character is alive (hp > 0).

        Returns:
            bool: True if the character is alive, False otherwise.
        """
        return self.hp > 0

    def get_spell_attack_bonus(self, spell_level: int = 1) -> int:
        """Calculates the spell attack bonus for the character.

        Args:
            spell_level (int, optional): The level of the spell being cast. Defaults to

        Returns:
            int: The spell attack bonus for the character.
        """
        return self.SPELLCASTING + spell_level

    def learn_action(self, action: Any):
        """Adds an Action object to the character's known actions.

        Args:
            action (Any): The action to learn.
        """
        if not action.name.lower() in self.actions:
            self.actions[action.name.lower()] = action
            debug(f"{self.name} learned {action.name}!")

    def unlearn_action(self, action: Any):
        """Removes an Action object from the character's known actions.

        Args:
            action (Any): The action to unlearn.
        """
        if action.name.lower() in self.actions:
            del self.actions[action.name.lower()]
            debug(f"{self.name} unlearned {action.name}!")

    def learn_spell(self, spell: Any):
        """Adds a Spell object to the character's known spells.

        Args:
            spell (Any): The spell to learn.
        """
        if not spell.name.lower() in self.spells:
            self.spells[spell.name.lower()] = spell
            debug(f"{self.name} learned {spell.name}!")

    def unlearn_spell(self, spell: Any):
        """Removes a Spell object from the character's known spells.

        Args:
            spell (Any): The spell to unlearn.
        """
        if spell.name.lower() in self.spells:
            del self.spells[spell.name.lower()]
            debug(f"{self.name} unlearned {spell.name}!")

    def add_effect(self, source: "Character", effect: Effect, mind_level: int = 0):
        """Applies an effect to the character.

        Args:
            source (Character): The character that applied the effect.
            effect (Any): The effect to apply.
            mind_level (int, optional): The mind level required to maintain the effect. Defaults to 0.
        """
        if not self.has_effect(effect):
            debug(f"Adding effect: {effect.name} to {self.name} from {source.name}")
            self.active_effects.append(ActiveEffect(source, effect, mind_level))

    def remove_effect(self, active_effect: ActiveEffect):
        """Removes a specific effect from the character.

        Args:
            effect (ActiveEffect): The effect to remove.
        """
        if self.has_effect(active_effect.effect):
            # Call the effect's remove method to revert its changes.
            active_effect.effect.remove(active_effect.source, self)
            # Remove the active effect from the list.
            self.active_effects.remove(active_effect)

    def has_effect(self, effect: Effect) -> bool:
        """
        Checks if the character has a specific active effect.
        Args:
            effect (Effect): The effect to check.
        Returns:
            bool: True if the effect is active, False otherwise.
        """
        for active_effect in self.active_effects:
            if active_effect.effect == effect:
                return True
        return False

    def get_all_effects_of_type(self, effect_type: type[Effect]) -> list[ActiveEffect]:
        """
        Returns a list of all active effects of a specific type.
        Args:
            effect_type (type[Effect]): The type of effect to filter by.
        Returns:
            list[ActiveEffect]: A list of active effects of the specified type.
        """
        return [
            active
            for active in self.active_effects
            if isinstance(active.effect, effect_type)
        ]

    def get_total_bonus_from_effects(self, bonus_type: BonusType) -> int:
        """
        Computes the total modifier from active effects for a given BonusType.
        Args:
            bonus_type (BonusType): The bonus type to compute.
        Returns:
            int: Total bonus or malus from all matching effects.
        """
        total = 0
        assert bonus_type in [
            BonusType.HP,
            BonusType.MIND,
            BonusType.AC,
            BonusType.INITIATIVE,
        ], f"Invalid bonus type: {bonus_type}"
        for active in self.active_effects:
            if isinstance(active.effect, Buff):
                if bonus_type in active.effect.modifiers:
                    total += evaluate_expression(
                        active.effect.modifiers[bonus_type], self, active.mind_level
                    )
        return total

    def get_effect_usefulness_index(self, effect: Effect) -> int:
        """Computes how much the character needs a specific effect.

        Args:
            effect (Effect): The effect to check.

        Returns:
            int: The index of the effect in the active effects list, or -1 if not found.
        """
        usefulness_index = 0
        for existing_effect in self.get_all_effects_of_type(Buff):
            usefulness_index += existing_effect.duration < effect.max_duration
            # If the target already has the buff, we don't need to buff them.
            if effect.is_stronger_than(existing_effect.effect):
                usefulness_index += 1
        return usefulness_index

    def get_all_melee_damage_bonuses(self) -> list[str]:
        """
        Returns a list of all melee damage bonuses from active effects.
        This is used to apply additional damage to melee attacks.
        """
        bonus_list: list[str] = []
        for active in self.active_effects:
            if isinstance(active.effect, Buff):
                if BonusType.DAMAGE in active.effect.modifiers:
                    bonus_list.append(active.effect.modifiers[BonusType.DAMAGE])
        return bonus_list

    def get_all_bonuses_from_effects_of_type(self, bonus_type: BonusType) -> list[str]:
        bonus_list: list[str] = []
        for active in self.active_effects:
            if isinstance(active.effect, Buff):
                if bonus_type in active.effect.modifiers:
                    bonus_list.append(active.effect.modifiers[bonus_type])
        return bonus_list

    def get_remaining_effect_duration(self, effect: Any) -> int:
        """
        Returns the remaining duration of a specific effect on the character.

        Args:
            effect (Effect): The effect to check.

        Returns:
            int: The remaining duration of the effect, or 0 if not found.
        """
        for active in self.active_effects:
            if active.effect == effect:
                return active.duration
        return 0

    def can_equip_weapon(self, weapon: Any) -> bool:
        """
        Checks if the character can equip a specific weapon.

        Args:
            weapon (Weapon): The weapon to check.

        Returns:
            bool: True if the weapon can be equipped, False otherwise.
        """
        if not hasattr(weapon, "hands_required"):
            warning(
                f"{self.name} cannot equip {weapon.name} because it is not a valid weapon."
            )
            return False
        return (self.hands_used + weapon.hands_required) <= self.total_hands

    def can_equip_armor(self, armor: Any) -> bool:
        """Checks if the character can equip a specific armor.

        Args:
            armor (Armor): The armor to check.

        Returns:
            bool: True if the armor can be equipped, False otherwise.
        """
        if not hasattr(armor, "armor_slot"):
            warning(
                f"{self.name} cannot equip {armor.name} because it is not a valid armor."
            )
            return False
        # Check if the armor slot is already occupied.
        for equipped in self.equipped_armor:
            if equipped.armor_slot == armor.armor_slot:
                warning(
                    f"{self.name} already has armor in slot {armor.armor_slot.name}. Cannot equip {armor.name}."
                )
                return False
        # If the armor slot is not occupied, we can equip it.
        return True

    def equip_weapon(self, weapon: Any) -> bool:
        """Equips a weapon to the character's weapon slots.

        Args:
            weapon (Weapon): The weapon to equip.
        """
        if not hasattr(weapon, "hands_required"):
            warning(
                f"{self.name} cannot equip {weapon.name} because it is not a valid weapon."
            )
            return False
        if self.can_equip_weapon(weapon):
            self.equipped_weapons.append(weapon)
            self.hands_used += weapon.hands_required
            return True
        warning(f"{self.name} does not have enough free hands to equip {weapon.name}.")
        return False

    def remove_weapon(self, weapon: Any) -> bool:
        """Removes a weapon from the character's equipped weapons.

        Args:
            weapon (Weapon): The weapon to remove.
        """
        if not hasattr(weapon, "hands_required"):
            warning(
                f"{self.name} cannot remove {weapon.name} because it is not a valid weapon."
            )
            return False
        if weapon in self.equipped_weapons:
            debug(f"Unequipping weapon: {weapon.name} from {self.name}")
            self.equipped_weapons.remove(weapon)
            self.hands_used -= weapon.hands_required
            return True
        warning(f"{self.name} does not have {weapon.name} equipped.")
        return False

    def add_armor(self, armor: Any) -> bool:
        """
        Adds an armor effect to the character's list of equipped armor.
        """
        if not hasattr(armor, "armor_slot"):
            warning(
                f"{self.name} cannot equip {armor.name} because it is not a valid armor."
            )
            return False
        if self.can_equip_armor(armor):
            debug(f"Equipping armor: {armor.name} for {self.name}")
            # Add the armor to the character's armor list.
            self.equipped_armor.append(armor)
            return True
        warning(
            f"{self.name} cannot equip {armor.name} because the armor slot is already occupied."
        )
        return False

    def remove_armor(self, armor: Any) -> bool:
        """
        Removes an armor effect from the character's list of equipped armor.
        """
        if not hasattr(armor, "armor_slot"):
            warning(
                f"{self.name} cannot unequip {armor.name} because it is not a valid armor."
            )
            return False
        if armor in self.equipped_armor:
            debug(f"Unequipping armor: {armor.name} from {self.name}")
            # Remove the armor from the character's armor list.
            self.equipped_armor.remove(armor)
            return True
        warning(f"{self.name} does not have {armor.name} equipped.")
        return False

    def turn_update(self):
        """
        Updates the duration of all active effects. Removes expired effects.
        This should be called at the end of a character's turn or a round.
        """
        effects_to_remove: list[ActiveEffect] = []
        for active in self.active_effects:
            active.effect.turn_update(active.source, self, active.mind_level)
            # Decrease the duration of the effect.
            active.duration -= 1
            # If the duration is less than or equal to zero, remove the effect.
            if active.duration <= 0:
                console.print(
                    f"    :hourglass_done: [bold yellow]{active.effect.name}[/] has expired on [bold]{self.name}[/]."
                )
                effects_to_remove.append(active)
        for active in effects_to_remove:
            self.remove_effect(active)

    def get_status_line(self):
        effects = (
            ", ".join(
                f"[{get_effect_color(e.effect)}]" + e.effect.name + "[/]"
                for e in self.active_effects
            )
            if self.active_effects
            else ""
        )
        hp_bar = make_bar(self.hp, self.HP_MAX, color="green")

        status = f"{get_character_type_emoji(self.type)} [bold]{self.name:<10}[/] "
        status += f"| AC: [bold yellow]{self.AC}[/] "
        status += f"| HP: [green]{self.hp}[/]/[bold green]{self.HP_MAX}[/] {hp_bar} "
        if self.MIND_MAX > 0:
            mind_bar = make_bar(self.mind, self.MIND_MAX, color="blue")
            status += f"| MIND: [blue]{self.mind}[/]/[bold blue]{self.MIND_MAX}[/] {mind_bar} "
        if effects:
            status += f"| Effects: {effects}"
        return status

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type.name,
            "race": self.race.name,
            "levels": {cls.name: lvl for cls, lvl in self.levels.items()},
            "stats": self.stats,
            "spellcasting_ability": self.spellcasting_ability,
            "equipped_weapons": [w.name for w in self.equipped_weapons],
            "equipped_armor": [a.name for a in self.equipped_armor],
            "actions": list(self.actions.keys()),
            "spells": list(self.spells.keys()),
        }

    @staticmethod
    def from_dict(data: dict[str, Any], registries: dict[str, Any]) -> "Character":
        cls_registry = registries["classes"]
        race_registry = registries["races"]

        # Load the race from the races registry.
        race = race_registry[data["race"]]

        # Load the levels from the class registry.
        levels: dict[CharacterClass, int] = {}
        for cls_name, cls_level in data["levels"].items():
            if cls_name not in cls_registry:
                warning(f"CharacterClass {cls_name} not found in registry.")
                continue
            levels[cls_registry[cls_name]] = cls_level

        # Create the character instance.
        char = Character(
            name=data["name"],
            race=race,
            levels=levels,
            strength=data["stats"]["strength"],
            dexterity=data["stats"]["dexterity"],
            constitution=data["stats"]["constitution"],
            intelligence=data["stats"]["intelligence"],
            wisdom=data["stats"]["wisdom"],
            charisma=data["stats"]["charisma"],
            spellcasting_ability=data.get("spellcasting_ability", None),
        )

        # Set the character as a player if specified.
        char.type = CharacterType[data.get("type", "ENEMY").upper()]

        # Load the weapons.
        for equipped_weapon_data in data.get("equipped_weapons", []):
            char.equip_weapon(BaseAction.from_dict(equipped_weapon_data))

        # Load the armor.
        for equipped_armor_data in data.get("equipped_armor", []):
            char.add_armor(Effect.from_dict(equipped_armor_data))

        # Load the actions.
        for action_data in data.get("actions", []):
            char.learn_action(BaseAction.from_dict(action_data))

        # Load the spells.
        for spell_data in data.get("spells", []):
            char.learn_spell(BaseAction.from_dict(spell_data))

        return char


def load_character_classes(file_path: str) -> dict[str, CharacterClass]:
    """
    Loads character classes from a JSON file.

    Args:
        file_path (str): The path to the JSON file containing character classes.

    Returns:
        dict[str, CharacterClass]: A dictionary mapping class names to CharacterClass instances.
    """
    classes: dict[str, CharacterClass] = {}
    with open(file_path, "r") as f:
        class_data = json.load(f)
        for entry in class_data:
            character_class = CharacterClass.from_dict(entry)
            classes[character_class.name] = character_class
    return classes


def load_character_races(file_path: str) -> dict[str, CharacterRace]:
    """Loads character races from a JSON file.

    Args:
        file_path (str): The path to the JSON file containing character races.

    Returns:
        dict[str, CharacterRace]: A dictionary mapping race names to CharacterRace instances.
    """
    races: dict[str, CharacterRace] = {}
    with open(file_path, "r") as f:
        race_data = json.load(f)
        for entry in race_data:
            character_race = CharacterRace.from_dict(entry)
            races[character_race.name] = character_race
    return races


def load_characters(file_path: str, registries: dict[str, Any]) -> dict[str, Character]:
    """
    Loads characters from a JSON file.

    Args:
        file_path (str): The path to the JSON file containing character data.
        registries (dict[str, Any]): A dictionary containing registries for classes and races.

    Returns:
        dict[str, Character]: A dictionary mapping character names to Character instances.
    """
    characters: dict[str, Character] = {}
    with open(file_path, "r") as f:
        character_data = json.load(f)
        for entry in character_data:
            character = Character.from_dict(entry, registries)
            characters[character.name] = character
    return characters


def load_player_character(
    file_path: str, registries: dict[str, Any]
) -> Character | None:
    """
    Loads the player character from a JSON file.

    Args:
        file_path (str): The path to the JSON file containing player character data.
        registries (dict[str, Any]): A dictionary containing registries for classes and races.

    Returns:
        Character: The loaded player character.
    """
    with open(file_path, "r") as f:
        player_data = json.load(f)
        player = Character.from_dict(player_data, registries)
        # Mark the character as a player character.
        player.type = CharacterType.PLAYER
        return player


def sort_for_weapon_attack(
    actor: Character, action: WeaponAttack, targets: list[Character]
) -> list[Character]:
    """
    Compares two characters based on their offensive capabilities.
    Returns True if char1 is more offensive than char2, False otherwise.
    """
    return sorted(
        targets,
        key=lambda c: (
            c.AC,
            c.hp / c.HP_MAX if c.HP_MAX > 0 else 1,
            (
                len(c.get_all_effects_of_type(DoT))
                if isinstance(action.effect, DoT)
                else 1
            ),
        ),
    )


def sort_for_spell_heal(
    actor: Character, action: SpellHeal, targets: list[Character]
) -> list[Character]:
    """
    Compares two characters based on their need for healing, or healing effects.
    """
    # Filter out targets who are already at full HP or already affected by the heal's effect.
    targets = [target for target in targets if target.hp < target.HP_MAX]
    return sorted(
        targets,
        key=lambda c: (
            c.hp / c.HP_MAX if c.HP_MAX > 0 else 1,
            (
                len(c.get_all_effects_of_type(HoT))
                if isinstance(action.effect, HoT)
                else 1
            ),
        ),
    )


def sort_for_spell_attack(
    actor: Character, action: SpellAttack, targets: list[Character]
) -> list[Character]:
    """
    Compares two characters based on their need for offensive spells.
    """
    return sorted(
        targets,
        key=lambda c: (
            c.AC,
            c.hp / c.HP_MAX if c.HP_MAX > 0 else 1,
            (
                len(c.get_all_effects_of_type(DoT))
                if isinstance(action.effect, DoT)
                else 1
            ),
        ),
    )


def sort_for_spell_buff(
    actor: Character, action: SpellBuff, targets: list[Character]
) -> list[Character]:
    """
    Compares two characters based on their need for defensive spells.
    """
    # Compute a numerical value that identifies how much a character needs a buff.
    usefulness_index: dict[Character, int] = {}
    for target in targets:
        usefulness_index[target] = target.get_effect_usefulness_index(action.effect)
    # Sort based on the need for the buff.
    return sorted(
        targets,
        key=lambda c: (usefulness_index.get(c, 0)),
    )
