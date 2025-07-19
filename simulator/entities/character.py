import json
from logging import debug, warning
from pathlib import Path
from typing import Any, Optional, Tuple

from actions.base_action import BaseAction
from actions.attack_action import BaseAttack, NaturalAttack, WeaponAttack
from actions.spell_action import Spell
from core.constants import (
    ActionType,
    ArmorSlot,
    BonusType,
    CharacterType,
    DamageType,
    get_character_type_emoji,
    get_effect_color,
)
from core.content import ContentRepository
from core.error_handling import GameError, ErrorSeverity, error_handler
from core.utils import get_stat_modifier, make_bar
from effects.effect import Effect
from effects.effect_manager import EffectManager
from entities.character_class import CharacterClass
from entities.character_race import CharacterRace
from items.armor import Armor
from items.weapon import Weapon


class Character:
    def __init__(
        self,
        char_type: CharacterType,
        name: str,
        race: CharacterRace,
        levels: dict[CharacterClass, int],
        stats: dict[str, int],
        spellcasting_ability: Optional[str] = None,
        total_hands: int = 2,
        resistances: set[DamageType] = set(),
        vulnerabilities: set[DamageType] = set(),
        number_of_attacks: int = 1,
    ):
        # Determines if the character is a player or an NPC.
        self.type: CharacterType = char_type
        # Name of the character.
        self.name: str = name
        # The character race.
        self.race: CharacterRace = race
        # The character's class levels.
        self.levels: dict[CharacterClass, int] = levels
        # Stats.
        self.stats: dict[str, int] = stats
        # Spellcasting Ability.
        self.spellcasting_ability: Optional[str] = spellcasting_ability
        # List of available attacks.
        self.total_hands: int = total_hands
        # Resistances and vulnerabilities to damage types.
        self.resistances: set[DamageType] = resistances
        self.vulnerabilities: set[DamageType] = vulnerabilities
        # Number of attacks.
        self.number_of_attacks: int = number_of_attacks

        # === Dynamic Properties ===

        # List of equipped weapons.
        self.equipped_weapons: list[Weapon] = list()
        # List of natural weapons, if any.
        self.natural_weapons: list[Weapon] = []
        # List of equipped armor.
        self.equipped_armor: list[Armor] = list()
        # List of actions.
        self.actions: dict[str, BaseAction] = dict()
        # List of spells
        self.spells: dict[str, Spell] = dict()

        # Turn flags to track used actions.
        self.turn_flags: dict[str, bool] = {
            "standard_action_used": False,
            "bonus_action_used": False,
        }
        # Manages active effects on the character.
        self.effect_manager: EffectManager = EffectManager(self)
        # Passive effects that are always active (like boss phase triggers)
        self.passive_effects: list[Effect] = []
        # Keep track of abilitiies cooldown.
        self.cooldowns: dict[str, int] = {}
        # Keep track of the uses of abilities.
        self.uses: dict[str, int] = {}
        # Maximum HP and Mind.
        self.hp: int = self.HP_MAX
        self.mind: int = self.MIND_MAX

    @property
    def HP_MAX(self) -> int:
        """Returns the maximum HP of the character."""
        hp_max: int = 0
        # Add the class levels' HP multipliers to the max HP.
        for cls, lvl in self.levels.items():
            hp_max += lvl * (cls.hp_mult + self.CON)
        # Add the effect modifiers to the max HP.
        hp_max += self.effect_manager.get_modifier(BonusType.HP)
        return hp_max

    @property
    def MIND_MAX(self) -> int:
        """Returns the maximum Mind of the character."""
        mind_max: int = 0
        # Add the class levels' Mind multipliers to the max Mind.
        for cls, lvl in self.levels.items():
            mind_max += lvl * (cls.mind_mult + self.SPELLCASTING)
        # Add the effect modifiers to the max Mind.
        mind_max += self.effect_manager.get_modifier(BonusType.MIND)
        return mind_max

    @property
    def STR(self) -> int:
        """Returns the DnD strength modifier."""
        return get_stat_modifier(self.stats["strength"])

    @property
    def DEX(self) -> int:
        """Returns the DnD dexterity modifier."""
        return get_stat_modifier(self.stats["dexterity"])

    @property
    def CON(self) -> int:
        """Returns the DnD constitution modifier."""
        return get_stat_modifier(self.stats["constitution"])

    @property
    def INT(self) -> int:
        """Returns the DnD intelligence modifier."""
        return get_stat_modifier(self.stats["intelligence"])

    @property
    def WIS(self) -> int:
        """Returns the DnD wisdom modifier."""
        return get_stat_modifier(self.stats["wisdom"])

    @property
    def CHA(self) -> int:
        """Returns the DnD charisma modifier."""
        return get_stat_modifier(self.stats["charisma"])

    @property
    def SPELLCASTING(self) -> int:
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

        # If there is equipped armor, replace base AC.
        if self.equipped_armor:
            base_ac = sum(armor.get_ac(self.DEX) for armor in self.equipped_armor)

        # Add effect bonuses to AC.
        effect_ac = self.effect_manager.get_modifier(BonusType.AC)

        # Determine final AC.
        race_bonus = self.race.natural_ac if self.race else 0
        return base_ac + race_bonus + effect_ac

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

    def get_expression_variables(self) -> dict[str, int]:
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

    @property
    def CONCENTRATION_LIMIT(self) -> int:
        """Calculate the maximum number of concentration effects this character can maintain.

        Returns:
            int: Maximum concentration effects
        """
        base_limit = max(1, 1 + (self.SPELLCASTING // 2))
        concentration_bonus = self.effect_manager.get_modifier(BonusType.CONCENTRATION)

        # Handle different return types from get_modifier
        if isinstance(concentration_bonus, list):
            # Sum up all concentration bonuses if it's a list
            bonus_value = sum(
                bonus for bonus in concentration_bonus if isinstance(bonus, int)
            )
        elif isinstance(concentration_bonus, int):
            bonus_value = concentration_bonus
        else:
            bonus_value = 0

        return max(1, base_limit + bonus_value)

    def reset_turn_flags(self) -> None:
        """Resets the turn flags for the character."""
        self.turn_flags["standard_action_used"] = False
        self.turn_flags["bonus_action_used"] = False

    def use_action_type(self, action_type: ActionType) -> None:
        """Marks an action type as used for the current turn."""
        if action_type == ActionType.STANDARD:
            self.turn_flags["standard_action_used"] = True
        elif action_type == ActionType.BONUS:
            self.turn_flags["bonus_action_used"] = True

    def has_action_type(self, action_type: ActionType) -> bool:
        """Checks if the character can use a specific action type this turn."""
        if action_type == ActionType.STANDARD:
            return not self.turn_flags["standard_action_used"]
        elif action_type == ActionType.BONUS:
            return not self.turn_flags["bonus_action_used"]
        return True

    def get_available_natural_weapon_attacks(self) -> list["NaturalAttack"]:
        """Returns a list of natural weapon attacks available to the character.

        Returns:
            list[NaturalAttack]: A list of natural weapon attacks.
        """
        from actions.attack_action import NaturalAttack

        result: list[NaturalAttack] = []
        # Iterate through the natural weapons and check if they are available.
        for weapon in self.natural_weapons:
            for attack in weapon.attacks:
                if self.is_on_cooldown(attack):
                    continue
                if not self.has_action_type(attack.type):
                    continue
                # Only include NaturalAttack instances
                if isinstance(attack, NaturalAttack):
                    result.append(attack)
        return result

    def get_available_weapon_attacks(self) -> list["WeaponAttack"]:
        """Returns a list of weapon attacks that the character can use this turn."""
        from actions.attack_action import WeaponAttack

        result: list[WeaponAttack] = []
        # Iterate through the equipped weapons and check if they are available.
        for weapon in self.equipped_weapons:
            for attack in weapon.attacks:
                if self.is_on_cooldown(attack):
                    continue
                if not self.has_action_type(attack.type):
                    continue
                # Only include WeaponAttack instances
                if isinstance(attack, WeaponAttack):
                    result.append(attack)
        return result

    def get_available_attacks(self) -> list[BaseAction]:
        """Returns a list of all attacks (weapon + natural) that the character can use this turn."""
        result: list[BaseAction] = []
        result.extend(self.get_available_weapon_attacks())
        result.extend(self.get_available_natural_weapon_attacks())
        return result

    def get_available_actions(self) -> list[BaseAction]:
        """Returns a list of actions that the character can use this turn."""
        available_actions = []
        for action in self.actions.values():
            if not self.is_on_cooldown(action) and self.has_action_type(action.type):
                available_actions.append(action)
        return available_actions

    def get_available_spells(self) -> list[Spell]:
        """Returns a list of spells that the character can use this turn."""
        available_spells = []
        for spell in self.spells.values():
            if not self.is_on_cooldown(spell) and self.has_action_type(spell.type):
                # Check if the character has enough mind points to cast the spell.
                if self.mind >= (spell.mind_cost[0] if spell.mind_cost else 0):
                    available_spells.append(spell)
        return available_spells

    def turn_done(self) -> bool:
        """
        Checks if the character has used both a standard and bonus action this turn.
        Returns True if both actions are used, False otherwise.
        """
        available_actions = self.get_available_actions() + self.get_available_spells()
        # Check if the character has any bonus actions available.
        has_bonus_actions = any(
            action.type == ActionType.BONUS for action in available_actions
        )
        if has_bonus_actions and not self.turn_flags["bonus_action_used"]:
            return False
        return self.turn_flags["standard_action_used"]

    def check_passive_triggers(self) -> list[str]:
        """
        Checks all passive effects for trigger conditions and activates them.
        Returns a list of activation messages for triggered effects.
        
        Returns:
            list[str]: Messages for effects that were triggered this check.
        """
        activation_messages = []
        
        for effect in self.passive_effects:
            # Check for OnLowHealthTrigger specifically
            if effect.__class__.__name__ == 'OnLowHealthTrigger':
                # Import here to avoid circular imports
                from effects.effect import OnLowHealthTrigger
                trigger_effect: OnLowHealthTrigger = effect  # type: ignore
                
                if trigger_effect.should_trigger(self):
                    # Activate the trigger
                    damage_bonuses, trigger_effects_with_levels = trigger_effect.activate(self)
                    
                    # Apply triggered effects to self
                    for triggered_effect, mind_level in trigger_effects_with_levels:
                        if triggered_effect.can_apply(self, self):
                            self.effect_manager.add_effect(self, triggered_effect, mind_level)
                    
                    # Create activation message
                    from core.constants import get_effect_color
                    activation_messages.append(
                        f"🔥 {self.name}'s [bold][{get_effect_color(effect)}]{effect.name}[/][/] activates!"
                    )
        
        return activation_messages

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
        
        # Check for passive triggers after taking damage (e.g., OnLowHealthTrigger)
        if self.passive_effects and self.is_alive():
            activation_messages = self.check_passive_triggers()
            if activation_messages:
                from core.utils import cprint
                for msg in activation_messages:
                    cprint(f"    {msg}")
        
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

    def get_occupied_hands(self) -> int:
        """Returns the number of hands currently occupied by equipped weapons and armor."""
        used_hands = sum(item.hands_required for item in self.equipped_weapons)
        used_hands += sum(
            armor.armor_slot == ArmorSlot.SHIELD for armor in self.equipped_armor
        )
        return used_hands

    def get_free_hands(self) -> int:
        """Returns the number of free hands available for equipping items."""
        return self.total_hands - self.get_occupied_hands()

    def can_equip_weapon(self, weapon: Weapon) -> bool:
        """Checks if the character can equip a specific weapon.

        Args:
            weapon (Weapon): The weapon to check.

        Returns:
            bool: True if the weapon can be equipped, False otherwise.
        """
        # If the weapon requires no hands, it can always be equipped.
        if weapon.hands_required <= 0:
            return True
        # Check if the character has enough free hands to equip the weapon.
        if weapon.hands_required > self.get_free_hands():
            warning(
                f"{self.name} does not have enough free hands to equip {weapon.name}."
            )
            return False
        return True

    def add_weapon(self, weapon: Weapon) -> bool:
        """Adds a weapon to the character's equipped weapons.

        Args:
            weapon (Weapon): The weapon to equip.

        Returns:
            bool: True if the weapon was equipped successfully, False otherwise.
        """
        if self.can_equip_weapon(weapon):
            debug(f"Equipping weapon: {weapon.name} for {self.name}")
            # Add the weapon to the character's weapon list.
            self.equipped_weapons.append(weapon)
            return True
        warning(f"{self.name} cannot equip {weapon.name}.")
        return False

    def remove_weapon(self, weapon: Weapon) -> bool:
        """Removes a weapon from the character's equipped weapons.

        Args:
            weapon (Weapon): The weapon to remove.

        Returns:
            bool: True if the weapon was removed successfully, False otherwise.
        """
        if weapon in self.equipped_weapons:
            debug(f"Unequipping weapon: {weapon.name} from {self.name}")
            # Remove the weapon from the character's weapon list.
            self.equipped_weapons.remove(weapon)
            return True
        warning(f"{self.name} does not have {weapon.name} equipped.")
        return False

    def can_equip_armor(self, armor: Armor) -> bool:
        """Checks if the character can equip a specific armor.

        Args:
            armor (Armor): The armor to check.

        Returns:
            bool: True if the armor can be equipped, False otherwise.
        """
        # If the armor is a shield, it can be equipped if the character has a free hand.
        if armor.armor_slot == ArmorSlot.SHIELD:
            if self.get_free_hands() <= 0:
                warning(f"{self.name} does not have a free hand to equip {armor.name}.")
                return False
            return True
        # Otherwise, check if the armor slot is already occupied.
        for equipped in self.equipped_armor:
            if equipped.armor_slot == armor.armor_slot:
                warning(
                    f"{self.name} already has armor in slot {armor.armor_slot.name}. Cannot equip {armor.name}."
                )
                return False
        # If the armor slot is not occupied, we can equip it.
        return True

    def add_armor(self, armor: Armor) -> bool:
        """Adds an armor to the character's equipped armor.

        Args:
            armor (Armor): The armor to equip.

        Returns:
            bool: True if the armor was equipped successfully, False otherwise.
        """
        if self.can_equip_armor(armor):
            debug(f"Equipping armor: {armor.name} for {self.name}")
            # Add the armor to the character's armor list.
            self.equipped_armor.append(armor)
            return True
        warning(
            f"{self.name} cannot equip {armor.name} because the armor slot is already occupied."
        )
        return False

    def remove_armor(self, armor: Armor) -> bool:
        """Removes an armor from the character's equipped armor.

        Args:
            armor (Armor): The armor to remove.

        Returns:
            bool: True if the armor was removed successfully, False otherwise.
        """
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
        if action.name not in self.cooldowns and duration > 0:
            self.cooldowns[action.name] = duration + 1

    def is_on_cooldown(self, action: BaseAction) -> bool:
        """Checks if an action is currently on cooldown.

        Args:
            action (BaseAction): The action to check.

        Returns:
            bool: True if the action is on cooldown, False otherwise.
        """
        return self.cooldowns.get(action.name, 0) > 0

    def initialize_uses(self, action: BaseAction):
        """Initializes the uses of an action to its maximum uses.

        Args:
            action (BaseAction): The action to initialize uses for.
        """
        if action.name not in self.uses:
            # For unlimited use actions (-1), don't track uses
            if action.maximum_uses == -1:
                self.uses[action.name] = -1  # Unlimited
                debug(f"{self.name} initialized {action.name} with unlimited uses.")
            else:
                self.uses[action.name] = action.maximum_uses
                debug(f"{self.name} initialized {action.name} with {action.maximum_uses} uses.")

    def get_remaining_uses(self, action: BaseAction) -> int:
        """Returns the remaining uses of an action.

        Args:
            action (BaseAction): The action to check.

        Returns:
            int: The remaining uses of the action. Returns -1 for unlimited use actions.
        """
        if action.maximum_uses == -1:
            return -1  # Unlimited uses
        return self.uses.get(action.name, 0)

    def decrement_uses(self, action: BaseAction):
        """Decrements the uses of an action by 1.

        Args:
            action (BaseAction): The action to decrement uses for.
        """
        # Don't decrement unlimited use actions
        if action.maximum_uses == -1:
            return
            
        if action.name in self.uses:
            if self.uses[action.name] > 0:
                self.uses[action.name] -= 1
                debug(
                    f"{self.name} used {action.name}. Remaining uses: {self.uses[action.name]}"
                )
            else:
                warning(f"{self.name} has no remaining uses for {action.name}.")
        else:
            warning(f"{self.name} does not have {action.name} in their uses.")

    def get_status_line(self, show_all_effects: bool = False, show_numbers: bool = False, show_bars: bool = False, show_ac: bool = True):
        # Collect all effects with better formatting
        effects_list = []
        if self.effect_manager.active_effects:
            for e in self.effect_manager.active_effects:
                color = get_effect_color(e.effect)
                # Truncate long effect names and show duration more compactly
                effect_name = e.effect.name[:12] + "..." if len(e.effect.name) > 15 else e.effect.name
                effects_list.append(f"[{color}]{effect_name}[/]({e.duration})")
        
        # Build status line with better spacing
        hp_bar = make_bar(self.hp, self.HP_MAX, color="green", length=8) if show_bars else ""
        
        # Use dynamic name width based on name length, but cap it
        name_width = min(max(len(self.name), 8), 16)
        status = f"{get_character_type_emoji(self.type)} [bold]{self.name:<{name_width}}[/] "
        
        # Show AC only for player and allies (not enemies) with yellow color
        if show_ac:
            status += f"| [yellow]AC:{self.AC:>2}[/] "
        
        # Build HP display based on parameters with green color
        hp_display = ""
        if show_numbers and show_bars:
            hp_display = f"| [green]HP:{self.hp:>3}/{self.HP_MAX}[/]{hp_bar} "
        elif show_numbers:
            hp_display = f"| [green]HP:{self.hp:>3}/{self.HP_MAX}[/] "
        elif show_bars:
            hp_display = f"| [green]HP:[/]{hp_bar} "
        else:
            # Default to showing numbers if neither is specified
            hp_display = f"| [green]HP:{self.hp:>3}/{self.HP_MAX}[/] "
        status += hp_display
        
        if self.MIND_MAX > 0:
            mind_bar = make_bar(self.mind, self.MIND_MAX, color="blue", length=8) if show_bars else ""
            
            # Build MP display based on parameters with blue color
            mp_display = ""
            if show_numbers and show_bars:
                mp_display = f"| [blue]MP:{self.mind:>3}/{self.MIND_MAX}[/]{mind_bar} "
            elif show_numbers:
                mp_display = f"| [blue]MP:{self.mind:>3}/{self.MIND_MAX}[/] "
            elif show_bars:
                mp_display = f"| [blue]MP:[/]{mind_bar} "
            else:
                # Default to showing numbers if neither is specified
                mp_display = f"| [blue]MP:{self.mind:>3}/{self.MIND_MAX}[/] "
            status += mp_display

        # Show concentration info only for the player with magenta/purple color
        if (
            self.type == CharacterType.PLAYER
            and self.effect_manager.concentration_manager.get_concentration_count() > 0
        ):
            concentration_count = self.effect_manager.concentration_manager.get_concentration_count()
            concentration_limit = self.CONCENTRATION_LIMIT
            conc_bar = make_bar(concentration_count, concentration_limit, color="magenta", length=concentration_limit) if show_bars else ""
            
            # Build concentration display based on parameters with magenta color
            conc_display = ""
            if show_numbers and show_bars:
                conc_display = f"| [magenta]C:{concentration_count}/{concentration_limit}[/]{conc_bar} "
            elif show_numbers:
                conc_display = f"| [magenta]C:{concentration_count}/{concentration_limit}[/] "
            elif show_bars:
                conc_display = f"| [magenta]C:[/]{conc_bar} "
            else:
                # Default to showing numbers if neither is specified
                conc_display = f"| [magenta]C:{concentration_count}/{concentration_limit}[/] "
            status += conc_display

        # Handle effects more intelligently
        if effects_list:
            if show_all_effects or len(effects_list) <= 3:
                # Show all effects if requested or 3 or fewer
                status += f"| {' '.join(effects_list)}"
            else:
                # Show first 2 effects + count of remaining
                remaining_count = len(effects_list) - 2
                status += f"| {' '.join(effects_list[:2])} [dim]+{remaining_count} more[/]"
        
        return status

    def get_detailed_effects(self) -> str:
        """Get a detailed multi-line view of all active effects."""
        if not self.effect_manager.active_effects:
            return "No active effects"
        
        effects_info = []
        for e in self.effect_manager.active_effects:
            color = get_effect_color(e.effect)
            effects_info.append(f"  [{color}]{e.effect.name}[/] ({e.duration} turns): {e.effect.description}")
        
        return "Active Effects:\n" + "\n".join(effects_info)

    def to_dict(self) -> dict[str, Any]:
        """Converts the character to a dictionary representation."""
        data: dict[str, Any] = {}
        data["type"] = self.type.name
        data["name"] = self.name
        data["race"] = self.race.name
        data["levels"] = {cls.name: lvl for cls, lvl in self.levels.items()}
        data["stats"] = {
            "strength": self.stats["strength"],
            "dexterity": self.stats["dexterity"],
            "constitution": self.stats["constitution"],
            "intelligence": self.stats["intelligence"],
            "wisdom": self.stats["wisdom"],
            "charisma": self.stats["charisma"],
        }
        data["spellcasting_ability"] = self.spellcasting_ability
        data["total_hands"] = self.total_hands
        data["equipped_weapons"] = [weapon.name for weapon in self.equipped_weapons]
        data["equipped_armor"] = [armor.name for armor in self.equipped_armor]
        data["actions"] = list(self.actions.keys())
        data["spells"] = list(self.spells.keys())
        data["resistances"] = [res.name for res in self.resistances]
        data["vulnerabilities"] = [vuln.name for vuln in self.vulnerabilities]
        data["number_of_attacks"] = self.number_of_attacks
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Character | None":

        # Get the content repositories.
        repo = ContentRepository()
        # Get the type.
        char_type = CharacterType[data["type"].upper()]
        # Get the name.
        name = data["name"]
        # Get the race.
        race = repo.get_character_race(data["race"])
        assert race, f"Invalid race '{data['race']}' for character {name}."
        # Get the levels.
        levels: dict[CharacterClass, int] = {}
        for cls_name, cls_level in data["levels"].items():
            # Get the class from the class registry.
            cls = repo.get_character_class(cls_name)
            assert cls is not None, f"Invalid class '{cls_name}' for character {name}."
            assert (
                cls_level > 0
            ), f"Invalid class level '{cls_level}' for character {name}."
            # Add the class and its level to the levels dictionary.
            levels[cls] = cls_level
        # Get the stats.
        stats = data["stats"]
        # Get the spellcasting ability if present.
        spellcasting_ability = data.get("spellcasting_ability", None)
        # Get the total hands.
        total_hands = data.get("total_hands", 2)
        # Get the resistances.
        resistances = set()
        for res in data.get("resistances", []):
            resistances.add(DamageType[res.upper()])
        # Get the vulnerabilities.
        vulnerabilities = set()
        for vuln in data.get("vulnerabilities", []):
            vulnerabilities.add(DamageType[vuln.upper()])
        # Get the number of attacks.
        number_of_attacks = data.get("number_of_attacks", 1)

        # Create the character instance.
        char = Character(
            char_type,
            name,
            race,
            levels,
            stats,
            spellcasting_ability,
            total_hands,
            resistances,
            vulnerabilities,
            number_of_attacks,
        )

        # Get the list of equipped weapons.
        for weapon_name in data.get("equipped_weapons", []):
            weapon = repo.get_weapon(weapon_name)
            if weapon is None:
                warning(f"Invalid weapon '{weapon_name}' for character {data['name']}.")
                continue
            char.add_weapon(weapon)

        # Get the list of natural weapons.
        for weapon_name in data.get("natural_weapons", []):
            weapon = repo.get_weapon(weapon_name)
            if weapon is None:
                warning(
                    f"Invalid natural weapon '{weapon_name}' for character {data['name']}."
                )
                continue
            char.natural_weapons.append(weapon)

        # Get the list of equipped armor.
        for armor_name in data.get("equipped_armor", []):
            armor = repo.get_armor(armor_name)
            if armor is None:
                warning(f"Invalid armor '{armor_name}' for character {data['name']}.")
                continue
            char.add_armor(armor)

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

        # Load passive effects (like boss phase triggers).
        for effect_data in data.get("passive_effects", []):
            try:
                effect = Effect.from_dict(effect_data)
                char.passive_effects.append(effect)
            except Exception as e:
                warning(f"Invalid passive effect for character {data['name']}: {e}")
                continue

        return char


def load_character(file_path: Path) -> Character | None:
    """
    Loads a character from a JSON file.

    Args:
        file_path (str): The path to the JSON file containing character data.

    Returns:
        Character | None: A Character instance if the file is valid, None otherwise.
    """
    try:
        with open(file_path, "r") as f:
            character_data = json.load(f)
            return Character.from_dict(character_data)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        warning(f"Failed to load character from {file_path}: {e}")
        return None


def load_characters(file_path: Path) -> dict[str, Character]:
    """Loads characters from a JSON file.

    Args:
        file_path (Path): The path to the JSON file containing character data.

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
