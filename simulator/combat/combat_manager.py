# combat_manager.py
from collections import deque
from logging import debug, warning
import random
from typing import Tuple

from rich.console import Console
from rich.rule import Rule

from actions.base_action import *
from actions.attack_action import *
from actions.spell_action import *
from core.constants import *
from ui.cli_interface import *
from combat.npc_ai import *

console = Console()


class CombatManager:
    def __init__(
        self,
        player: Character,
        enemies: list[Character],
        friendlies: list[Character],
    ):
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
        console.print("[bold green]Combat initialized![/]")
        console.print("[bold yellow]Turn Order:[/]")
        for participant in self.participants:
            console.print(
                f"    🎲 {self.initiatives[participant]:3}  {participant.get_status_line()}",
                markup=True,
            )

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
            if is_oponent(actor.type, char.type)
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
            if not is_oponent(actor.type, char.type)
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
        console.print(Rule(title=f"⏱ Start of Turn {self.turn_number}", style="cyan"))

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

            # Print the participant's status line.
            console.print(participant.get_status_line(), markup=True)

            # Execute the participant's action based on whether they are the player or an NPC.
            if participant == self.player:
                self.ask_for_player_action()
            else:
                self.execute_npc_action(participant)

            # Apply end-of-turn updates and check for expiration
            participant.turn_update()

            console.print("")

    def ask_for_player_action(self) -> None:
        """
        Handles player input for choosing an action and target during their turn.
        """
        if not self.get_alive_opponents(self.player):
            return

        while not self.player.turn_done():
            # Gather available actions and attacks
            attacks = self.player.get_available_attacks()
            actions = self.player.get_available_actions()
            spells = self.player.get_available_spells()

            # Main action selection menu.
            submenus = []
            if spells:
                submenus.append("Cast a Spell")

            # Player selects an action or submenu option.
            choice = self.ui.choose_action(attacks + actions, submenus)
            if choice is None or isinstance(choice, str) and choice == "Skip":
                break
            # If the action is a Spell, we need to handle it differently.
            if isinstance(choice, BaseAttack):
                self.ask_for_player_full_attack(choice)
            elif choice == "Cast a Spell":
                self.ask_for_player_spell_cast(spells)

    def ask_for_player_full_attack(self, attack: BaseAttack) -> None:
        """Asks the player to choose targets for a full attack action."""
        attacks_used: int = 0
        # Get the list of all attacks available in the full attack.
        attacks = self.player.get_available_attacks()
        # Iterate through each attack in the full attack.
        while attacks_used < self.player.number_of_attacks:
            # Get the legal targets for the action.
            valid_targets = self._get_legal_targets(self.player, attack)
            if not valid_targets:
                warning(f"No valid targets for {attack.name}.")
                continue
            # Ask the player to choose a target.
            target = self.ui.choose_target(valid_targets, show_back=attacks_used == 0)
            # If the player chose to go back, we stop asking for targets.
            if isinstance(target, str) and target == "Back":
                return
            # If the target is not valid, skip this attack.
            if not isinstance(target, Character):
                continue
            # If this is the first attack, we allow to cancel the action.
            attacks_used += 1
            # Perform the attack on the target.
            attack.execute(self.player, target)
        # Mark the action type as used.
        self.player.use_action_type(ActionType.STANDARD)

    def ask_for_player_spell_cast(self, spells: list[Spell]) -> bool:
        while True:
            # Ask for the spell and the mind level.
            choice = self.ask_for_player_spell_and_mind(spells)
            if choice is None:
                break
            if isinstance(choice, str):
                if choice == "Back":
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
                    warning(f"No valid targets for {spell.name}.")
                    break
                if isinstance(targets, str):
                    if targets == "Back":
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
                self.player.use_action_type(spell.type)
                # Add the spell to the cooldowns if it has one.
                self.player.add_cooldown(spell, spell.cooldown)
                return True
        return False

    def ask_for_player_spell_and_mind(
        self, spells: list[Spell]
    ) -> Optional[tuple[Spell, int] | str]:
        """Asks the player to choose a spell from their available spells.

        Returns:
            Optional[tuple[Spell, int]]: The chosen spell and mind level, or None if no spell was selected.
        """
        while True:
            # Let the player choose a spell.
            spell = self.ui.choose_spell(spells)
            if spell is None:
                break
            if isinstance(spell, str):
                if spell == "Back":
                    return "Back"
                continue
            # Ask for the [MIND] level to use for the spell.
            mind = self.ui.choose_mind(self.player, spell)
            return spell, mind
        return None

    def ask_for_player_target(self, action: BaseAction) -> Optional[Character | str]:
        """Asks the player to choose a target for the given action.

        Args:
            action (BaseAction): The action for which to choose a target.

        Returns:
            Optional[Character]: The chosen target, or None if no valid target was selected.
        """
        # Get the legal targets for the action.
        valid_targets = self._get_legal_targets(self.player, action)
        if not valid_targets:
            warning(f"No valid targets for {action.name}.")
            return None
        # Ask the player to choose a target.
        return self.ui.choose_target(valid_targets)

    def ask_for_player_targets(
        self, action: BaseAction, max_targets: int
    ) -> Optional[List[Character] | str]:
        """Asks the player to choose multiple targets for the given action.

        Args:
            action (BaseAction): The action for which to choose targets.
            max_targets (int): The maximum number of targets to choose.

        Returns:
            Optional[list[Character]]: The chosen targets, or None if no valid targets were selected.
        """
        # Get the legal targets for the action.
        valid_targets = self._get_legal_targets(self.player, action)
        if len(valid_targets) == 0:
            warning(f"No valid targets for {action.name}.")
            return None
        if max_targets <= 0:
            warning(f"Invalid maximum number of targets: {max_targets}.")
            return None
        if max_targets == 1 or len(valid_targets) == 1:
            target = self.ask_for_player_target(action)
            if target is None:
                warning(f"No valid target for {action.name}.")
                return None
            if isinstance(target, str):
                return target
            return [target]
        # Ask the player to choose multiple targets.
        return self.ui.choose_targets(valid_targets, max_targets)

    def execute_npc_action(self, npc: Character):
        """
        General AI logic for any NPC, whether enemy or friendly:
        - Heal low HP allies (including self)
        - Buff self if not already buffed
        - Attack enemies
        """
        allies = self.get_alive_friendlies(npc)
        enemies = self.get_alive_opponents(npc)

        if not enemies:
            warning(f"SKIP: {npc.name} has no enemies to attack.")
            return

        # Get all actions available to the NPC.
        actions: list[BaseAction] = get_all_combat_actions(npc)
        # Get all actions by cathegory.
        base_attacks: list[BaseAttack] = get_base_attacks(actions)
        spell_attacks: list[SpellAttack] = get_spell_attacks(actions)
        spell_heals: list[SpellHeal] = get_spell_heals(actions)
        spell_buffs: list[SpellBuff] = get_spell_buffs(actions)
        spell_debuffs: list[SpellDebuff] = get_spell_debuffs(actions)

        if spell_heals:
            result = choose_best_healing_spell_action(npc, allies, spell_heals)
            if result:
                spell, mind_level, targets = result
                # Cast the healing spell on the targets.
                for t in targets:
                    spell.cast_spell(npc, t, mind_level)
                # Add the spell to the cooldowns if it has one.
                self.player.add_cooldown(spell, spell.cooldown)
                # Remove the MIND cost from the NPC.
                npc.mind -= mind_level
                return
        if spell_buffs:
            result = choose_best_buff_spell_action(npc, allies, spell_buffs)
            if result:
                spell, mind_level, targets = result
                # Cast the buff spell on the targets.
                for t in targets:
                    spell.cast_spell(npc, t, mind_level)
                # Add the spell to the cooldowns if it has one.
                self.player.add_cooldown(spell, spell.cooldown)
                # Remove the MIND cost from the NPC.
                npc.mind -= mind_level
                return
        if spell_debuffs:
            result = choose_best_debuff_spell_action(npc, enemies, spell_debuffs)
            if result:
                spell, mind_level, targets = result
                # Cast the debuff spell on the targets.
                for t in targets:
                    spell.cast_spell(npc, t, mind_level)
                # Add the spell to the cooldowns if it has one.
                self.player.add_cooldown(spell, spell.cooldown)
                # Remove the MIND cost from the NPC.
                npc.mind -= mind_level
                return
        if spell_attacks:
            result = choose_best_attack_spell_action(npc, enemies, spell_attacks)
            if result:
                spell, mind_level, targets = result
                # Cast the attack spell on the targets.
                for target in targets:
                    spell.cast_spell(npc, target, mind_level)
                # Add the spell to the cooldowns if it has one.
                self.player.add_cooldown(spell, spell.cooldown)
                # Remove the MIND cost from the NPC.
                npc.mind -= mind_level
                return
        if base_attacks:
            result = choose_best_base_attack_action(npc, enemies, base_attacks)
            if result:
                attack, target = result
                # Perform the attack on the target.
                attack.execute(npc, target)
                return

        warning(f"SKIP: {npc.name} has no usable action or valid targets.")

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
        console.print(Rule(":hourglass_done: Pre-Combat Phase", style="blue"))
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
            console.print(
                "[yellow]No healing or buff spells known. Skipping pre-combat phase.[/]"
            )
            return
        # Otherwise, allow to perform healing actions.
        while True:
            if not self.ask_for_player_spell_cast(buffs + heals):
                break

    def post_combat_phase(self) -> None:
        """Handles the post-combat phase where the player can heal friendly characters."""
        console.print(Rule(":hourglass_done: Post-Combat Healing", style="green"))
        # Stop now if there are no friendly character that needs healing.
        if not any(t.hp < t.HP_MAX for t in self.get_alive_friendlies(self.player)):
            console.print("[yellow]No friendly characters to heal.[/]")
            return
        # Gather viable healing spells.
        heals: list[Spell] = [
            s for s in self.player.spells.values() if isinstance(s, SpellHeal)
        ]
        if not heals:
            console.print("[yellow]No healing spells known.[/]")
            return
        # Otherwise, allow to perform healing actions.
        while True:
            for ally in self.get_alive_friendlies(self.player):
                console.print(ally.get_status_line(), markup=True)
            if not any(t.hp < t.HP_MAX for t in self.get_alive_friendlies(self.player)):
                console.print("[yellow]No friendly characters needs more healing.[/]")
                return
            # let the UI list ONLY those spells plus an 'End' sentinel.
            if not self.ask_for_player_spell_cast(heals):
                break

    def final_report(self) -> None:
        console.print(Rule("📊  Final Battle Report", style="bold blue"))
        # Player
        console.print(self.player.get_status_line(), markup=True)
        # Allies
        for ally in self.get_alive_friendlies(self.player):
            if ally != self.player:
                console.print(ally.get_status_line(), markup=True)
        # Fallen foes
        defeated = [
            c
            for c in self.participants
            if not c.is_alive() and c.type == CharacterType.ENEMY
        ]
        if defeated:
            console.print(
                f"[bold magenta]Defeated Enemies ({len(defeated)}):[/] "
                + ", ".join(d.name for d in defeated)
            )
        console.print("")  # blank line

    def is_combat_over(self) -> bool:
        """
        Determines if combat has ended.
        Combat ends if the player is defeated, or all enemies are defeated.
        """
        if not self.player.is_alive():
            console.print("[bold red]Combat ends. You have been defeated![/]")
            return True
        if not self.get_alive_opponents(self.player):
            console.print(
                "[bold green]Combat ends. All enemies defeated! You are victorious![/]"
            )
            return True
        return False
