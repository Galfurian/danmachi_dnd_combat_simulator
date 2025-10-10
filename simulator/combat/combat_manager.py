"""
Combat manager module for the simulator.

Handles the overall combat flow, including turn management, initiative,
character actions, and combat resolution between players and enemies.
"""

# combat_manager.py
import random
from collections import deque
from logging import debug
from typing import Callable

from actions.attacks.base_attack import (
    BaseAttack,
)
from actions.base_action import (
    BaseAction,
)
from actions.spells.base_spell import (
    BaseSpell,
)
from character.main import Character
from combat.npc_ai import (
    choose_best_attack_spell_action,
    choose_best_base_attack_action,
    choose_best_buff_or_debuff_ability_action,
    choose_best_buff_or_debuff_spell_action,
    choose_best_healing_ability_action,
    choose_best_healing_spell_action,
    choose_best_offensive_ability_action,
    choose_best_target_for_attack,
    get_actions_by_type,
    get_natural_attacks,
)
from core.constants import (
    ActionCategory,
    ActionClass,
    CharacterType,
    is_oponent,
)
from core.logging import logger
from core.utils import cprint, crule
from ui.cli_interface import PlayerInterface

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
        participants: list[Character],
    ):
        """Initialize the CombatManager with participants and turn order.

        Args:
            participants (list[Character]): List of all characters participating in combat.

        """
        # Store the ui.
        self.ui: PlayerInterface = PlayerInterface()

        # Combine all participants for the deque
        self.participants: deque[Character] = deque(participants)

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
            status_line = participant.display.get_status_line(
                show_bars=True, show_ac=show_ac
            )
            cprint(f"    🎲 {self.initiatives[participant]:3}  {status_line}")

    def is_combat_over(self) -> bool:
        """Determines if combat has ended.

        Returns:
            bool: True if combat has ended, False otherwise.

        """
        alive_enemies = self.get_alive_participants(CharacterType.ENEMY)

        # Combat ends if there are no enemies left
        if not alive_enemies:
            cprint("[bold green]Combat ends. All enemies defeated![/]")
            return True

        # If there are no more players or allies alive, combat ends.
        alive_players = self.get_alive_participants(CharacterType.PLAYER)
        alive_allies = self.get_alive_participants(CharacterType.ALLY)
        if not alive_players and not alive_allies:
            cprint("[bold red]Combat ends. All allies have been defeated![/]")
            return True

        return False

    def get_alive_participants(
        self,
        char_type: CharacterType | None = None,
    ) -> list[Character]:
        """
        Returns a list of all participants (player, enemies, friendlies) who are
        still alive.

        Args:
            char_type (CharacterType | None, optional):
                The type of character to filter by. If None, returns all alive
                participants.

        Returns:
            list[Character]:
                A list of alive characters.

        """
        if char_type is not None:
            return [
                char
                for char in self.participants
                if char.is_alive() and char.char_type == char_type
            ]
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
        if not self.get_alive_participants(CharacterType.ENEMY):
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
        if not participant.is_alive():
            return

        # Print the participant's status line with appropriate display mode
        if participant.char_type == CharacterType.PLAYER:
            # Player gets full display: numbers + bars + AC
            cprint(
                participant.display.get_status_line(
                    show_all_effects=True,
                    show_numbers=True,
                    show_bars=True,
                    show_ac=True,
                )
            )
        else:
            # NPCs get bars only for cleaner display.
            cprint(
                participant.display.get_status_line(
                    show_all_effects=False,
                    show_numbers=False,
                    show_bars=True,
                    show_ac=False,
                )
            )

        # Start of turn effects
        participant.turn_start(self.turn_number)

        # Check if character is incapacitated
        if participant.is_incapacitated():
            cprint(
                f"    💤 {participant.name} is incapacitated and cannot act this turn."
            )
        else:
            # Execute the participant's action based on whether they are the
            # player or an NPC.
            if participant.char_type == CharacterType.PLAYER:
                self.ask_for_player_action(participant)
            else:
                self.execute_npc_action(participant)

        # Apply end-of-turn updates and check for expiration
        participant.turn_end(self.turn_number)

        cprint("")

    def ask_for_player_action(self, player: Character) -> None:
        """Handles player input for choosing an action and target during their turn."""
        if not self.get_alive_opponents(player):
            return

        while not player.actions.turn_done():
            # Gather available actions and attacks.
            actions = []
            if player.actions.has_action_class(ActionClass.STANDARD):
                actions.append(FULL_ATTACK)
            actions.extend(player.actions.get_available_abilities())
            spells = player.actions.get_available_spells()

            # Main action selection menu.
            submenus = []
            if spells:
                submenus.append("Cast a Spell")

            # Player selects an action or submenu option.
            choice = self.ui.choose_action(actions, submenus, "Skip")
            if isinstance(choice, str) and choice == "q":
                break
            if choice is None:
                break
            # If the action is a BaseSpell, we need to handle it differently.
            if choice == FULL_ATTACK:
                self.ask_for_player_full_attack(player)
            elif choice == "Cast a Spell":
                self.ask_for_player_spell_cast(player, spells)
            elif isinstance(choice, BaseAction):
                target = self.ask_for_player_target(player, choice)
                if isinstance(target, str) and target == "q":
                    break
                if not isinstance(target, Character):
                    continue
                # Perform the action on the target.
                choice.execute(player, target)
                # Add the action to the cooldowns if it has one.
                player.actions.add_cooldown(choice)
                # Mark the action class as used.
                player.actions.use_action_class(choice.action_class)
            else:
                logger.warning(f"Invalid action selected {choice}")

    def ask_for_player_full_attack(self, player: Character) -> None:
        """Asks the player to choose targets for a full attack action."""
        # Get the list of all attacks available in the full attack.
        attacks = player.actions.get_available_attacks()
        if not attacks:
            logger.warning("No available attacks for the full attack action")
            return

        # Choose the attack type to use for all attacks in the sequence
        attack = self.ui.choose_action(attacks)
        if isinstance(attack, str) and attack == "q":
            return
        if attack is None or not isinstance(attack, BaseAttack):
            logger.warning("Invalid attack selected. Ending full attack")
            return

        # Get the legal targets for the action.
        valid_targets = self._get_legal_targets(player, attack)
        if not valid_targets:
            logger.warning(f"No valid targets for {attack.name}")
            return

        # Choose the initial target
        target = self.ui.choose_target(valid_targets, [])
        if not isinstance(target, Character):
            return

        # Execute the full attack sequence using the same attack type
        attacks_made = 0
        for attack_num in range(player.number_of_attacks):
            # Check if there are still valid opponents
            if not self.get_alive_opponents(player):
                break

            # If the current target is dead, ask for a new target
            if target.is_dead():
                # Get remaining legal targets
                remaining_targets = self._get_legal_targets(player, attack)
                if not remaining_targets:
                    break
                target = self.ui.choose_target(remaining_targets, [])

            if not isinstance(target, Character):
                return

            # Perform the attack
            attack.execute(player, target)
            attacks_made += 1

            # Add cooldown only once for the attack type
            if attack_num == 0:
                player.actions.add_cooldown(attack)

        # Mark the action class as used.
        player.actions.use_action_class(ActionClass.STANDARD)

    def ask_for_player_spell_cast(
        self, player: Character, spells: list[BaseSpell]
    ) -> bool:
        """Handles the player's choice to cast a spell.

        Args:
            player (Character): The player character casting the spell.
            spells (list[BaseSpell]): List of available spells for the player.

        Returns:
            bool: True if a spell was successfully cast, False otherwise.

        """
        while True:
            # Ask for the spell and the rank level.
            choice = self.ask_for_player_spell_and_rank(player, spells)
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
                variables = spell.spell_get_variables(player, rank)
                # Get the maximum number of targets if applicable.
                max_targets = spell.target_count(variables)
                # Get the targets for the spell.
                targets = self.ask_for_player_targets(player, spell, max_targets)
                if not targets:
                    logger.warning(f"No valid targets for {spell.name}")
                    break
                if isinstance(targets, str):
                    if targets == "q":
                        break
                    continue
                if not all(isinstance(t, Character) for t in targets):
                    continue
                for target in targets:
                    # Perform the action on the target.
                    spell.execute(
                        actor=player,
                        target=target,
                        rank=rank,
                    )
                # Remove the MIND cost from the player.
                player.use_mind(spell.mind_cost[rank])
                # Mark the action class as used.
                player.actions.use_action_class(spell.action_class)
                # Add the spell to the cooldowns if it has one.
                player.actions.add_cooldown(spell)
                return True
        return False

    def ask_for_player_spell_and_rank(
        self,
        player: Character,
        spells: list[BaseSpell],
    ) -> tuple[BaseSpell, int] | str | None:
        """
        Asks the player to choose a spell from their available spells.

        Args:
            player (Character): The player character choosing the spell.
            spells (list[BaseSpell]):
            List of available spells for the player.

        Returns:
            Optional[tuple[BaseSpell, int] | str]:
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
            rank = self.ui.choose_rank(player, spell)
            if rank == -1:
                return "q"
            return spell, rank
        return None

    def ask_for_player_target(
        self, player: Character, action: BaseAction
    ) -> Character | str | None:
        """Asks the player to choose a target for the given action.

        Args:
            player (Character): The player character choosing the target.
            action (BaseAction): The action for which to choose a target.

        Returns:
            Optional[Character | str]: The chosen target, or None if no valid target was selected.

        """
        # Get the legal targets for the action.
        valid_targets = self._get_legal_targets(player, action)
        if not valid_targets:
            logger.warning(f"No valid targets for {action.name}")
            return None
        # Ask the player to choose a target.
        return self.ui.choose_target(valid_targets)

    def ask_for_player_targets(
        self, player: Character, action: BaseAction, max_targets: int
    ) -> list[Character] | str | None:
        """Asks the player to choose multiple targets for the given action.

        Args:
            player (Character): The player character choosing the targets.
            action (BaseAction): The action for which to choose targets.
            max_targets (int): The maximum number of targets to choose.

        Returns:
            Optional[list[Character] | str]: The chosen targets, or None if no valid targets were selected.

        """
        # Get the legal targets for the action.
        valid_targets = self._get_legal_targets(player, action)
        if len(valid_targets) == 0:
            logger.warning(f"No valid targets for {action.name}")
            return None
        if max_targets <= 0:
            logger.warning(f"Invalid maximum number of targets: {max_targets}")
            return None
        if max_targets == 1 or len(valid_targets) == 1:
            target = self.ask_for_player_target(player, action)
            if target is None:
                logger.warning(f"No valid target for {action.name}")
                return None
            if isinstance(target, str):
                return target
            return [target]
        # Ask the player to choose multiple targets.
        return self.ui.choose_targets(valid_targets, max_targets)

    def pre_combat_phase(self) -> None:
        """
        Handles the pre-combat phase where players can prepare for combat.
        """
        crule(":hourglass_done: Pre-Combat Phase", style="blue")

        alive_players = self.get_alive_participants(CharacterType.PLAYER)
        for player in alive_players:
            cprint(f"[bold cyan]Pre-combat actions for {player.name}:[/]")

            targets = self.get_alive_friendlies(player)

            while True:
                for ally in targets:
                    # Show full details for healing phase (allies show AC)
                    cprint(
                        ally.display.get_status_line(
                            show_numbers=True,
                            show_bars=True,
                            show_ac=True,
                        )
                    )
                abilities: list[BaseAction] = []
                spells: list[BaseSpell] = []

                # Get the list of buff spells/abilities.
                abilities.extend(
                    [
                        a
                        for a in player.actions.abilities.values()
                        if a.category == ActionCategory.BUFF
                    ]
                )
                spells.extend(
                    [
                        s
                        for s in player.actions.spells.values()
                        if s.category == ActionCategory.BUFF
                    ]
                )

                # If someone needs healing, add healing spells/abilities.
                if any(t.stats.hp < t.HP_MAX for t in targets):
                    abilities.extend(
                        [
                            a
                            for a in player.actions.abilities.values()
                            if a.category == ActionCategory.HEALING
                        ]
                    )
                    spells.extend(
                        [
                            s
                            for s in player.actions.spells.values()
                            if s.category == ActionCategory.HEALING
                        ]
                    )

                # Main action selection menu.
                submenus = []
                if spells:
                    submenus.append("Cast a Spell")

                # Player selects an action or submenu option.
                choice = self.ui.choose_action(abilities, submenus, "Skip")
                if choice is None or (isinstance(choice, str) and choice == "q"):
                    break
                # If the action is a BaseSpell, we need to handle it differently.
                if choice == "Cast a Spell":
                    self.ask_for_player_spell_cast(player, spells)

    def post_combat_phase(self) -> None:
        """
        Handles the post-combat phase where players can heal friendly
        characters.
        """
        crule(":hourglass_done: Post-Combat Healing", style="green")

        alive_players = self.get_alive_participants(CharacterType.PLAYER)
        for player in alive_players:
            cprint(f"[bold green]Post-combat healing for {player.name}:[/]")

            targets = self.get_alive_friendlies(player)

            abilities: list[BaseAction]
            spells: list[BaseSpell]

            while True:

                for ally in targets:
                    # Show full details for healing phase (allies show AC)
                    cprint(
                        ally.display.get_status_line(
                            show_numbers=True,
                            show_bars=True,
                            show_ac=True,
                        )
                    )

                # If someone needs healing, add healing spells/abilities.
                if not any(t.stats.hp < t.HP_MAX for t in targets):
                    cprint("[bold green]All allies are at full health![/]")

                abilities = [
                    a
                    for a in player.actions.abilities.values()
                    if a.category == ActionCategory.HEALING
                ]
                spells = [
                    s
                    for s in player.actions.spells.values()
                    if s.category == ActionCategory.HEALING
                ]

                # Main action selection menu.
                submenus = []
                if spells:
                    submenus.append("Cast a Spell")

                # Player selects an action or submenu option.
                choice = self.ui.choose_action(abilities, submenus, "Skip")
                if choice is None or (isinstance(choice, str) and choice == "q"):
                    break
                # If the action is a BaseSpell, we need to handle it differently.
                if choice == "Cast a Spell":
                    self.ask_for_player_spell_cast(player, spells)

    def final_report(self) -> None:
        """Generates the final battle report after combat ends."""
        crule("📊  Final Battle Report", style="bold blue")
        # Show all alive players
        alive_players = self.get_alive_participants(CharacterType.PLAYER)
        for player in alive_players:
            cprint(
                player.display.get_status_line(
                    show_numbers=True,
                    show_bars=True,
                    show_ac=True,
                )
            )
        # Allies get full display too in final report
        for ally in self.get_alive_participants():
            if ally.char_type == CharacterType.ALLY and ally not in alive_players:
                cprint(
                    ally.display.get_status_line(
                        show_numbers=True,
                        show_bars=True,
                        show_ac=True,
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

    def execute_npc_action(self, npc: Character) -> None:
        """
        Executes the best action for an NPC based on score evaluation.

        Args:
            npc (Character): The NPC whose action is being executed.

        """
        allies = self.get_alive_friendlies(npc)
        enemies = self.get_alive_opponents(npc)

        # Choose the best action using score-based evaluation
        best_action = self._choose_best_action(npc, allies, enemies)

        # Execute the best action if one was found
        if best_action:
            best_action()
        else:
            cprint(f"    {npc.name} has no available actions this turn.")

    def _choose_best_action(
        self,
        npc: Character,
        allies: list[Character],
        enemies: list[Character],
    ) -> Callable[[], None] | None:
        """
        Evaluates all possible actions for an NPC and returns the best one by
        score.

        Args:
            npc (Character):
                The NPC making the decision.
            allies (list[Character]):
                List of friendly characters.
            enemies (list[Character]):
                List of enemy characters.

        Returns:
            Callable[[], None] | None:
                A function that executes the best action, or None if no action
                is available.
        """
        from actions.abilities.ability_buff import AbilityBuff
        from actions.abilities.ability_debuff import AbilityDebuff
        from actions.abilities.ability_heal import AbilityHeal
        from actions.abilities.ability_offensive import AbilityOffensive
        from actions.spells.spell_buff import SpellBuff
        from actions.spells.spell_debuff import SpellDebuff
        from actions.spells.spell_heal import SpellHeal
        from actions.spells.spell_offensive import SpellOffensive
        from actions.attacks.weapon_attack import WeaponAttack

        best_score = -1
        best_action: Callable[[], None] | None = None

        # Helper functions for action execution
        def execute_healing_spell():
            self._execute_spell_action(npc, healing_spell)

        def execute_healing_ability():
            self._execute_ability_action(npc, healing_ability)

        def execute_buff_spell():
            self._execute_spell_action(npc, buff_spell)

        def execute_buff_ability():
            self._execute_ability_action(npc, buff_ability)

        def execute_debuff_spell():
            self._execute_spell_action(npc, debuff_spell)

        def execute_debuff_ability():
            self._execute_ability_action(npc, debuff_ability)

        def execute_offensive_spell():
            self._execute_spell_action(npc, offensive_spell)

        def execute_offensive_ability():
            self._execute_ability_action(npc, offensive_ability)

        def execute_weapon_attack():
            self._execute_weapon_attack(npc, weapon_attack_selection, enemies)

        def execute_natural_attack():
            self._execute_natural_attack(npc, natural_attack_selection, enemies)

        # Evaluate healing actions
        healing_spell = choose_best_healing_spell_action(
            source=npc, allies=allies, spells=get_actions_by_type(npc, SpellHeal)
        )
        if healing_spell and healing_spell.score > best_score:
            best_score = healing_spell.score
            best_action = execute_healing_spell

        healing_ability = choose_best_healing_ability_action(
            source=npc, allies=allies, abilities=get_actions_by_type(npc, AbilityHeal)
        )
        if healing_ability and healing_ability.score > best_score:
            best_score = healing_ability.score
            best_action = execute_healing_ability

        # Evaluate buff actions
        buff_spell = choose_best_buff_or_debuff_spell_action(
            source=npc, targets=allies, spells=get_actions_by_type(npc, SpellBuff)
        )
        if buff_spell and buff_spell.score > best_score:
            best_score = buff_spell.score
            best_action = execute_buff_spell

        buff_ability = choose_best_buff_or_debuff_ability_action(
            source=npc, targets=allies, abilities=get_actions_by_type(npc, AbilityBuff)
        )
        if buff_ability and buff_ability.score > best_score:
            best_score = buff_ability.score
            best_action = execute_buff_ability

        # Evaluate debuff actions
        debuff_spell = choose_best_buff_or_debuff_spell_action(
            source=npc, targets=enemies, spells=get_actions_by_type(npc, SpellDebuff)
        )
        if debuff_spell and debuff_spell.score > best_score:
            best_score = debuff_spell.score
            best_action = execute_debuff_spell

        debuff_ability = choose_best_buff_or_debuff_ability_action(
            source=npc,
            targets=enemies,
            abilities=get_actions_by_type(npc, AbilityDebuff),
        )
        if debuff_ability and debuff_ability.score > best_score:
            best_score = debuff_ability.score
            best_action = execute_debuff_ability

        # Evaluate offensive actions
        offensive_spell = choose_best_attack_spell_action(
            source=npc, enemies=enemies, spells=get_actions_by_type(npc, SpellOffensive)
        )
        if offensive_spell and offensive_spell.score > best_score:
            best_score = offensive_spell.score
            best_action = execute_offensive_spell

        offensive_ability = choose_best_offensive_ability_action(
            source=npc,
            enemies=enemies,
            abilities=get_actions_by_type(npc, AbilityOffensive),
        )
        if offensive_ability and offensive_ability.score > best_score:
            best_score = offensive_ability.score
            best_action = execute_offensive_ability

        # Evaluate weapon attacks
        weapon_attacks = get_actions_by_type(npc, WeaponAttack)
        if weapon_attacks:
            weapon_attack_selection = choose_best_base_attack_action(
                source=npc, enemies=enemies, base_attacks=weapon_attacks
            )
            if weapon_attack_selection and weapon_attack_selection.score > best_score:
                best_score = weapon_attack_selection.score
                best_action = execute_weapon_attack

        # Evaluate natural attacks
        natural_attacks = get_natural_attacks(npc)
        if natural_attacks:
            natural_attack_selection = choose_best_base_attack_action(
                source=npc, enemies=enemies, base_attacks=natural_attacks  # type: ignore
            )
            if natural_attack_selection and natural_attack_selection.score > best_score:
                best_score = natural_attack_selection.score
                best_action = execute_natural_attack

        return best_action

    def _execute_spell_action(self, npc: Character, spell_selection) -> None:
        """Execute a spell action from a SpellSelection."""
        for target in spell_selection.targets:
            spell_selection.spell.execute(
                actor=npc,
                target=target,
                rank=spell_selection.rank,
            )
        npc.actions.add_cooldown(spell_selection.spell)
        npc.actions.use_action_class(spell_selection.spell.action_class)
        npc.use_mind(spell_selection.mind_level)

    def _execute_ability_action(self, npc: Character, ability_selection) -> None:
        """Execute an ability action from an AbilitySelection."""
        for target in ability_selection.targets:
            ability_selection.ability.execute(
                actor=npc,
                target=target,
            )
        npc.actions.add_cooldown(ability_selection.ability)
        npc.actions.use_action_class(ability_selection.ability.action_class)

    def _execute_weapon_attack(
        self, npc: Character, attack_selection, enemies: list[Character]
    ) -> None:
        """Execute weapon attacks from an AttackSelection."""
        attacks_made = False
        for _ in range(npc.number_of_attacks):
            target = choose_best_target_for_attack(
                npc, attack_selection.attack, enemies
            )
            if target:
                attack_selection.attack.execute(npc, target)
                attacks_made = True
        if attacks_made:
            npc.actions.add_cooldown(attack_selection.attack)
            npc.actions.use_action_class(attack_selection.attack.action_class)

    def _execute_natural_attack(
        self, npc: Character, attack_selection, enemies: list[Character]
    ) -> None:
        """Execute natural attacks from an AttackSelection."""
        for (
            attack
        ) in attack_selection.targets:  # attack_selection.targets contains the attacks
            target = choose_best_target_for_attack(npc, attack, enemies)
            if target:
                attack.execute(npc, target)
                npc.actions.add_cooldown(attack)
                npc.actions.use_action_class(attack.action_class)

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
