# combat_manager.py
from ast import Dict
from collections import deque
from logging import info, debug, warning, error
import random

from rich.console import Console
from rich.rule import Rule
from rich.progress import BarColumn, Progress

from character import Character
from actions import BaseAction, Spell
from effect import *
from constants import *
from interfaces import PlayerInterface

console = Console()

TARGET_RULES = {
    # Each key is a tuple of (is_enemy, ActionCategory)
    (True, ActionCategory.OFFENSIVE): lambda self: self.get_alive_friendlies(),
    (True, ActionCategory.HEALING): lambda self: self.get_alive_enemies(),
    (True, ActionCategory.BUFF): lambda self: self.get_alive_friendlies(),
    (True, ActionCategory.DEBUFF): lambda self: self.get_alive_enemies(),
    (True, ActionCategory.UTILITY): lambda self: self.get_alive_participants(),
    (False, ActionCategory.OFFENSIVE): lambda self: self.get_alive_enemies(),
    (False, ActionCategory.HEALING): lambda self: self.get_alive_friendlies(),
    (False, ActionCategory.BUFF): lambda self: self.get_alive_friendlies(),
    (False, ActionCategory.DEBUFF): lambda self: self.get_alive_enemies(),
    (False, ActionCategory.UTILITY): lambda self: self.get_alive_participants(),
}


class CombatManager:
    def __init__(
        self,
        ui: PlayerInterface,
        player: Character,
        enemies: list[Character],
        friendlies: list[Character],  # These are allies other than the player
    ):
        # Store the ui.
        self.ui = ui
        # Combine all participants for the deque, ensuring player is handled specifically
        self.participants = deque([player] + enemies + (friendlies or []))
        # The player character, who is controlled by the user.
        self.player = player
        # The list of enemies the player is fighting against.
        self.enemies = enemies
        # Other non-player-controlled or allied NPCs.
        self.friendlies = friendlies
        # This will now represent the "Round Number"
        self.turn_number = 0
        # Call the new initialize method.
        self.initialize()

    def initialize(self) -> None:
        """Initializes the combat by sorting participants by initiative."""
        # Ensure each character has an 'initiative' attribute (e.g., random.randint(1, 20) + char.DEX)
        # before calling initialize if not already done.
        self.participants = deque(
            sorted(self.participants, key=lambda c: c.initiative, reverse=True)
        )
        console.print("[bold green]Combat initialized![/]")
        console.print("[bold yellow]Turn Order:[/]")
        for participant in self.participants:
            console.print(f"  {participant.initiative:3} - {participant.name}")

    def get_alive_participants(self) -> list[Character]:
        """Returns a list of all characters in combat (player, enemies, friendlies) who are still alive."""
        # This method should consider all characters known to the CombatManager, not just the deque,
        # as deque is for turn order, not comprehensive participant list.
        all_known_chars = [self.player] + self.enemies + self.friendlies
        return [char for char in all_known_chars if char.is_alive()]

    def get_alive_enemies(self) -> list[Character]:
        """Returns a list of enemies who are still alive."""
        return [char for char in self.enemies if char.is_alive()]

    def get_alive_friendlies(self) -> list[Character]:
        """Returns a list of friendlies (including the player) who are still alive."""
        return [char for char in [self.player] + self.friendlies if char.is_alive()]

    def run_turn(self) -> bool:
        """
        Runs a single character's turn within a combat round.
        Returns False if combat should end, True otherwise.
        """
        # Combat end checks
        if not self.get_alive_participants():
            debug("No participants left in combat. Combat ends.")
            return False
        if not self.get_alive_enemies():
            debug("All enemies defeated! Combat ends.")
            return False
        # Prepare a clean queue of participants for this turn.
        current_turn_participants = deque(
            char for char in self.participants if char.is_alive()
        )
        if not current_turn_participants:
            debug("No participants left for this turn. Combat ends.")
            return False
        # Print the status of the player at the turn's end.
        console.print(Rule(title=f"⏱ Start of Turn {self.turn_number}", style="cyan"))
        # Keep dequeuing participants until we find one that can act.
        while current_turn_participants:
            # Popo the next participant in the turn order.
            participant = current_turn_participants.popleft()
            # If the participant is not alive, skip their turn.
            if not participant.is_alive():
                continue
            # Run the participant's turn.
            self.run_participant_turn(participant)
        self.turn_number += 1
        return True

    def run_participant_turn(self, participant: Character):
        """
        Runs a single participant's turn within a combat round.
        This is a helper method to allow for specific participant turns.
        """
        if participant.is_alive():
            # Reset the participant's turn flags to allow for new actions.
            participant.reset_turn_flags()
            # Execute the participant's action based on whether they are the player or an NPC.
            if participant == self.player:
                self.ask_for_player_action()
            else:
                self.execute_enemy_action(participant)
            # Apply end-of-turn updates and check for expiration
            participant.turn_update()

    def ask_for_player_action(self) -> None:
        """
        Handles player input for choosing an action and target during their turn.
        """
        while not self.player.turn_done():
            # Get the action.
            action = self.ui.choose_action(self.player)
            if not isinstance(action, BaseAction):
                break
            # Get the legal targets for the chosen action.
            valid_targets = self._get_legal_targets(self.player, action)
            # If there are no valid targets, skip this action.
            if not valid_targets:
                warning(
                    f"{self.player.name} has no valid targets for {action.name}. Skipping action."
                )
                continue
            # If the action is a Spell, we need to handle it differently.
            if isinstance(action, Spell):
                # Gather here the actual targets.
                targets = []
                # Get the number of targets for the spell.
                maximum_num_targets = action.target_count(self.player, -1)
                # Ask for the [MIND] level to use for the spell.
                mind_level = self.ui.choose_mind(self.player, action)
                # If the action accepts just one target, we can ask for a single target.
                if maximum_num_targets == 1:
                    # Ask for a single target.
                    targets = [self.ui.choose_target(self.player, valid_targets)]
                # If the action accepts multiple targets, we can ask for multiple targets.
                elif maximum_num_targets > 1:
                    # Ask for multiple targets.
                    targets = self.ui.choose_targets(self.player, valid_targets)
                # Check if the targets are valid.
                if not isinstance(targets, list):
                    continue
                if not all(isinstance(t, Character) for t in targets):
                    continue
                for target in targets:
                    # Perform the action on the target.
                    action.cast_spell(self.player, target, mind_level)
                # Remove the MIND cost from the player.
                self.player.mind -= mind_level
                # Mark the action type as used.
                self.player.use_action_type(action.type)
            else:
                # Get the target for the action.
                target = self.ui.choose_target(self.player, valid_targets)
                # If the target is not valid, skip this action.
                if not isinstance(target, Character):
                    continue
                # Perform the action on the target.
                action.execute(self.player, target)
                # Mark the action type as used.
                self.player.use_action_type(action.type)

    def execute_enemy_action(self, npc: Character):
        """
        Placeholder for NPC AI logic.
        Simple AI: If an enemy, always tries to attack the player.
        If a friendly NPC, tries to heal player if low, otherwise attacks an enemy.
        """
        is_enemy_npc = npc in self.enemies
        is_friendly_npc = npc in self.friendlies

        target_char = None
        selected_ability = None

        if is_enemy_npc:
            target_char = self.player
            if not target_char.is_alive():
                warning(
                    f"{npc.name} has no valid target ({target_char.name} is unconscious). Skipping turn."
                )
                return

            for action in npc.actions.values():
                if action.category == ActionCategory.OFFENSIVE:
                    selected_ability = action
                    break
            if not selected_ability:
                for spell in npc.spells.values():
                    if spell.category == ActionCategory.OFFENSIVE:
                        selected_ability = spell
                        break

        elif is_friendly_npc:
            if self.player.is_alive() and self.player.hp < self.player.hp_max * 0.5:
                for spell in npc.spells.values():
                    if spell.category == ActionCategory.HEALING:
                        selected_ability = spell
                        target_char = self.player
                        break

            if not selected_ability:
                alive_enemies = self.get_alive_enemies()
                if alive_enemies:
                    target_char = random.choice(alive_enemies)
                    for action in npc.actions.values():
                        if action.category == ActionCategory.OFFENSIVE:
                            selected_ability = action
                            break
                    if not selected_ability:
                        for spell in npc.spells.values():
                            if spell.category == ActionCategory.OFFENSIVE:
                                selected_ability = spell
                                break

        if not selected_ability:
            warning(f"{npc.name} has no suitable action. Skipping turn.")
            return
        if not target_char or not target_char.is_alive():
            warning(
                f"{npc.name} found no valid target for their action. Skipping turn."
            )
            return

        selected_ability.execute(npc, target_char)

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
        is_enemy = character in self.enemies
        key = (is_enemy, ability.category)
        rule = TARGET_RULES.get(key)
        return rule(self) if rule else []

    def _is_valid_target(
        self, character: Character, target: Character, ability: BaseAction
    ) -> bool:
        """
        Checks if the target is valid for the given character and ability.
        """
        if not target.is_alive():
            warning(f"Target {target.name} is not alive and cannot be targeted.")
            return False
        legal_targets = self._get_legal_targets(character, ability)
        if target not in legal_targets:
            warning(
                f"{target.name} is not a valid target for {character.name}'s {ability.name}."
            )
            return False
        return True

    def _show_status(self, character: Character):
        console = Console()
        console.print(f"[bold]{character.name}[/]  AC {character.ac}")
        bar = Progress(
            "{task.description}",
            BarColumn(bar_width=24),
            "{task.completed}/{task.total}",
            console=console,
            transient=True,
        )
        bar.add_task("HP ", total=character.hp_max, completed=character.hp)
        bar.add_task("MND", total=character.mind_max, completed=character.mind)
        bar.refresh()

    def is_combat_over(self) -> bool:
        """
        Determines if combat has ended.
        Combat ends if the player is defeated, or all enemies are defeated.
        """
        player_alive = self.player.is_alive()
        enemies_alive = any(char.is_alive() for char in self.get_alive_enemies())

        if not player_alive:
            console.print("[bold red]Combat ends. You have been defeated![/]")
            return True
        if not enemies_alive:
            console.print(
                "[bold green]Combat ends. All enemies defeated! You are victorious![/]"
            )
            return True
        return False
