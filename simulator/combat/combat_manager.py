# combat_manager.py
import random
from collections import deque
from logging import debug

from actions.abilities import (
    AbilityBuff,
    AbilityDebuff,
    AbilityHeal,
    AbilityOffensive,
)
from actions.attacks import BaseAttack, WeaponAttack
from actions.base_action import BaseAction
from actions.spells import Spell, SpellBuff, SpellDebuff, SpellHeal, SpellOffensive
from character import Character
from combat.npc_ai import (
    choose_best_attack_spell_action,
    choose_best_base_attack_action,
    choose_best_buff_ability_action,
    choose_best_buff_spell_action,
    choose_best_debuff_ability_action,
    choose_best_debuff_spell_action,
    choose_best_healing_ability_action,
    choose_best_healing_spell_action,
    choose_best_offensive_ability_action,
    choose_best_target_for_weapon,
    choose_best_weapon_for_situation,
    get_actions_by_type,
    get_natural_attacks,
)
from core.constants import ActionCategory, ActionType, CharacterType, is_oponent
from core.utils import cprint, crule
from ui.cli_interface import PlayerInterface

FULL_ATTACK = BaseAction(
    name="Full Attack",
    action_type=ActionType.STANDARD,
    category=ActionCategory.OFFENSIVE,
    description="Perform a full attack with all available attacks.",
)


class CombatManager:
    """Manages the flow of combat, including turn order, actions, and combat phases.

    This class handles the initialization, execution, and conclusion of combat
    encounters. It manages participants, turn order, and the logic for both
    player and NPC actions. Additionally, it provides methods for pre-combat
    preparation, post-combat healing, and final battle reporting.
    """

    def __init__(
        self,
        player: Character,
        enemies: list[Character],
        friendlies: list[Character],
    ):
        """Initialize the CombatManager with participants and turn order.

        Args:
            player (Character): The player character controlled by the user.
            enemies (list[Character]): List of enemy characters.
            friendlies (list[Character]): List of friendly characters.

        """
        # Store the ui.
        self.ui: PlayerInterface = PlayerInterface()

        # The player character, who is controlled by the user.
        self.player: Character = player

        # Combine all participants for the deque, ensuring player is handled specifically
        self.participants: deque[Character] = deque([player] + enemies + friendlies)

        # Stores the initiative of each participant.
        self.initiatives: dict[Character, int] = {
            participant: random.randint(1, 20) + participant.INITIATIVE
            for participant in self.participants
        }

        # This will now represent the "Round Number"
        self.turn_number: int = 0

    def initialize(self) -> None:
        """Initializes the combat by sorting participants by initiative."""
        # Ensure each character has an 'initiative' attribute (e.g., random.randint(1, 20) + char.DEX)
        # before calling initialize if not already done.
        self.participants = deque(
            sorted(
                self.participants,
                key=lambda c: self.initiatives[c],
                reverse=True,
            )
        )
        cprint("[bold green]Combat initialized![/]")
        cprint("[bold yellow]Turn Order:[/]")
        for participant in self.participants:
            # Use bars only for turn order display to keep it compact
            # Show AC for player and allies, hide for enemies
            show_ac = participant.char_type != CharacterType.ENEMY
            status_line = participant.get_status_line(show_bars=True, show_ac=show_ac)
            cprint(f"    🎲 {self.initiatives[participant]:3}  {status_line}")

    def get_alive_participants(self) -> list[Character]:
        """Returns a list of all participants (player, enemies, friendlies) who are still alive.

        Returns:
            list[Character]: A list of alive characters.

        """
        return [char for char in self.participants if char.is_alive()]

    def get_alive_opponents(self, actor: Character) -> list[Character]:
        """Returns a list of opponents for the actor, who are still alive.

        Args:
            actor (Character): The character for whom to find opponents.

        Returns:
            list[Character]: A list of alive opponents.

        """
        return [
            char
            for char in self.get_alive_participants()
            if is_oponent(actor.char_type, char.char_type)
        ]

    def get_alive_friendlies(self, actor: Character) -> list[Character]:
        """Returns a list of friendly characters for the actor, who are still alive.

        Args:
            actor (Character): The character for whom to find friendlies.

        Returns:
            list[Character]: A list of alive friendly characters.

        """
        return [
            char
            for char in self.get_alive_participants()
            if not is_oponent(actor.char_type, char.char_type)
        ]

    def run_turn(self) -> bool:
        """Runs a single turn within the combat round.

        Returns:
            bool: True if the turn was successfully executed, False if combat should end.

        """
        alive_participants = deque(self.get_alive_participants())

        # If there are no more participants alive, combat ends.
        if not alive_participants:
            debug("No participants left in combat. Combat ends.")
            return False

        # If there are no more enemies alive, combat ends.
        if not self.get_alive_opponents(self.player):
            debug("All enemies defeated! Combat ends.")
            return False

        # Print the status of the player at the turn's end.
        crule(f"⏱ Start of Turn {self.turn_number}", style="cyan")

        # Keep dequeuing participants until we find one that can act.
        while alive_participants:
            # Pop the next participant in the turn order.
            participant = alive_participants.popleft()

            # Run the participant's turn.
            self.run_participant_turn(participant)

        # Increment the turn number after all participants have acted.
        self.turn_number += 1

        return True

    def run_participant_turn(self, participant: Character):
        """Runs a single participant's turn in combat.

        Args:
            participant (Character): The participant whose turn is being run.

        """
        if participant.is_alive():
            # Reset the participant's turn flags to allow for new actions.
            participant.reset_turn_flags()

            # Print the participant's status line with appropriate display mode
            if participant == self.player:
                # Player gets full display: numbers + bars + AC
                cprint(
                    participant.get_status_line(
                        show_numbers=True, show_bars=True, show_ac=True
                    )
                )
            else:
                # NPCs get bars only for cleaner display
                # Show AC for allies, hide for enemies
                show_ac = participant.char_type != CharacterType.ENEMY
                cprint(participant.get_status_line(show_bars=True, show_ac=show_ac))

            # Check if character is incapacitated
            if participant.is_incapacitated():
                cprint(
                    f"    💤 {participant.name} is incapacitated and cannot act this turn."
                )
            # Execute the participant's action based on whether they are the player or an NPC.
            elif participant == self.player:
                self.ask_for_player_action()
            else:
                self.execute_npc_action(participant)

            # Apply end-of-turn updates and check for expiration
            participant.turn_update()

            cprint("")

    def ask_for_player_action(self) -> None:
        """Handles player input for choosing an action and target during their turn."""
        if not self.get_alive_opponents(self.player):
            return

        while not self.player.turn_done():
            # Gather available actions and attacks.
            actions = []
            if self.player.has_action_type(ActionType.STANDARD):
                actions.append(FULL_ATTACK)
            actions.extend(self.player.get_available_actions())
            spells = self.player.get_available_spells()

            # Main action selection menu.
            submenus = []
            if spells:
                submenus.append("Cast a Spell")

            # Player selects an action or submenu option.
            choice = self.ui.choose_action(actions, submenus, "Skip")
            if choice is None or (isinstance(choice, str) and choice == "q"):
                break
            # If the action is a Spell, we need to handle it differently.
            if choice == FULL_ATTACK:
                self.ask_for_player_full_attack()
            elif choice == "Cast a Spell":
                self.ask_for_player_spell_cast(spells)

    def ask_for_player_full_attack(self) -> None:
        """Asks the player to choose targets for a full attack action."""
        # Get the list of all attacks available in the full attack.
        attacks = self.player.get_available_attacks()
        if not attacks:
            print(
                "No available attacks for the full attack action",
                {"player": self.player.name, "context": "full_attack_selection"},
            )
            return

        # Choose the attack type to use for all attacks in the sequence
        attack = self.ui.choose_action(attacks)
        if attack is None or not isinstance(attack, BaseAttack):
            print(
                "Invalid attack selected. Ending full attack",
                {
                    "player": self.player.name,
                    "selected_attack": str(attack),
                    "context": "full_attack_selection",
                },
            )
            return

        # Get the legal targets for the action.
        valid_targets = self._get_legal_targets(self.player, attack)
        if not valid_targets:
            print(
                f"No valid targets for {attack.name}",
                {
                    "player": self.player.name,
                    "attack": attack.name,
                    "context": "full_attack_target_selection",
                },
            )
            return

        # Choose the initial target
        target = self.ui.choose_target(valid_targets, [])
        if not isinstance(target, Character):
            return

        # Execute the full attack sequence using the same attack type
        attacks_made = 0
        for attack_num in range(self.player.number_of_attacks):
            # Check if there are still valid opponents
            if not self.get_alive_opponents(self.player):
                break

            # If the current target is dead, ask for a new target
            current_target = target
            if not target.is_alive():
                remaining_targets = self._get_legal_targets(self.player, attack)
                if not remaining_targets:
                    break
                current_target = self.ui.choose_target(
                    remaining_targets, [], f"Attack {attack_num + 1} target"
                )
                if not isinstance(current_target, Character):
                    break
                target = current_target

            # Perform the attack
            attack.execute(self.player, current_target)
            attacks_made += 1

            # Add cooldown only once for the attack type
            if attack_num == 0:
                self.player.add_cooldown(attack)

        # Mark the action type as used.
        self.player.use_action_type(ActionType.STANDARD)

    def ask_for_player_spell_cast(self, spells: list[Spell]) -> bool:
        """Handles the player's choice to cast a spell.

        Args:
            spells (list[Spell]): List of available spells for the player.

        Returns:
            bool: True if a spell was successfully cast, False otherwise.

        """
        while True:
            # Ask for the spell and the mind level.
            choice = self.ask_for_player_spell_and_mind(spells)
            if choice is None:
                break
            if isinstance(choice, str):
                if choice == "q":
                    break
                continue
            # Unpack the spell and mind level.
            spell, mind_level = choice
            while True:
                # Get the targets for the spell.
                targets = self.ask_for_player_targets(
                    spell, spell.target_count(self.player, mind_level)
                )
                if not targets:
                    print(
                        f"No valid targets for {spell.name}",
                        {
                            "player": self.player.name,
                            "spell": spell.name,
                            "context": "spell_target_selection",
                        },
                    )
                    break
                if isinstance(targets, str):
                    if targets == "q":
                        break
                    continue
                if not all(isinstance(t, Character) for t in targets):
                    continue
                for target in targets:
                    # Perform the action on the target.
                    spell.cast_spell(self.player, target, mind_level)
                # Remove the MIND cost from the player.
                self.player.mind -= mind_level
                # Mark the action type as used.
                self.player.use_action_type(spell.action_type)
                # Add the spell to the cooldowns if it has one.
                self.player.add_cooldown(spell)
                return True
        return False

    def ask_for_player_spell_and_mind(
        self, spells: list[Spell]
    ) -> tuple[Spell, int] | str | None:
        """Asks the player to choose a spell from their available spells.

        Args:
            spells (list[Spell]): List of available spells for the player.

        Returns:
            Optional[tuple[Spell, int] | str]: The chosen spell and mind level, or None if no spell was selected.

        """
        while True:
            # Let the player choose a spell.
            spell = self.ui.choose_spell(spells)
            if spell is None:
                break
            if isinstance(spell, str):
                if spell == "q":
                    return spell
                continue
            # Ask for the [MIND] level to use for the spell.
            mind = self.ui.choose_mind(self.player, spell)
            if mind == -1:
                return "q"
            return spell, mind
        return None

    def ask_for_player_target(self, action: BaseAction) -> Character | str | None:
        """Asks the player to choose a target for the given action.

        Args:
            action (BaseAction): The action for which to choose a target.

        Returns:
            Optional[Character | str]: The chosen target, or None if no valid target was selected.

        """
        # Get the legal targets for the action.
        valid_targets = self._get_legal_targets(self.player, action)
        if not valid_targets:
            print(
                f"No valid targets for {action.name}",
                {
                    "player": self.player.name,
                    "action": action.name,
                    "context": "single_target_selection",
                },
            )
            return None
        # Ask the player to choose a target.
        return self.ui.choose_target(valid_targets)

    def ask_for_player_targets(
        self, action: BaseAction, max_targets: int
    ) -> list[Character] | str | None:
        """Asks the player to choose multiple targets for the given action.

        Args:
            action (BaseAction): The action for which to choose targets.
            max_targets (int): The maximum number of targets to choose.

        Returns:
            Optional[list[Character] | str]: The chosen targets, or None if no valid targets were selected.

        """
        # Get the legal targets for the action.
        valid_targets = self._get_legal_targets(self.player, action)
        if len(valid_targets) == 0:
            print(
                f"No valid targets for {action.name}",
                {
                    "player": self.player.name,
                    "action": action.name,
                    "context": "multi_target_selection",
                },
            )
            return None
        if max_targets <= 0:
            print(
                f"Invalid maximum number of targets: {max_targets}",
                {
                    "player": self.player.name,
                    "action": action.name,
                    "max_targets": max_targets,
                    "context": "target_validation",
                },
            )
            return None
        if max_targets == 1 or len(valid_targets) == 1:
            target = self.ask_for_player_target(action)
            if target is None:
                print(
                    f"No valid target for {action.name}",
                    {
                        "player": self.player.name,
                        "action": action.name,
                        "context": "single_target_fallback",
                    },
                )
                return None
            if isinstance(target, str):
                return target
            return [target]
        # Ask the player to choose multiple targets.
        return self.ui.choose_targets(valid_targets, max_targets)

    def execute_npc_action(self, npc: Character):
        """Executes the action logic for an NPC during their turn.

        Args:
            npc (Character): The NPC whose action is being executed.

        """
        allies = self.get_alive_friendlies(npc)
        enemies = self.get_alive_opponents(npc)

        if not enemies:
            print(
                f"SKIP: {npc.name} has no enemies to attack",
                {
                    "npc": npc.name,
                    "allies_count": len(allies),
                    "context": "npc_ai_decision",
                },
            )
            return

        # Check for healing spells.
        spell_heals: list[SpellHeal] = get_actions_by_type(npc, SpellHeal)
        if spell_heals:
            result = choose_best_healing_spell_action(npc, allies, spell_heals)
            if result:
                spell, mind_level, targets = result
                # Cast the healing spell on the targets.
                for t in targets:
                    spell.cast_spell(npc, t, mind_level)
                # Add the spell to the cooldowns if it has one.
                npc.add_cooldown(spell)
                # Mark the action type as used.
                npc.use_action_type(spell.action_type)
                # Remove the MIND cost from the NPC.
                npc.mind -= mind_level

        # Check for healing abilities.
        healing_abilities: list[AbilityHeal] = get_actions_by_type(
            npc, AbilityHeal
        )
        if healing_abilities:
            result = choose_best_healing_ability_action(npc, allies, healing_abilities)
            if result:
                ability, targets = result
                # Use the healing ability on the targets.
                for t in targets:
                    ability.execute(npc, t)
                # Add the ability to the cooldowns if it has one.
                npc.add_cooldown(ability)
                # Mark the action type as used.
                npc.use_action_type(ability.action_type)

        # Check for buff spells.
        spell_buffs: list[SpellBuff] = get_actions_by_type(npc, SpellBuff)
        if spell_buffs:
            result = choose_best_buff_spell_action(npc, allies, spell_buffs)
            if result:
                spell, mind_level, targets = result
                # Cast the buff spell on the targets.
                for t in targets:
                    spell.cast_spell(npc, t, mind_level)
                # Add the spell to the cooldowns if it has one.
                npc.add_cooldown(spell)
                # Mark the action type as used.
                npc.use_action_type(spell.action_type)
                # Remove the MIND cost from the NPC.
                npc.mind -= mind_level

        # Check for buff abilities.
        buff_abilities: list[AbilityBuff] = get_actions_by_type(npc, AbilityBuff)
        if buff_abilities:
            result = choose_best_buff_ability_action(npc, allies, buff_abilities)
            if result:
                ability, targets = result
                # Use the buff ability on the targets.
                for t in targets:
                    ability.execute(npc, t)
                # Add the ability to the cooldowns if it has one.
                npc.add_cooldown(ability)
                # Mark the action type as used.
                npc.use_action_type(ability.action_type)

        # Check for debuff spells.
        spell_debuffs: list[SpellDebuff] = get_actions_by_type(npc, SpellDebuff)
        if spell_debuffs:
            result = choose_best_debuff_spell_action(npc, enemies, spell_debuffs)
            if result:
                spell, mind_level, targets = result
                # Cast the debuff spell on the targets.
                for t in targets:
                    spell.cast_spell(npc, t, mind_level)
                # Add the spell to the cooldowns if it has one.
                npc.add_cooldown(spell)
                # Mark the action type as used.
                npc.use_action_type(spell.action_type)
                # Remove the MIND cost from the NPC.
                npc.mind -= mind_level

        # Check for debuff abilities.
        debuff_abilities: list[AbilityDebuff] = get_actions_by_type(npc, AbilityDebuff)
        if debuff_abilities:
            result = choose_best_debuff_ability_action(npc, enemies, debuff_abilities)
            if result:
                ability, targets = result
                # Use the debuff ability on the targets.
                for t in targets:
                    ability.execute(npc, t)
                # Add the ability to the cooldowns if it has one.
                npc.add_cooldown(ability)
                # Mark the action type as used.
                npc.use_action_type(ability.action_type)

        # Check for attack spells.
        spell_attacks: list[SpellOffensive] = get_actions_by_type(npc, SpellOffensive)
        if spell_attacks:
            result = choose_best_attack_spell_action(npc, enemies, spell_attacks)
            if result:
                spell, mind_level, targets = result
                # Cast the attack spell on the targets.
                for target in targets:
                    spell.cast_spell(npc, target, mind_level)
                # Add the spell to the cooldowns if it has one.
                npc.add_cooldown(spell)
                # Mark the action type as used.
                npc.use_action_type(spell.action_type)
                # Remove the MIND cost from the NPC.
                npc.mind -= mind_level

        # Check for offensive abilities.
        offensive_abilities: list[AbilityOffensive] = get_actions_by_type(
            npc, AbilityOffensive
        )
        if offensive_abilities:
            result = choose_best_offensive_ability_action(
                npc, enemies, offensive_abilities
            )
            if result:
                ability, targets = result
                # Use the offensive ability on the targets.
                for target in targets:
                    ability.execute(npc, target)
                # Add the ability to the cooldowns if it has one.
                npc.add_cooldown(ability)
                # Mark the action type as used.
                npc.use_action_type(ability.action_type)

        # Check for base attacks.
        weapon_attacks: list[WeaponAttack] = get_actions_by_type(npc, WeaponAttack)
        used_weapon_attack: bool = False
        if weapon_attacks:
            # Choose the best weapon type once for the full attack sequence
            best_weapon = choose_best_weapon_for_situation(npc, weapon_attacks, enemies)
            if best_weapon:
                # Get initial target for this weapon
                current_target = choose_best_target_for_weapon(
                    npc, best_weapon, enemies
                )

                # Perform multiple attacks with the same weapon type
                for attack_num in range(npc.number_of_attacks):
                    # If current target is dead, find a new one
                    if not current_target or not current_target.is_alive():
                        current_target = choose_best_target_for_weapon(
                            npc, best_weapon, enemies
                        )
                        if not current_target:
                            # No more valid targets
                            break

                    # Perform the attack
                    best_weapon.execute(npc, current_target)
                    used_weapon_attack = True

                # Add cooldown and mark action type only once after all attacks
                if used_weapon_attack:
                    npc.add_cooldown(best_weapon)
                    npc.use_action_type(best_weapon.action_type)

        # Check for natural attacks.
        if not used_weapon_attack:
            # Natural attacks are designed as a sequence - perform each different attack once
            for attack in get_natural_attacks(npc):
                result = choose_best_base_attack_action(npc, enemies, [attack])
                if result:
                    _, target = result
                    # Perform the natural attack on the target.
                    attack.execute(npc, target)
                    # Add the attack to the cooldowns if it has one.
                    npc.add_cooldown(attack)
                    # Mark the action type as used.
                    npc.use_action_type(attack.action_type)

    def _get_legal_targets(
        self, character: Character, ability: BaseAction
    ) -> list[Character]:
        """Retrieves a list of legal targets for the given character and ability.

        Args:
            character (Character): The character performing the action or spell.
            ability (BaseAction): The action or spell being performed.

        Returns:
            list[Character]: A list of legal targets for the action or spell.

        """
        return [
            participant
            for participant in self.participants
            if ability.is_valid_target(character, participant)
        ]

    def pre_combat_phase(self) -> None:
        """Handles the pre-combat phase where the player can prepare for combat."""
        crule(":hourglass_done: Pre-Combat Phase", style="blue")
        # Gather viable healing spells.
        buffs: list[Spell] = [
            s for s in self.player.spells.values() if isinstance(s, SpellBuff)
        ]
        heals: list[Spell] = (
            [s for s in self.player.spells.values() if isinstance(s, SpellHeal)]
            if any(t.hp < t.HP_MAX for t in self.get_alive_friendlies(self.player))
            else []
        )
        # If the player has no spells, skip this phase.
        if not heals and not buffs:
            cprint(
                "[yellow]No healing or buff spells known. Skipping pre-combat phase.[/]"
            )
            return
        # Otherwise, allow to perform healing actions.
        while True:
            if not self.ask_for_player_spell_cast(buffs + heals):
                break

    def post_combat_phase(self) -> None:
        """Handles the post-combat phase where the player can heal friendly characters."""
        crule(":hourglass_done: Post-Combat Healing", style="green")
        # Stop now if there are no friendly character that needs healing.
        if not any(t.hp < t.HP_MAX for t in self.get_alive_friendlies(self.player)):
            cprint("[yellow]No friendly characters to heal.[/]")
            return
        # Gather viable healing spells.
        heals: list[Spell] = [
            s for s in self.player.spells.values() if isinstance(s, SpellHeal)
        ]
        if not heals:
            cprint("[yellow]No healing spells known.[/]")
            return
        # Otherwise, allow to perform healing actions.
        while True:
            for ally in self.get_alive_friendlies(self.player):
                # Show full details for healing phase (allies show AC)
                cprint(
                    ally.get_status_line(
                        show_numbers=True, show_bars=True, show_ac=True
                    )
                )
            if not any(t.hp < t.HP_MAX for t in self.get_alive_friendlies(self.player)):
                cprint("[yellow]No friendly characters needs more healing.[/]")
                return
            # let the UI list ONLY those spells plus an 'End' sentinel.
            if not self.ask_for_player_spell_cast(heals):
                break

    def final_report(self) -> None:
        """Generates the final battle report after combat ends."""
        crule("📊  Final Battle Report", style="bold blue")
        # Player gets full display in final report
        cprint(
            self.player.get_status_line(show_numbers=True, show_bars=True, show_ac=True)
        )
        # Allies get full display too in final report
        for ally in self.get_alive_friendlies(self.player):
            if ally != self.player:
                cprint(
                    ally.get_status_line(
                        show_numbers=True, show_bars=True, show_ac=True
                    )
                )
        # Fallen foes
        defeated = [
            c
            for c in self.participants
            if not c.is_alive() and c.char_type == CharacterType.ENEMY
        ]
        if defeated:
            cprint(
                f"[bold magenta]Defeated Enemies ({len(defeated)}):[/] "
                + ", ".join(d.name for d in defeated)
            )
        cprint("")  # blank line

    def is_combat_over(self) -> bool:
        """Determines if combat has ended.

        Returns:
            bool: True if combat has ended, False otherwise.

        """
        if not self.player.is_alive():
            cprint("[bold red]Combat ends. You have been defeated![/]")
            return True
        if not self.get_alive_opponents(self.player):
            cprint(
                "[bold green]Combat ends. All enemies defeated! You are victorious![/]"
            )
            return True
        return False
