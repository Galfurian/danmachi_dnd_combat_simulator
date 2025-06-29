# combat_manager.py
from ast import Dict
from collections import deque
from logging import info, debug, warning, error
import random
from typing import Tuple

from rich.console import Console
from rich.rule import Rule
from rich.progress import BarColumn, Progress

from character import Character
from actions import (
    BaseAction,
    Spell,
    SpellAttack,
    SpellBuff,
    SpellDebuff,
    SpellHeal,
    WeaponAttack,
)
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
        # Stores the initiative of each participant.
        self.initiatives = {
            participant: random.randint(1, 20) + participant.INITIATIVE
            for participant in self.participants
        }
        # The player character, who is controlled by the user.
        self.player = player
        # The list of enemies the player is fighting against.
        self.enemies = enemies
        # Other non-player-controlled or allied NPCs.
        self.friendlies = friendlies
        # This will now represent the "Round Number"
        self.turn_number = 0
        self.last_action = None
        self.last_targets = []
        self.last_mind_level = -1
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
                f"  {self.initiatives[participant]:3} - {participant.name:<20} - {participant.get_status_line()}",
                markup=True,
            )

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
        while not self.player.turn_done():
            # Get the action.
            action = self.ui.choose_action(self.player)
            if not action:
                break
            # If no input, repeat previous.
            if isinstance(action, int) and action == -1:
                if not self.last_action:
                    continue
                # Check if ALL of the last targets are still alive.
                if not all(t.is_alive() for t in self.last_targets):
                    self.last_action = None
                    self.last_targets = []
                    self.last_mind_level = -1
                    warning(
                        f"{self.player.name} some of the last targets are no longer alive."
                    )
                    continue
                # Check the mind level if the action is a Spell.
                if self.last_mind_level and self.last_mind_level >= self.player.mind:
                    self.last_action = None
                    self.last_targets = []
                    self.last_mind_level = -1
                    warning(
                        f"{self.player.name} does not have enough MIND to repeat the last action at level {self.last_mind_level}."
                    )
                    continue
                console.print(
                    f"[dim]Repeating previous action: {self.last_action.name}[/]"
                )
                # Re-execute:
                for target in self.last_targets:
                    if isinstance(self.last_action, Spell):
                        self.last_action.cast_spell(
                            self.player, target, self.last_mind_level
                        )
                    else:
                        self.last_action.execute(self.player, target)
                self.player.use_action_type(self.last_action.type)
                if self.last_mind_level:
                    self.player.mind -= self.last_mind_level
                continue

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
                # Ask for the [MIND] level to use for the spell.
                mind_level = self.ui.choose_mind(self.player, action)
                # Get the number of targets for the spell.
                maximum_num_targets = action.target_count(self.player, mind_level)
                print(
                    f"{self.player.name} is casting {action.name} at mind level {mind_level} with a maximum of {maximum_num_targets} targets."
                )
                # If the action accepts just one target, we can ask for a single target.
                if maximum_num_targets == 1:
                    # Ask for a single target.
                    targets = [self.ui.choose_target(self.player, valid_targets)]
                # If the action accepts multiple targets, we can ask for multiple targets.
                elif maximum_num_targets > 1:
                    # Ask for multiple targets.
                    targets = self.ui.choose_targets(
                        self.player, valid_targets, maximum_num_targets
                    )
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
                # Update the last action and targets.
                self.last_action = action
                self.last_targets = targets if isinstance(targets, list) else [target]
                self.last_mind_level = mind_level if isinstance(action, Spell) else -1
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
                # Update the last action and targets.
                self.last_action = action
                self.last_targets = [target]
                self.last_mind_level = -1

    def execute_npc_action(self, npc: Character):
        """
        General AI logic for any NPC, whether enemy or friendly:
        - Heal low HP allies (including self)
        - Buff self if not already buffed
        - Attack enemies
        """
        allies = (
            self.get_alive_friendlies()
            if npc in self.friendlies
            else self.get_alive_enemies()
        )
        enemies = (
            self.get_alive_enemies()
            if npc in self.friendlies
            else self.get_alive_friendlies()
        )

        if not enemies:
            warning(f"SKIP: {npc.name} has no enemies to attack.")
            return

        action_list: list[BaseAction] = (
            list(npc.actions.values())
            + list(npc.spells.values())
            + npc.equipped_weapons
        )

        # Categorize actions
        weapon_attacks: list[WeaponAttack] = [
            a for a in action_list if isinstance(a, WeaponAttack)
        ]
        offensive: list[SpellAttack] = [
            a for a in action_list if isinstance(a, SpellAttack)
        ]
        healing: list[SpellHeal] = [a for a in action_list if isinstance(a, SpellHeal)]
        buffing: list[SpellBuff] = [a for a in action_list if isinstance(a, SpellBuff)]
        debuffing: list[SpellDebuff] = [
            a for a in action_list if isinstance(a, SpellDebuff)
        ]

        # Priority 1: Heal lowest-HP ally if any are below threshold.
        if healing:
            possible_healing_choices = []
            for healing_spell in healing:
                mind_level, targets = self._get_heal_targets_for_npc(
                    npc, allies, healing_spell
                )
                if targets:
                    possible_healing_choices.append(
                        (healing_spell, mind_level, targets)
                    )
            if possible_healing_choices:
                # Choose best based on most HP restored, then lowest mind, then most targets
                possible_healing_choices.sort(
                    key=lambda x: (
                        -sum(
                            t.hp_max - t.hp for t in x[2] if t.hp < t.hp_max
                        ),  # most HP to heal
                        x[1],  # least mind
                        -len(x[2]),  # most targets
                    )
                )
                best_healing_spell, mind_level, targets = possible_healing_choices[0]
                for target in targets:
                    best_healing_spell.cast_spell(npc, target, mind_level)
                npc.mind -= mind_level
                return

        # Priority 2: Buff self if not already affected.
        if buffing:
            for buffing_spell in buffing:
                targets = self._get_buff_targets_for_npc(npc, allies, buffing_spell)
                info(
                    f"Buff targets for {npc.name} using {buffing_spell.name}: {[t.name for t in targets]}"
                )

        # Priority 4: Debuff enemies if any are present
        if debuffing:
            for debuffing_spell in debuffing:
                targets = self._get_debuff_targets_for_npc(
                    npc, enemies, debuffing_spell
                )
                info(
                    f"Debuff targets for {npc.name} using {debuffing_spell.name}: {[t.name for t in targets]}"
                )

        # Priority 4: Attack weakest enemy
        if offensive:
            for offensive_spell in offensive:
                targets = self._get_offensive_spell_targets_for_npc(
                    npc, enemies, offensive_spell
                )
                info(
                    f"Offensive spell targets for {npc.name} using {offensive_spell.name}: {[t.name for t in targets]}"
                )

        if weapon_attacks:
            selected_action = weapon_attacks[0]
            target = enemies[0]
            if selected_action and target:
                selected_action.execute(npc, target)
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

    def _get_offensive_spell_targets_for_npc(
        self, npc: Character, enemies: list[Character], spell: SpellAttack
    ) -> list[Character]:
        """
        Determines the optimal targets for an offensive spell cast by an NPC, based on their current mind level.
        Returns a list of Character objects to target.
        """
        if not isinstance(spell, SpellAttack):
            error(f"Invalid spell type: {spell.name} is not a SpellAttack.")
            return []
        # Determine the maximum mind the NPC can spend (cannot go below 0)
        mind_level = max(1, min(npc.mind, npc.mind_max))
        # Determine the number of targets allowed at this mind level
        num_targets = spell.target_count(npc, mind_level)
        # Filter out targets already affected by the spell's effect.
        available_targets = [
            enemy for enemy in enemies if not enemy.has_effect(spell.effect)
        ]
        # Sort by lowest HP first, then by remaining duration of any existing effects.
        prioritized_targets = sorted(
            available_targets,
            key=lambda c: (
                c.hp / c.hp_max if c.hp_max > 0 else 1,
                self._get_remaining_duration(c, spell.effect),
            ),
        )
        # Select up to num_targets
        return prioritized_targets[:num_targets]

    def _get_heal_targets_for_npc(
        self, npc: Character, allies: list[Character], spell: SpellHeal
    ) -> Tuple[int, list[Character]]:
        """
        Determines the optimal targets for a heal spell cast by an NPC, based on their current mind level.
        Returns a list of Character objects to target.
        """
        if not isinstance(spell, SpellHeal):
            error(f"Invalid spell type: {spell.name} is not a SpellHeal.")
            return []
        # Sort by lowest HP first, then by remaining duration of any existing effects.
        available_targets = sorted(
            allies,
            key=lambda c: (
                c.hp / c.hp_max if c.hp_max > 0 else 1,
                self._get_remaining_duration(c, spell.effect),
            ),
        )
        # Filter out allies who are already at full HP or already affected by the heal's effect.
        available_targets = [
            ally
            for ally in available_targets
            if ally.hp < ally.hp_max and not ally.has_effect(spell.effect)
        ]
        # If the spell is single target heal, just return the first target.
        if spell.is_single_target():
            if available_targets:
                return 1, [available_targets[0]]
            else:
                return 0, []
        # Now, based on how many we need to heal, we need to determine how much
        # mind we can spend. Unfortunately, the number of targets is determined
        # by the spell.multi_target_expr, which might contain the [MIND] token.
        selected_mind_level = 1
        selected_targets = []
        mind_levels = (
            spell.upscale_choices if len(spell.upscale_choices) > 0 else [spell.mind]
        )
        for mind_level in mind_levels:
            if mind_level > npc.mind:
                continue
            # Evaluate the number of targets allowed at this mind level.
            num_targets = spell.target_count(npc, mind_level)
            if selected_targets and num_targets > len(available_targets):
                continue
            selected_mind_level = mind_level
            selected_targets = available_targets[:num_targets]
            # If we have selected targets, we can stop.
            if selected_targets:
                break
        if not selected_targets:
            return 0, []
        # Select up to num_targets.
        return selected_mind_level, selected_targets

    def _get_buff_targets_for_npc(
        self, npc: Character, allies: list[Character], spell: SpellBuff
    ) -> list[Character]:
        """
        Determines the optimal targets for a buff spell cast by an NPC, based on their current mind level.
        Returns a list of Character objects to target.
        """
        if not isinstance(spell, SpellBuff):
            error(f"Invalid spell type: {spell.name} is not a SpellBuff.")
            return []
        # Determine the maximum mind the NPC can spend (cannot go below 0)
        mind_level = max(1, min(npc.mind, npc.mind_max))
        # Determine the number of targets allowed at this mind level
        num_targets = spell.target_count(npc, mind_level)
        # Filter out targets already affected by the buff's effect.
        available_targets = [
            ally for ally in allies if not ally.has_effect(spell.effect)
        ]
        # Prioritize self first, then lowest HP allies
        prioritized_targets = sorted(
            available_targets,
            key=lambda c: (
                c != npc,
                c.hp / c.hp_max if c.hp_max > 0 else 1,
                self._get_remaining_duration(c, spell.effect),
            ),
        )
        # Select up to num_targets
        return prioritized_targets[:num_targets]

    def _get_debuff_targets_for_npc(
        self, npc: Character, enemies: list[Character], spell: SpellDebuff
    ) -> list[Character]:
        """
        Determines the optimal targets for a debuff spell cast by an NPC.
        Returns a list of Character objects to target.
        """
        if not isinstance(spell, SpellDebuff):
            error(f"Invalid spell type: {spell.name} is not a SpellDebuff.")
            return []
        # Determine the maximum mind the NPC can spend (cannot go below 0)
        mind_level = max(1, min(npc.mind, npc.mind_max))
        # Determine the number of targets allowed at this mind level
        num_targets = spell.target_count(npc, mind_level)
        # Filter out targets already affected by the debuff's effect.
        available_targets = [
            enemy for enemy in enemies if not enemy.has_effect(spell.effect)
        ]
        # Sort by lowest HP first, then by remaining duration of any existing effects.
        prioritized_targets = sorted(
            available_targets,
            key=lambda c: (
                c.hp / c.hp_max if c.hp_max > 0 else 1,
                self._get_remaining_duration(c, spell.effect),
            ),
        )
        # Select up to num_targets
        return prioritized_targets[:num_targets]

    def _get_remaining_duration(self, target: Character, effect: Effect) -> int:
        for active in target.active_effects:
            if active.effect == effect:
                return active.duration
        return 0

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
