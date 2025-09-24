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
from catchery import log_warning, log_debug
from character import Character
from core.constants import ActionCategory, ActionClass, CharacterType, is_oponent
from core.utils import cprint, crule
from ui.cli_interface import PlayerInterface

from combat.npc_ai import (
    choose_best_attack_spell_action,
    choose_best_base_attack_action,
    choose_best_buff_or_debuff_ability_action,
    choose_best_buff_or_debuff_spell_action,
    choose_best_healing_ability_action,
    choose_best_healing_spell_action,
    choose_best_offensive_ability_action,
    choose_best_target_for_weapon,
    choose_best_weapon_for_situation,
    get_actions_by_type,
    get_natural_attacks,
)

FULL_ATTACK = BaseAction(
    name="Full Attack",
    action_class=ActionClass.STANDARD,
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

    def run_participant_turn(self, participant: Character) -> None:
        """
        Runs a single participant's turn in combat.

        Args:
            participant (Character):
                The participant whose turn is being run.

        """
        if participant.is_alive():
            # Reset the participant's turn flags to allow for new actions.
            participant.reset_available_actions()

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
            if self.player.has_action_class(ActionClass.STANDARD):
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
            log_warning(
                "No available attacks for the full attack action",
                {"player": self.player.name, "context": "full_attack_selection"},
            )
            return

        # Choose the attack type to use for all attacks in the sequence
        attack = self.ui.choose_action(attacks)
        if attack is None or not isinstance(attack, BaseAttack):
            log_warning(
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
            log_warning(
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
            if target.is_dead():
                # Get remaining legal targets
                remaining_targets = self._get_legal_targets(self.player, attack)
                if not remaining_targets:
                    break
                target = self.ui.choose_target(remaining_targets, [])

            if not isinstance(target, Character):
                return

            # Perform the attack
            attack.execute(self.player, target)
            attacks_made += 1

            # Add cooldown only once for the attack type
            if attack_num == 0:
                self.player.add_cooldown(attack)

        # Mark the action class as used.
        self.player.use_action_class(ActionClass.STANDARD)

    def ask_for_player_spell_cast(self, spells: list[Spell]) -> bool:
        """Handles the player's choice to cast a spell.

        Args:
            spells (list[Spell]): List of available spells for the player.

        Returns:
            bool: True if a spell was successfully cast, False otherwise.

        """
        while True:
            # Ask for the spell and the rank level.
            choice = self.ask_for_player_spell_and_rank(spells)
            if choice is None:
                break
            if isinstance(choice, str):
                if choice == "q":
                    break
                continue
            # Unpack the spell and mind level.
            spell, rank = choice
            while True:
                # Get the maximum number of targets if applicable.
                variables = spell.spell_get_variables(self.player, rank)
                # Get the maximum number of targets if applicable.
                max_targets = spell.target_count(variables)
                # Get the targets for the spell.
                targets = self.ask_for_player_targets(spell, max_targets)
                if not targets:
                    log_warning(
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
                    spell.cast_spell(
                        actor=self.player,
                        target=target,
                        rank=rank,
                    )
                # Remove the MIND cost from the player.
                self.player.use_mind(spell.mind_cost[rank])
                # Mark the action class as used.
                self.player.use_action_class(spell.action_class)
                # Add the spell to the cooldowns if it has one.
                self.player.add_cooldown(spell)
                return True
        return False

    def ask_for_player_spell_and_rank(
        self,
        spells: list[Spell],
    ) -> tuple[Spell, int] | str | None:
        """
        Asks the player to choose a spell from their available spells.

        Args:
            spells (list[Spell]):
            List of available spells for the player.

        Returns:
            Optional[tuple[Spell, int] | str]:
                The chosen spell and rank level, or None if no spell was selected.

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
            # Ask for the rank level to use for the spell.
            rank = self.ui.choose_rank(self.player, spell)
            if rank == -1:
                return "q"
            return spell, rank
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
            log_warning(
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
            log_warning(
                f"No valid targets for {action.name}",
                {
                    "player": self.player.name,
                    "action": action.name,
                    "context": "multi_target_selection",
                },
            )
            return None
        if max_targets <= 0:
            log_warning(
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
                log_warning(
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

    def execute_npc_action(self, npc: Character) -> None:
        """
        Executes the action logic for an NPC during their turn.

        Args:
            npc (Character):
                The NPC whose action is being executed.

        """
        allies = self.get_alive_friendlies(npc)
        enemies = self.get_alive_opponents(npc)

        if not enemies:
            log_warning(
                f"SKIP: {npc.name} has no enemies to attack",
                {
                    "npc": npc.name,
                    "allies_count": len(allies),
                    "context": "npc_ai_decision",
                },
            )
            return

        # Try perfroming actions in order of priority.
        self._execute_npc_healing(npc, allies)
        self._execute_npc_buff(npc, allies)
        self._execute_npc_debuff(npc, enemies)
        self._execute_npc_spell_attack(npc, enemies)
        self._execute_npc_ability_attack(npc, enemies)
        self._execute_npc_full_attack(npc, enemies)
        self._execute_npc_full_natural_attack(npc, enemies)

        # Just check if the NPC still has all action classes available but did
        # nothing.
        if (
            npc.has_action_class(ActionClass.BONUS)
            and npc.has_action_class(ActionClass.FREE)
            and npc.has_action_class(ActionClass.STANDARD)
        ):
            log_warning(
                f"SKIP: {npc.name} could not find any action to perform",
                {
                    "npc": npc.name,
                    "allies_count": len(allies),
                    "enemies_count": len(enemies),
                    "context": "npc_ai_decision",
                },
            )

    def _execute_npc_healing(
        self,
        npc: Character,
        allies: list[Character],
    ) -> None:
        """
        Executes the best healing action for the NPC if available.

        Args:
            npc (Character):
                The NPC whose healing is being executed.
            allies (list[Character]):
                List of friendly characters.
        """

        # Check for healing spells.
        candidate_spell = choose_best_healing_spell_action(
            source=npc,
            allies=allies,
            spells=get_actions_by_type(npc, SpellHeal),
        )
        if candidate_spell:
            # Cast the healing spell on the targets.
            for target in candidate_spell.targets:
                candidate_spell.spell.cast_spell(
                    actor=npc,
                    target=target,
                    rank=candidate_spell.rank,
                )
            # Add the spell to the cooldowns if it has one.
            npc.add_cooldown(candidate_spell.spell)
            # Mark the action class as used.
            npc.use_action_class(candidate_spell.spell.action_class)
            # Remove the MIND cost from the NPC.
            npc.use_mind(candidate_spell.mind_level)

        # Check for healing abilities.
        candidate_ability = choose_best_healing_ability_action(
            source=npc,
            allies=allies,
            abilities=get_actions_by_type(npc, AbilityHeal),
        )
        if candidate_ability:
            # Use the healing ability on the targets.
            for target in candidate_ability.targets:
                candidate_ability.ability.execute(
                    actor=npc,
                    target=target,
                )
            # Add the ability to the cooldowns if it has one.
            npc.add_cooldown(candidate_ability.ability)
            # Mark the action class as used.
            npc.use_action_class(candidate_ability.ability.action_class)

    def _execute_npc_buff(
        self,
        npc: Character,
        allies: list[Character],
    ) -> None:
        """
        Executes the best buff spell for the NPC if available.

        Args:
            npc (Character):
                The NPC whose buff is being executed.
            allies (list[Character]):
                List of friendly characters.
        """

        # Check for buff spells.
        candidate_spell = choose_best_buff_or_debuff_spell_action(
            source=npc,
            targets=allies,
            spells=get_actions_by_type(npc, SpellBuff),
        )
        if candidate_spell:
            # Cast the buff spell on the targets.
            for target in candidate_spell.targets:
                candidate_spell.spell.cast_spell(
                    actor=npc,
                    target=target,
                    rank=candidate_spell.rank,
                )
            # Add the spell to the cooldowns if it has one.
            npc.add_cooldown(candidate_spell.spell)
            # Mark the action class as used.
            npc.use_action_class(candidate_spell.spell.action_class)
            # Remove the MIND cost from the NPC.
            npc.use_mind(candidate_spell.mind_level)

        # Check for buff abilities.
        candidate_ability = choose_best_buff_or_debuff_ability_action(
            source=npc,
            targets=allies,
            abilities=get_actions_by_type(npc, AbilityBuff),
        )
        if candidate_ability:
            # Use the buff ability on the targets.
            for target in candidate_ability.targets:
                candidate_ability.ability.execute(
                    actor=npc,
                    target=target,
                )
            # Add the ability to the cooldowns if it has one.
            npc.add_cooldown(candidate_ability.ability)
            # Mark the action class as used.
            npc.use_action_class(candidate_ability.ability.action_class)

    def _execute_npc_debuff(
        self,
        npc: Character,
        enemies: list[Character],
    ) -> None:
        """
        Executes the best debuff spell for the NPC if available.

        Args:
            npc (Character):
                The NPC whose debuff is being executed.
            enemies (list[Character]):
                List of enemy characters.
        """

        # Check for debuff spells.
        candidate_spell = choose_best_buff_or_debuff_spell_action(
            source=npc,
            targets=enemies,
            spells=get_actions_by_type(npc, SpellDebuff),
        )
        if candidate_spell:
            # Cast the debuff spell on the targets.
            for target in candidate_spell.targets:
                candidate_spell.spell.cast_spell(
                    actor=npc,
                    target=target,
                    rank=candidate_spell.rank,
                )
            # Add the spell to the cooldowns if it has one.
            npc.add_cooldown(candidate_spell.spell)
            # Mark the action class as used.
            npc.use_action_class(candidate_spell.spell.action_class)
            # Remove the MIND cost from the NPC.
            npc.use_mind(candidate_spell.mind_level)

        # Check for debuff abilities.
        candidate_ability = choose_best_buff_or_debuff_ability_action(
            source=npc,
            targets=enemies,
            abilities=get_actions_by_type(npc, AbilityDebuff),
        )
        if candidate_ability:
            # Use the debuff ability on the targets.
            for target in candidate_ability.targets:
                candidate_ability.ability.execute(
                    actor=npc,
                    target=target,
                )
            # Add the ability to the cooldowns if it has one.
            npc.add_cooldown(candidate_ability.ability)
            # Mark the action class as used.
            npc.use_action_class(candidate_ability.ability.action_class)

    def _execute_npc_spell_attack(
        self,
        npc: Character,
        enemies: list[Character],
    ) -> None:
        """
        Executes the best offensive spell for the NPC if available.

        Args:
            npc (Character):
                The NPC whose spell attack is being executed.
            enemies (list[Character]):
                List of enemy characters.

        """
        # Check for attack spells.
        candidate = choose_best_attack_spell_action(
            source=npc,
            enemies=enemies,
            spells=get_actions_by_type(npc, SpellOffensive),
        )
        if candidate:
            # Cast the attack spell on the targets.
            for target in candidate.targets:
                candidate.spell.cast_spell(
                    actor=npc,
                    target=target,
                    rank=candidate.rank,
                )
            # Add the spell to the cooldowns if it has one.
            npc.add_cooldown(candidate.spell)
            # Mark the action class as used.
            npc.use_action_class(candidate.spell.action_class)
            # Remove the MIND cost from the NPC.
            npc.use_mind(candidate.mind_level)

    def _execute_npc_ability_attack(
        self,
        npc: Character,
        enemies: list[Character],
    ) -> None:
        """
        Executes the best offensive ability for the NPC if available.

        Args:
            npc (Character):
                The NPC whose ability attack is being executed.
            enemies (list[Character]):
                List of enemy characters.

        """
        # Check for attack abilities.
        candidate = choose_best_offensive_ability_action(
            source=npc,
            enemies=enemies,
            abilities=get_actions_by_type(npc, AbilityOffensive),
        )
        if candidate:
            # Use the offensive ability on the targets.
            for target in candidate.targets:
                candidate.ability.execute(npc, target)
            # Add the ability to the cooldowns if it has one.
            npc.add_cooldown(candidate.ability)
            # Mark the action class as used.
            npc.use_action_class(candidate.ability.action_class)

    def _execute_npc_full_attack(
        self,
        npc: Character,
        enemies: list[Character],
    ) -> None:
        """
        Executes a full attack sequence for the NPC if possible.

        Args:
            npc (Character):
                The NPC performing the full attack.
            enemies (list[Character]):
                List of enemy characters.

        """
        weapon_attacks: list[WeaponAttack] = get_actions_by_type(npc, WeaponAttack)
        if not weapon_attacks:
            return

        # Choose the best weapon type once for the full attack sequence
        attack = choose_best_weapon_for_situation(npc, weapon_attacks, enemies)
        if not attack:
            return

        # Perform multiple attacks with the same weapon type.
        attacks_made: bool = False
        for _ in range(npc.number_of_attacks):
            target = choose_best_target_for_weapon(npc, attack, enemies)
            # If we have a valid target, perform the attack.
            if target:
                attack.execute(npc, target)
                attacks_made = True

        # Add cooldown and mark action class only once after all attacks.
        if attacks_made:
            npc.add_cooldown(attack)
            npc.use_action_class(attack.action_class)

    def _execute_npc_full_natural_attack(
        self,
        npc: Character,
        enemies: list[Character],
    ) -> None:
        """
        Executes a full sequence of natural attacks for the NPC if possible.

        Args:
            npc (Character):
                The NPC performing the natural attacks.
            enemies (list[Character]):
                List of enemy characters.

        """
        from actions.attacks.natural_attack import NaturalAttack

        natural_attacks: list[NaturalAttack] = get_natural_attacks(npc)
        if not natural_attacks:
            return

        # All natural attacks are performed once each in a full sequence.
        for attack in natural_attacks:
            # Choose the best target for this attack.
            target = choose_best_target_for_weapon(npc, attack, enemies)
            # If we have a valid target, perform the attack.
            if target:
                attack.execute(npc, target)
                # Add cooldown and mark action class for the natural attack.
                npc.add_cooldown(attack)
                npc.use_action_class(attack.action_class)

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
