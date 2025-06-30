# combat_manager.py
from collections import deque
from logging import info, debug, warning, error
import random
from typing import Tuple

from rich.console import Console
from rich.rule import Rule

from character import *
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
                f"  {self.initiatives[participant]:3} - {participant.name:<20} - {participant.get_status_line()}",
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
        while not self.player.turn_done():
            # Get the action.
            action: Optional[BaseAction] = self.ui.choose_action(self.player)
            if not action:
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
                # Ask for the [MIND] level to use for the spell.
                mind_level = self.ui.choose_mind(self.player, action)
                if mind_level == 0:
                    continue
                # Get the number of targets for the spell.
                maximum_num_targets = action.target_count(self.player, mind_level)
                # There is no point in asking for more targets than we have valid targets.
                maximum_num_targets = min(maximum_num_targets, len(valid_targets))
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
            spell_heal_choices: list[tuple[SpellHeal, int, list[Character]]] = []
            for healing_spell in healing:
                mind_level, targets = self._get_spell_heal_targets(
                    npc, allies, healing_spell
                )
                if targets:
                    spell_heal_choices.append((healing_spell, mind_level, targets))
            if spell_heal_choices:
                # Choose best based on most HP restored, then lowest mind, then most targets
                spell_heal_choices.sort(
                    key=lambda x: (
                        -sum(
                            t.HP_MAX - t.hp for t in x[2] if t.hp < t.HP_MAX
                        ),  # most HP to heal
                        x[1],  # least mind
                        -len(x[2]),  # most targets
                    )
                )
                best_healing_spell, mind_level, targets = spell_heal_choices[0]
                for target in targets:
                    best_healing_spell.cast_spell(npc, target, mind_level)
                npc.mind -= mind_level
                return

        # Priority 2: Buff self if not already affected.
        if buffing:
            spell_buff_choices: list[tuple[SpellBuff, int, list[Character]]] = []
            for buffing_spell in buffing:
                mind_level, targets = self._get_spell_buff_targets(
                    npc, allies, buffing_spell
                )
                if targets:
                    spell_buff_choices.append((buffing_spell, mind_level, targets))
            if spell_buff_choices:
                # Choose best based on most beneficial effect, then lowest mind, then most targets
                spell_buff_choices.sort(
                    key=lambda x: (
                        -sum(
                            t.get_effect_usefulness_index(x[0].effect) for t in x[2]
                        ),  # most beneficial effect
                        x[1],  # least mind
                        -len(x[2]),  # most targets
                    )
                )
                best_buffing_spell, mind_level, targets = spell_buff_choices[0]
                for target in targets:
                    best_buffing_spell.cast_spell(npc, target, mind_level)
                npc.mind -= mind_level
                return

        # Priority 4: Debuff enemies if any are present
        if debuffing:
            for debuffing_spell in debuffing:
                targets = self._get_debuff_targets_for_npc(
                    npc, enemies, debuffing_spell
                )
                debug(
                    f"Debuff targets for {npc.name} using {debuffing_spell.name}: {[t.name for t in targets]}"
                )

        # Priority 4: Attack weakest enemy
        if offensive:
            possible_choices: list[tuple[SpellAttack, int, list[Character]]] = []
            for offensive_spell in offensive:
                mind_level, targets = self._get_spell_attack_targets(
                    npc, enemies, offensive_spell
                )
                if targets:
                    possible_choices.append((offensive_spell, mind_level, targets))
            if possible_choices:
                # Choose best based on most damage, then lowest mind, then most targets
                possible_choices.sort(
                    key=lambda x: (
                        -sum(
                            t.HP_MAX - t.hp for t in x[2] if t.hp < t.HP_MAX
                        ),  # most damage
                        x[1],  # least mind
                        -len(x[2]),  # most targets
                    )
                )
                best_offensive_spell, mind_level, targets = possible_choices[0]
                for target in targets:
                    best_offensive_spell.cast_spell(npc, target, mind_level)
                npc.mind -= mind_level
                return

        if weapon_attacks:
            targets = self._get_weapon_attack_targets(npc, enemies, weapon_attacks[0])
            if targets:
                weapon_attacks[0].execute(npc, targets[0])
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

    def _get_weapon_attack_targets(
        self, npc: Character, enemies: list[Character], action: WeaponAttack
    ) -> list[Character]:
        """
        Determines the optimal targets for a weapon attack cast by an NPC.
        Returns a list of Character objects to target.
        """
        # Sort by lowest HP first, then by remaining duration of any existing effects.
        prioritized_targets = sort_for_weapon_attack(npc, action, enemies)
        # Select the first target (the weakest one).
        return prioritized_targets[:1]

    def _get_spell_heal_targets(
        self, npc: Character, allies: list[Character], spell: SpellHeal
    ) -> Tuple[int, list[Character]]:
        """
        Determines the optimal targets for a heal spell cast by an NPC, based on their current mind level.
        Returns a list of Character objects to target.
        """
        # Sort by lowest HP first, then by remaining duration of any existing effects.
        targets = sort_for_spell_heal(npc, spell, allies)
        # Now, based on how many we need to heal, we need to determine how much
        # mind we can spend. Unfortunately, the number of targets is determined
        # by the spell.multi_target_expr, which might contain the [MIND] token.
        mind_level, targets = self._get_mind_level_and_targets_for_spell(
            npc, spell, targets
        )
        # If no targets are available, return 0 mind and an empty list.
        if not targets:
            return 0, []
        # Select up to num_targets.
        return mind_level, targets

    def _get_spell_attack_targets(
        self, npc: Character, enemies: list[Character], spell: SpellAttack
    ) -> Tuple[int, list[Character]]:
        """
        Determines the optimal targets for an offensive spell cast by an NPC.
        Returns a list of Character objects to target.
        """
        # Sort by lowest HP first, then by remaining duration of any existing effects.
        targets = sort_for_spell_attack(npc, spell, enemies)
        # Select the mind level and targets based on the spell's requirements.
        mind_level, targets = self._get_mind_level_and_targets_for_spell(
            npc, spell, targets
        )
        # If no targets are available, return an empty list.
        if not targets:
            return 0, []
        # Return the selected targets.
        return mind_level, targets

    def _get_spell_buff_targets(
        self, npc: Character, allies: list[Character], spell: SpellBuff
    ) -> Tuple[int, list[Character]]:
        """
        Determines the optimal targets for a buff spell cast by an NPC.
        Returns a list of Character objects to target.
        """
        # Sort by AC, then by HP percentage, and finally by the number of active DoTs.
        targets = sort_for_spell_buff(npc, spell, allies)
        # Select the mind level and targets based on the spell's requirements.
        mind_level, targets = self._get_mind_level_and_targets_for_spell(
            npc, spell, targets
        )
        # If no targets are available, return an empty list.
        if not targets:
            return 0, []
        # Return the selected targets.
        return mind_level, targets

    def _get_debuff_targets_for_npc(
        self, npc: Character, enemies: list[Character], spell: SpellDebuff
    ) -> list[Character]:
        """
        Determines the optimal targets for a debuff spell cast by an NPC.
        Returns a list of Character objects to target.
        """
        # Determine the maximum mind the NPC can spend (cannot go below 0)
        mind_level = max(1, min(npc.mind, npc.MIND_MAX))
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
                c.hp / c.HP_MAX if c.HP_MAX > 0 else 1,
                c.get_remaining_effect_duration(spell.effect),
            ),
        )
        # Select up to num_targets
        return prioritized_targets[:num_targets]

    def _get_mind_level_and_targets_for_spell(
        self, character: Character, spell: Spell, targets: list[Character]
    ) -> Tuple[int, list[Character]]:
        selected_mind_level = 0
        selected_targets = []
        if targets:
            for mind_level in spell.get_upscale_choices():
                # If the mind level is greater than the character's current mind, skip it.
                if mind_level > character.mind:
                    continue
                # Evaluate the number of targets allowed at this mind level.
                num_targets = spell.target_count(character, mind_level)
                # If we have already selected targets and the number of targets
                # allowed at this mind level is greater than the number of targets,
                # we can keep the previous mind level and targets.
                if selected_targets and num_targets > len(targets):
                    break
                # Update the selected mind level and targets.
                selected_mind_level = mind_level
                selected_targets = targets[:num_targets]
        # Return the selected mind level and targets.
        return selected_mind_level, selected_targets

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
