import json
from logging import debug, warning
from typing import Any, Tuple
from rich.console import Console

from constants import *
from actions import *
from effect_manager import *
from effect import *
from utils import *
from character_class import *
from character_race import *
from content import ContentRepository

console = Console()


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
        # List of available attacks.
        self.attacks: list[FullAttack] = []
        self.total_hands: int = 2
        self.hands_used: int = 0
        # List of equipped armor.
        self.equipped_armor: list[Armor] = []
        # Manages active effects on the character.
        self.effect_manager: EffectManager = EffectManager(self)
        # List of actions.
        self.actions: dict[str, BaseAction] = {}
        # List of spells
        self.spells: dict[str, Spell] = {}
        # Turn flags to track used actions.
        self.turn_flags: dict[str, bool] = {
            "standard_action_used": False,
            "bonus_action_used": False,
        }
        # Resistances and vulnerabilities to damage types.
        self.resistances: set[DamageType] = set()
        self.vulnerabilities: set[DamageType] = set()
        # Keep track of abilitiies cooldown.
        self.cooldowns: dict[str, int] = {}
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
        hp_max += self.effect_manager.get_modifier(BonusType.HP)
        return hp_max

    @property
    def MIND_MAX(self) -> int:
        """Returns the maximum Mind of the character."""
        mind_max: int = 0
        # Add the class levels' Mind multipliers to the max Mind.
        for cls, cls_level in self.levels.items():
            mind_max += max(0, (cls.mind_mult + self.SPELLCASTING)) * cls_level
        # Add the effect modifiers to the max Mind.
        mind_max += self.effect_manager.get_modifier(BonusType.MIND)
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
        effect_ac = self.effect_manager.get_modifier(BonusType.AC)

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
        initiative += self.effect_manager.get_modifier(BonusType.INITIATIVE)
        return initiative

    def get_expression_modifiers(self) -> dict[str, int]:
        """Returns a dictionary of the character's modifiers.

        Returns:
            dict[str, int]: A dictionary containing the character's modifiers.
        """
        return {
            "SPELLCASTING": self.SPELLCASTING,
            "STR": self.STR,
            "DEX": self.DEX,
            "CON": self.CON,
            "INT": self.INT,
            "WIS": self.WIS,
            "CHA": self.CHA,
        }

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

    def take_damage(self, amount: int, damage_type: DamageType) -> Tuple[int, int, int]:
        """
        Applies damage to the character, factoring in resistances and vulnerabilities.

        Args:
            amount (int): The raw base damage.
            damage_type (DamageType): The type of damage being dealt.

        Returns:
            Tuple[int, int, int]: (base_damage, adjusted_damage, damage_taken)
        """
        base = amount
        adjusted = base
        if damage_type in self.resistances:
            adjusted = adjusted // 2
        elif damage_type in self.vulnerabilities:
            adjusted = adjusted * 2
        adjusted = max(adjusted, 0)
        actual = min(adjusted, self.hp)
        self.hp = max(self.hp - adjusted, 0)
        return base, adjusted, actual

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

    def can_add_attack(self, full_attack: FullAttack) -> bool:
        """
        Checks if the character can add a specific full_attack.

        Args:
            full_attack (FullAttack): The full_attack to check.

        Returns:
            bool: True if the full_attack can be added, False otherwise.
        """
        hands_required = sum(attack.hands_required for attack in full_attack.attacks)
        return (self.hands_used + hands_required) <= self.total_hands

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

    def add_attack(self, full_attack: FullAttack) -> bool:
        """Adds an attack to the character's equipped attacks.

        Args:
            full_attack (FullAttack): The attack to add.
        """
        if self.can_add_attack(full_attack):
            self.attacks.append(full_attack)
            self.hands_used += sum(
                attack.hands_required for attack in full_attack.attacks
            )
            return True
        warning(
            f"{self.name} does not have enough free hands to equip {full_attack.name}."
        )
        return False

    def remove_attack(self, full_attack: FullAttack) -> bool:
        """Removes an attack from the character's equipped attacks.

        Args:
            full_attack (FullAttack): The attack to remove.
        """
        if full_attack in self.attacks:
            debug(f"Unequipping attack: {full_attack.name} from {self.name}")
            self.attacks.remove(full_attack)
            self.hands_used -= sum(
                attack.hands_required for attack in full_attack.attacks
            )
            return True
        warning(f"{self.name} does not have {full_attack.name} equipped.")
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
        """Updates the duration of all active effects, and cooldowns. Removes
        expired effects. This should be called at the end of a character's turn
        or a round."""
        self.effect_manager.turn_update()
        # Iterate the cooldowns and decrement them.
        for action_name in list(self.cooldowns.keys()):
            if self.cooldowns[action_name] > 0:
                self.cooldowns[action_name] -= 1
        # Clear expired cooldowns.
        self.cooldowns = {
            action_name: cd for action_name, cd in self.cooldowns.items() if cd > 0
        }

    def add_cooldown(self, action: BaseAction, duration: int):
        """Adds a cooldown to an action.

        Args:
            action_name (BaseAction): The action to add a cooldown to.
            duration (int): The duration of the cooldown in turns.
        """
        if action.name not in self.cooldowns:
            self.cooldowns[action.name] = duration + 1

    def is_on_cooldown(self, action: BaseAction) -> bool:
        """Checks if an action is currently on cooldown.

        Args:
            action (BaseAction): The action to check.

        Returns:
            bool: True if the action is on cooldown, False otherwise.
        """
        return self.cooldowns.get(action.name, 0) > 0

    def get_status_line(self):
        effects = (
            ", ".join(
                f"[{get_effect_color(e.effect)}]"
                + e.effect.name
                + f"[/] ({e.duration})"
                for e in self.effect_manager.active_effects
            )
            if self.effect_manager.active_effects
            else ""
        )
        hp_bar = make_bar(self.hp, self.HP_MAX, color="green")

        status = f"{get_character_type_emoji(self.type)} [bold]{self.name:<14}[/] "
        status += f"| AC: [bold yellow]{self.AC}[/] "
        status += (
            f"| HP: [green]{self.hp:>3}[/]/[bold green]{self.HP_MAX:<3}[/] {hp_bar} "
        )
        if self.MIND_MAX > 0:
            mind_bar = make_bar(self.mind, self.MIND_MAX, color="blue")
            status += f"| MIND: [blue]{self.mind:>3}[/]/[bold blue]{self.MIND_MAX:<3}[/] {mind_bar} "
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
            "attacks": [w.name for w in self.attacks],
            "equipped_armor": [a.name for a in self.equipped_armor],
            "actions": list(self.actions.keys()),
            "spells": list(self.spells.keys()),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Character | None":

        # Get the content repositories.
        repo = ContentRepository()

        # Load the race from the races registry.
        race = repo.get_character_race(data["race"])
        if race is None:
            warning(f"Invalid race '{data['race']}' for character {data['name']}.")
            return None

        # Load the levels from the class registry.
        levels: dict[CharacterClass, int] = {}
        for cls_name, cls_level in data["levels"].items():
            # Get the class from the class registry.
            character_class = repo.get_character_class(cls_name)
            if character_class is None:
                warning(f"Invalid class '{cls_name}' for character {data['name']}.")
                return None
            # Add the class and its level to the levels dictionary.
            levels[character_class] = cls_level

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

        # Load resistances and vulnerabilities if present in the data.
        if "resistances" in data:
            for res in data["resistances"]:
                try:
                    char.resistances.add(DamageType[res.upper()])
                except KeyError:
                    warning(
                        f"Invalid damage type '{res}' in resistances for {char.name}."
                    )
        if "vulnerabilities" in data:
            for vuln in data["vulnerabilities"]:
                try:
                    char.vulnerabilities.add(DamageType[vuln.upper()])
                except KeyError:
                    warning(
                        f"Invalid damage type '{vuln}' in vulnerabilities for {char.name}."
                    )

        # Set the character as a player if specified.
        char.type = CharacterType[data.get("type", "ENEMY").upper()]

        # Load the attacks.
        for attack in data.get("attacks", []):
            if isinstance(attack, str):
                base_attack = repo.get_base_attack(attack)
                if base_attack is None:
                    warning(f"Invalid attack '{attack}' for character {char.name}.")
                    continue
                char.add_attack(
                    FullAttack(
                        name=base_attack.name,
                        type=ActionType.STANDARD,
                        cooldown=base_attack.cooldown,
                        attacks=[base_attack],
                    )
                )
            elif isinstance(attack, dict) and attack.get("class") == "FullAttack":
                full_attack = FullAttack.from_dict(attack, repo.attacks)
                if full_attack is None:
                    warning(
                        f"Invalid full attack '{attack}' for character {char.name}."
                    )
                    continue
                char.add_attack(full_attack)

        # Load the armor.
        for equipped_armor in data.get("equipped_armor", []):
            equipped_armor = repo.get_armor(equipped_armor)
            if equipped_armor is None:
                warning(
                    f"Invalid armor '{equipped_armor}' for character {data['name']}."
                )
                continue
            char.add_armor(equipped_armor)

        # Load the actions.
        for action_name in data.get("actions", []):
            action = repo.get_action(action_name)
            if action is None:
                warning(f"Invalid action '{action_name}' for character {data['name']}.")
                continue
            char.learn_action(action)

        # Load the spells.
        for spell_data in data.get("spells", []):
            spell = repo.get_spell(spell_data)
            if spell is None:
                warning(f"Invalid spell '{spell_data}' for character {data['name']}.")
                continue
            char.learn_spell(spell)

        return char


def load_characters(file_path: str) -> dict[str, Character]:
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
            character = Character.from_dict(entry)
            if character is not None:
                characters[character.name] = character
    return characters


def load_player_character(file_path: str) -> Character | None:
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
        player = Character.from_dict(player_data)
        if player is None:
            warning(f"Failed to load player character from {file_path}.")
            return None
        # Mark the character as a player character.
        player.type = CharacterType.PLAYER
        return player


def print_character_details(char: Character):
    """Prints the details of a character in a formatted way."""

    console.print(
        f"{get_character_type_emoji(char.type)} [{get_character_type_color(char.type)}]{char.name}[/], [blue]{char.race.name}[/], {', '.join([f'[green]{cls.name} {lvl}[/]' for cls, lvl in char.levels.items()])}, hp: {char.hp}, ac: {char.AC}"
    )
    console.print(
        f"  {', '.join([f'{stat}: {value}' for stat, value in char.stats.items()])}"
    )
    if char.equipped_armor:
        console.print(f"  Armor:")
        for armor in char.equipped_armor:
            console.print(
                f"    - [blue]{armor.name}[/], {get_armor_type_emoji(armor.armor_type)}, {armor.ac}"
            )
    if char.attacks:
        console.print(f"  Attacks:")
        for full_attack in char.attacks:
            if len(full_attack.attacks) == 1:
                attack = full_attack.attacks[0]
                console.print(
                    f"    - [green]{attack.name}[/], [blue]1D20+{attack.attack_roll}[/], damage: [blue]{'+ '.join([f'{damage_component.damage_roll} {damage_component.damage_type.name}' for damage_component in attack.damage])}[/]"
                )
            else:
                console.print(
                    f"    - [green]{full_attack.name}[/], [{get_action_type_color(full_attack.type)}]{full_attack.type.name}[/], cooldown: {full_attack.cooldown}, attacks:"
                )
                for i, attack in enumerate(full_attack.attacks, start=1):
                    console.print(
                        f"      {i}. [green]{attack.name}[/], [blue]1D20+{attack.attack_roll}[/], damage: [blue]{'+ '.join([f'{damage_component.damage_roll} {damage_component.damage_type.name}' for damage_component in attack.damage])}[/]"
                    )
    if char.actions:
        console.print(f"  Actions:")
        for action in char.actions.values():
            console.print(
                f"    - [green]{action.name}[/], [{get_action_type_color(action.type)}]{action.type.name}[/]"
            )
    if char.spells:
        console.print(f"  Spellcasting ability: {char.spellcasting_ability}")
        console.print(f"  Spells:")
        for spell in char.spells.values():
            console.print(
                f"    - [green]{spell.name}[/], lv {spell.level}, [{get_action_type_color(spell.type)}]{spell.type.name}[/]"
            )
    if char.resistances:
        console.print(
            f"  Resistances: {', '.join([f"[{get_damage_type_color(r)}]{r.name}[/]" for r in char.resistances])}"
        )
    if char.vulnerabilities:
        console.print(
            f"  Vulnerabilities: {', '.join([f"[{get_damage_type_color(v)}]{v.name}[/]" for v in char.vulnerabilities])}"
        )
