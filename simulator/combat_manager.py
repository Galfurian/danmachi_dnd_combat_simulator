# combat_manager.py
from collections import deque
from logging import debug, warning
import random
from typing import Tuple

from rich.console import Console
from rich.rule import Rule

from actions.base_action import BaseAction
from actions.attack_action import FullAttack
from actions.spell_action import Spell, SpellAttack, SpellHeal, SpellBuff, SpellDebuff
from character import *
from effect import *
from constants import *
from interfaces import *
from npc_ai import *

console = Console()


class CombatManager:
    def __init__(
        self,
        ui: PlayerInterface,
        player: Character,
        enemies: list[Character],
        friendlies: list[Character],
    ):
        # Store the ui.
        self.ui = ui

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

        # Call the new initialize method.
        self.initialize()

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

        action: Optional[MenuOption] = None

        while not self.player.turn_done():
            attacks = [ActionOption(a) for a in self.player.get_available_attacks()]
            actions = [ActionOption(a) for a in self.player.get_available_actions()]
            spells = [ActionOption(s) for s in self.player.get_available_spells()]
            cast_spell = SubmenuOption("Cast a Spell")
            skip_action = MenuOption("Skip Action")
            # Create the proper list of options for the UI.
            options: list[MenuOption] = actions + attacks
            if spells:
                options.append(cast_spell)
            options.append(skip_action)
            # Get the action.
            action = self.ui.choose_action(options)
            if not action:
                break
            # If the action is a Spell, we need to handle it differently.
            if action == cast_spell:
                # Create the back option.
                back_option = MenuOption("Back")

                # Choose a spell from the player's available spells.
                spell = self.ui.choose_spell(self.player, spells + [back_option])
                if spell is None:
                    continue

                # Get the legal targets for the attack.
                valid_targets = self._get_legal_targets(self.player, spell)
                # If there are no valid targets, skip this attack.
                if not valid_targets:
                    continue

                valid_targets = [TargetOption(t) for t in valid_targets]

                # Gather here the actual targets.
                targets = []

                mind_levels = [
                    MenuOption(f"{i} MIND") for i in range(1, self.player.mind + 1)
                ]

                # Ask for the [MIND] level to use for the spell.
                mind_level = self.ui.choose_mind(mind_levels + [back_option])
                if mind_level == -1:
                    continue

                # Get the number of targets for the spell.
                maximum_num_targets = spell.target_count(self.player, mind_level)
                # There is no point in asking for more targets than we have valid targets.
                maximum_num_targets = min(maximum_num_targets, len(valid_targets))
                # If the action accepts just one target, we can ask for a single target.
                if maximum_num_targets == 1:
                    # Ask for a single target.
                    targets = [self.ui.choose_target(valid_targets)]
                # If the action accepts multiple targets, we can ask for multiple targets.
                elif maximum_num_targets > 1:
                    # Ask for multiple targets.
                    targets = self.ui.choose_targets(valid_targets, maximum_num_targets)
                # Check if the targets are valid.
                if not isinstance(targets, list):
                    continue
                if not all(isinstance(t, Character) for t in targets):
                    continue
                for target in targets:
                    # Perform the action on the target.
                    spell.cast_spell(self.player, target, mind_level)
                # Remove the MIND cost from the player.
                self.player.mind -= mind_level.level
                # Mark the action type as used.
                self.player.use_action_type(spell.type)
            elif isinstance(action, FullAttack):
                for attack in action.attacks:
                    # Get the legal targets for the attack.
                    valid_targets = self._get_legal_targets(self.player, attack)
                    # If there are no valid targets, skip this attack.
                    if not valid_targets:
                        continue
                    # Get the target for the attack.
                    target = self.ui.choose_target(self.player, valid_targets, attack)
                    # If the target is not valid, skip this attack.
                    if not isinstance(target, Character):
                        continue
                    # Perform the attack on the target.
                    attack.execute(self.player, target)
                # Mark the action type as used.
                self.player.use_action_type(action.type)
            else:
                # Get the legal targets for the action.
                valid_targets = self._get_legal_targets(self.player, action)
                # If there are no valid targets, skip this action.
                if not valid_targets:
                    continue
                # Get the target for the action.
                target = self.ui.choose_target(self.player, valid_targets, action)
                # If the target is not valid, skip this action.
                if not isinstance(target, Character):
                    continue
                # Perform the action on the target.
                action.execute(self.player, target)
                # Mark the action type as used.
                self.player.use_action_type(action.type)

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
        full_attacks: list[FullAttack] = get_full_attacks(actions)
        spell_attacks: list[SpellAttack] = get_spell_attacks(actions)
        spell_heals: list[SpellHeal] = get_spell_heals(actions)
        spell_buffs: list[SpellBuff] = get_spell_buffs(actions)
        spell_debuffs: list[SpellDebuff] = get_spell_debuffs(actions)

        if spell_heals:
            result = choose_best_healing_spell_action(npc, allies, spell_heals)
            if result:
                spell, mind_level, targets = result
                for t in targets:
                    spell.cast_spell(npc, t, mind_level)
                npc.mind -= mind_level
                return
        if spell_buffs:
            result = choose_best_buff_spell_action(npc, allies, spell_buffs)
            if result:
                spell, mind_level, targets = result
                for t in targets:
                    spell.cast_spell(npc, t, mind_level)
                npc.mind -= mind_level
                return
        if spell_debuffs:
            result = choose_best_debuff_spell_action(npc, enemies, spell_debuffs)
            if result:
                spell, mind_level, targets = result
                for t in targets:
                    spell.cast_spell(npc, t, mind_level)
                npc.mind -= mind_level
                return
        if spell_attacks:
            result = choose_best_attack_spell_action(npc, enemies, spell_attacks)
            if result:
                spell, mind_level, targets = result
                for target in targets:
                    spell.cast_spell(npc, target, mind_level)
                npc.mind -= mind_level
                return
        if full_attacks:
            result = choose_best_full_attack_action(npc, enemies, full_attacks)
            if result:
                _, associations = result
                for attack, target in associations:
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

    # -- Post-combat only the player is allowed to keep acting and ONLY with SpellHeal --
    def post_combat_healing_phase(self) -> None:
        console.print(Rule("🏥  Post-Combat Healing", style="green"))
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
            spell: Optional[Spell] = self.ui.choose_spell(self.player, heals)
            if spell is None:
                break
            # Gather here the actual targets.
            targets = []
            # Ask for the [MIND] level to use for the spell.
            mind_level = self.ui.choose_mind(self.player, spell)
            if mind_level == -1:
                continue
            # Get the legal targets for the spell.
            targets = self._get_legal_targets(self.player, spell)
            # Filter those that are fully healed.
            targets = [t for t in targets if t.hp < t.HP_MAX and t.is_alive()]
            # Get the number of targets for the spell.
            maximum_num_targets = spell.target_count(self.player, mind_level)
            # There is no point in asking for more targets than we have valid targets.
            maximum_num_targets = min(maximum_num_targets, len(targets))
            # If the action accepts just one target, we can ask for a single target.
            if maximum_num_targets == 1:
                # Ask for a single target.
                targets = [self.ui.choose_target(self.player, targets)]
            # If the action accepts multiple targets, we can ask for multiple targets.
            elif maximum_num_targets > 1:
                # Ask for multiple targets.
                targets = self.ui.choose_targets(
                    self.player, targets, maximum_num_targets
                )
            # Check if the targets are valid.
            if not isinstance(targets, list):
                continue
            if not all(isinstance(t, Character) for t in targets):
                continue
            for target in targets:
                # Perform the action on the target.
                spell.cast_spell(self.player, target, mind_level)
            # Remove the MIND cost from the player.
            self.player.mind -= mind_level

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
