from abc import abstractmethod
import json
from logging import debug, error
from rich.console import Console
from typing import Any, Optional

from damage import *
from effect import *
from utils import *
from constants import *
from damage import *

console = Console()


class BaseAction:
    def __init__(
        self, name: str, type: ActionType, category: ActionCategory, cooldown: int
    ):
        self.name: str = name
        self.type: ActionType = type
        self.category: ActionCategory = category
        self.cooldown: int = cooldown

    def execute(self, actor: Any, target: Any) -> bool:
        """Abstract method for executables.

        Args:
            actor (Any): The character performing the action.
            target (Any): The character targeted by the action.

        Returns:
            bool: True if the action was successfully executed, False otherwise.
        """
        ...

    def apply_effect(
        self,
        actor: Any,
        target: Any,
        effect: Optional[Effect],
        mind_level: Optional[int] = 0,
    ):
        """Applies an effect to a target character.

        Args:
            actor (Any): The character performing the action.
            target (Any): The character targeted by the action.
            effect (Effect): The effect to apply.
            mind_level (int, optional): The mind_cost level to use for the effect. Defaults to 0.
        """
        if effect:
            debug(f"Applying effect {effect.name} from {actor.name} to {target.name}.")
            # Apply the effect to the target.
            effect.apply(actor, target, mind_level)
            # Add the effect to the target's effects list.
            target.effect_manager.add_effect(actor, effect, mind_level)

    def apply_effect_and_log(
        self,
        actor: Any,
        target: Any,
        effect: Optional[Effect],
        mind_level: Optional[int] = 0,
    ) -> None:
        """
        Applies the effect to the target if alive, adds it to their effect manager,
        and logs the application message with color and emoji.
        """
        if effect and target.is_alive():
            self.apply_effect(actor, target, effect, mind_level)
            target_str = f"[{get_character_type_color(target.type)}]{target.name}[/]"
            effect_msg = f"        {get_effect_emoji(effect)} Effect "
            effect_msg += apply_effect_color(effect, effect.name)
            effect_msg += f" applied to {target_str}."
            console.print(effect_msg, markup=True)

    def roll_attack_with_crit(
        self, actor, attack_bonus_expr: str, bonus_list: list[str]
    ) -> Tuple[int, str, int]:
        expr = "1D20"
        if attack_bonus_expr:
            expr += f" + {attack_bonus_expr}"
        for bonus in bonus_list:
            expr += f" + {bonus}"
        total, desc, rolls = roll_and_describe(expr, actor)
        return total, desc, rolls[0] if rolls else 0

    def is_valid_target(self, actor: Any, target: Any) -> bool:
        """Checks if the target is valid for the action.

        Args:
            actor (Any): The character performing the action.
            target (Any): The character targeted by the action.

        Returns:
            bool: True if the target is valid, False otherwise.
        """
        return False

    def to_dict(self) -> dict[str, Any]:
        """Converts the action to a dictionary representation.

        Returns:
            dict: A dictionary containing the executable's data.
        """
        return {
            "class": self.__class__.__name__,
            "name": self.name,
            "type": self.type.name,
            "category": self.category.name,
            "cooldown": self.cooldown,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "BaseAction":
        """Creates an executable from a dictionary representation.

        Args:
            data (dict): The dictionary containing the executable's data.

        Returns:
            Executable: An instance of the executable.
        """
        if data.get("class") == "WeaponAttack":
            return WeaponAttack.from_dict(data)
        if data.get("class") == "SpellAttack":
            return SpellAttack.from_dict(data)
        if data.get("class") == "SpellHeal":
            return SpellHeal.from_dict(data)
        if data.get("class") == "SpellBuff":
            return SpellBuff.from_dict(data)
        if data.get("class") == "SpellDebuff":
            return SpellDebuff.from_dict(data)
        raise ValueError(f"Unknown action class: {data.get('class')}")


class WeaponAttack(BaseAction):
    def __init__(
        self,
        name: str,
        type: ActionType,
        cooldown: int,
        hands_required: int,
        attack_roll: str,
        damage: list[DamageComponent],
        effect: Optional[Effect] = None,
    ):
        super().__init__(name, type, ActionCategory.OFFENSIVE, cooldown)
        self.hands_required: int = hands_required
        self.attack_roll: str = attack_roll
        self.damage: list[DamageComponent] = damage
        self.effect: Optional[Effect] = effect

    def execute(self, actor: Any, target: Any):
        actor_str = apply_character_type_color(actor.type, actor.name)
        target_str = apply_character_type_color(target.type, target.name)

        debug(f"{actor.name} attempts a {self.name} on {target.name}.")

        # If the action has a cooldown, add it to the actor's cooldowns.
        assert not actor.is_on_cooldown(self), f"Action {self.name} is on cooldown."
        if self.cooldown > 0:
            actor.add_cooldown(self, self.cooldown)

        # --- Build & resolve attack roll ---

        # Roll the attack.
        attack_total, attack_roll_desc, d20_roll = self.roll_attack_with_crit(
            actor,
            self.attack_roll,
            actor.effect_manager.get_modifier(BonusType.ATTACK),
        )

        # Detect crit and fumble.
        is_crit = d20_roll == 20
        is_fumble = d20_roll == 1

        # --- Outcome: MISS ---

        if is_fumble:
            console.print(
                f"    ❌ {actor_str} attacks {target_str} with [bold]{self.name}[/]: "
                f"rolled ({attack_roll_desc}) [red]{attack_total}[/] vs AC [yellow]{target.AC}[/] — [red]fumble![/]",
                markup=True,
            )
            return True

        if attack_total < target.AC and not is_crit:
            console.print(
                f"    ❌ {actor_str} attacks {target_str} with [bold]{self.name}[/]: "
                f"rolled ({attack_roll_desc}) [red]{attack_total}[/] vs AC [yellow]{target.AC}[/] — [red]miss[/]",
                markup=True,
            )
            return True

        # --- Outcome: HIT ---

        # First roll the attack damage from the weapon.
        base_damage, base_damage_details = roll_damage_components_no_mind(
            actor, target, self.damage
        )

        # If it's a crit, double the base damage.
        if is_crit:
            base_damage *= 2

        # Then roll any additional damage from effects.
        bonus_damage, bonus_damage_details = roll_damage_components(
            actor, target, actor.effect_manager.get_damage_modifiers()
        )

        # Extend the total damage and details with bonus damage.
        total_damage = base_damage + bonus_damage
        damage_details = base_damage_details + bonus_damage_details

        console.print(
            (
                f"    🎯 {actor_str} attacks {target_str} with [bold]{self.name}[/]: "
                f"rolled ({attack_roll_desc}) {attack_total} vs AC [yellow]{target.AC}[/] — "
                f"[magenta]crit![/]"
                if is_crit
                else "[green]hit![/]"
            ),
            markup=True,
        )
        console.print(
            f"        {actor_str} deals {total_damage} total damage to {target_str} → "
            + " + ".join(damage_details),
            markup=True,
        )

        # Apply any effect.
        self.apply_effect_and_log(actor, target, self.effect)

        if not target.is_alive():
            console.print(
                f"        [bold red]{target_str} has been defeated![/]",
                markup=True,
            )

        return True

    def is_valid_target(self, actor: Any, target: Any) -> bool:
        """Checks if the target is valid for the action.

        Args:
            actor (Any): The character performing the action.
            target (Any): The character targeted by the action.

        Returns:
            bool: True if the target is valid, False otherwise.
        """
        # A target is valid if:
        # - It is not the actor itself.
        # - Both actor and target are alive.
        # - If the actor and the enemy are not both allies or enemies.
        if target == actor:
            return False
        if not actor.is_alive() or not target.is_alive():
            return False
        if not is_oponent(actor.type, target.type):
            return False
        return True

    def get_damage_expr(self, actor: Any) -> str:
        """Returns the damage expression with variables substituted.

        Args:
            actor (Any): The character performing the action.

        Returns:
            str: The damage expression with variables substituted.
        """
        return " + ".join(
            substitute_variables(component.damage_roll, actor)
            for component in self.damage
        )

    def get_min_damage(self, actor: Any) -> int:
        """Returns the minimum damage value for the attack.

        Args:
            actor (Any): The character performing the action.

        Returns:
            int: The minimum damage value for the attack.
        """
        return sum(
            parse_expr_and_assume_min_roll(
                substitute_variables(component.damage_roll, actor)
            )
            for component in self.damage
        )

    def get_max_damage(self, actor: Any) -> int:
        """Returns the maximum damage value for the attack.

        Args:
            actor (Any): The character performing the action.

        Returns:
            int: The maximum damage value for the attack.
        """
        return sum(
            parse_expr_and_assume_max_roll(
                substitute_variables(component.damage_roll, actor)
            )
            for component in self.damage
        )

    def to_dict(self) -> dict[str, Any]:
        # Get the base dictionary representation.
        data = super().to_dict()
        # Add specific fields for WeaponAttack
        data["hands_required"] = self.hands_required
        data["attack_roll"] = self.attack_roll
        data["damage"] = [component.to_dict() for component in self.damage]
        # Include the effect if it exists.
        if self.effect:
            data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "WeaponAttack":
        """
        Creates a WeaponAttack instance from a dictionary.
        Args:
            data (dict): Dictionary containing the action data.
        Returns:
            WeaponAttack: An instance of WeaponAttack.
        """
        return WeaponAttack(
            name=data["name"],
            type=ActionType[data["type"]],
            cooldown=data.get("cooldown", 0),
            hands_required=data["hands_required"],
            attack_roll=data["attack_roll"],
            damage=[DamageComponent.from_dict(comp) for comp in data["damage"]],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
        )


class Spell(BaseAction):
    def __init__(
        self,
        name: str,
        type: ActionType,
        cooldown: int,
        level: int,
        mind_cost: list[int],
        category: ActionCategory,
        multi_target_expr: str = "",
    ):
        super().__init__(name, type, category, cooldown)
        self.level: int = level
        self.mind_cost: list[int] = mind_cost
        self.multi_target_expr: str = multi_target_expr

    def is_single_target(self) -> bool:
        """Check if the spell is single-target.

        Returns:
            bool: True if single-target, False otherwise.
        """
        return not self.multi_target_expr or self.multi_target_expr.strip() == ""

    def target_count(self, actor: Any, mind_level: int) -> int:
        """Returns the number of targets this ability can affect.

        Args:
            actor (Any): The character casting the spell.
            mind_level (int): The mind_cost level to use for evaluation.

        Returns:
            int: The number of targets this ability can affect.
        """
        if self.multi_target_expr:
            # Evaluate the multi-target expression to get the number of targets.
            return evaluate_expression(self.multi_target_expr, actor, mind_level)
        return 1

    def execute(self, actor: Any, target: Any) -> bool:
        """Executes the spell.

        Args:
            actor (Any): The character casting the spell.
            target (Any): The character targeted by the spell.

        Returns:
            bool: True if the spell was successfully cast, False otherwise.
        """
        raise NotImplementedError("Spells must use the cast_spell method.")

    @abstractmethod
    def cast_spell(self, actor: Any, target: Any, mind_level: int) -> bool:
        """
        Abstract method for executing an action.

        Args:
            actor (Any): The character performing the action.
            target (Any): The character targeted by the action.

        Returns:
            bool: True if the action was successfully executed, False otherwise.
        """
        pass

    def to_dict(self) -> dict[str, Any]:
        """Converts the spell to a dictionary representation."""
        data = super().to_dict()
        # Add specific fields for Spell
        data["level"] = self.level
        data["mind_cost"] = self.mind_cost
        # Include the multi-target expression if it exists.
        if self.multi_target_expr:
            data["multi_target_expr"] = self.multi_target_expr
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Spell":
        """
        Creates a Spell instance from a dictionary.
        Args:
            data (dict): Dictionary containing the action data.
        Returns:
            Spell: An instance of Spell.
        """
        if data.get("class") == "SpellAttack":
            return SpellAttack.from_dict(data)
        if data.get("class") == "SpellHeal":
            return SpellHeal.from_dict(data)
        if data.get("class") == "SpellBuff":
            return SpellBuff.from_dict(data)
        if data.get("class") == "SpellDebuff":
            return SpellDebuff.from_dict(data)
        raise ValueError(f"Unknown spell class: {data.get('class')}")


class SpellAttack(Spell):
    def __init__(
        self,
        name: str,
        type: ActionType,
        cooldown: int,
        level: int,
        mind_cost: list[int],
        damage: list[DamageComponent],
        effect: Optional[Effect] = None,
        multi_target_expr: str = "",
    ):
        super().__init__(
            name,
            type,
            cooldown,
            level,
            mind_cost,
            ActionCategory.OFFENSIVE,
            multi_target_expr,
        )
        self.damage: list[DamageComponent] = damage
        self.effect: Optional[Effect] = effect

    def cast_spell(self, actor: Any, target: Any, mind_level: int) -> bool:
        """
        Executes a spell attack from the actor to the target with breakdown logs.
        """
        debug(f"{actor.name} attempts to cast {self.name} on {target.name}.")

        if actor.mind < mind_level:
            error(f"{actor.name} does not have enough mind_cost to cast {self.name}.")
            return False

        # If the action has a cooldown, add it to the actor's cooldowns.
        assert not actor.is_on_cooldown(self), "Action is on cooldown."
        if self.cooldown > 0:
            actor.add_cooldown(self, self.cooldown)

        actor_str = f"[{get_character_type_color(actor.type)}]{actor.name}[/]"
        target_str = f"[{get_character_type_color(target.type)}]{target.name}[/]"

        # --- Build and roll attack expression ---

        # Roll the attack.
        attack_total, attack_roll_desc, d20_roll = self.roll_attack_with_crit(
            actor,
            actor.get_spell_attack_bonus(self.level),
            actor.effect_manager.get_modifier(BonusType.ATTACK),
        )

        # Detect crit and fumble.
        is_crit = d20_roll == 20
        is_fumble = d20_roll == 1

        # --- Outcome: FUMBLE ---

        if is_fumble:
            console.print(
                f"    ❌ {actor_str} attacks {target_str} with [bold]{self.name}[/]: "
                f"rolled ({attack_roll_desc}) [red]{attack_total}[/] vs AC [yellow]{target.AC}[/] — [red]fumble![/]",
                markup=True,
            )
            return True

        # --- Outcome: MISS ---

        if attack_total < target.AC and not is_crit:
            console.print(
                f"    ❌ {actor_str} casts [bold]{self.name}[/] on {target_str}: "
                f"rolled ({attack_roll_desc}) [red]{attack_total}[/] vs AC [yellow]{target.AC}[/] — [red]miss[/]",
                markup=True,
            )
            return True

        # --- Outcome: HIT ---

        # Create a list of tuples with damage components and mind levels.
        damage_components = [(component, mind_level) for component in self.damage]

        # First roll the attack damage from the weapon.
        total_damage, damage_details = roll_damage_components(
            actor, target, damage_components
        )

        # Print the damage breakdown.
        console.print(
            f"    🎯 {actor_str} casts [bold]{self.name}[/] on {target_str}: "
            f"rolled ({attack_roll_desc}) [white]{attack_total}[/] vs AC [yellow]{target.AC}[/] — [green]hit![/]",
            markup=True,
        )
        console.print(
            f"        {actor_str} deals {total_damage} total damage to {target_str} → "
            + " + ".join(damage_details),
            markup=True,
        )

        # Apply any effect.
        self.apply_effect_and_log(actor, target, self.effect, mind_level)

        if not target.is_alive():
            console.print(
                f"        [bold red]{target_str} has been defeated![/]",
                markup=True,
            )
        return True

    def is_valid_target(self, actor: Any, target: Any) -> bool:
        """Checks if the target is valid for the action.

        Args:
            actor (Any): The character performing the action.
            target (Any): The character targeted by the action.

        Returns:
            bool: True if the target is valid, False otherwise.
        """
        # A target is valid if:
        # - It is not the actor itself.
        # - Both actor and target are alive.
        # - If the actor and the enemy are not both allies or enemies.
        if target == actor:
            return False
        if not actor.is_alive() or not target.is_alive():
            return False
        if not is_oponent(actor.type, target.type):
            return False
        return True

    def get_damage_expr(self, actor: Any, mind_level: Optional[int] = None) -> str:
        """Returns the damage expression with variables substituted.

        Args:
            actor (Any): The character casting the spell.
            mind_level (int, optional): The mind_cost level to use for evaluation. Defaults to None.

        Returns:
            str: The damage expression with variables substituted.
        """
        return " + ".join(
            substitute_variables(component.damage_roll, actor, mind_level)
            for component in self.damage
        )

    def get_min_damage(self, actor: Any, mind_level: Optional[int] = None) -> int:
        """Returns the minimum damage value for the spell.

        Args:
            actor (Any): The character casting the spell.
            mind_level (int, optional): The mind_cost level to use for evaluation. Defaults to None.

        Returns:
            int: The minimum damage value for the spell.
        """
        return sum(
            parse_expr_and_assume_min_roll(
                substitute_variables(component.damage_roll, actor, mind_level)
            )
            for component in self.damage
        )

    def get_max_damage(self, actor: Any, mind_level: Optional[int] = None) -> int:
        """Returns the maximum damage value for the spell.

        Args:
            actor (Any): The character casting the spell.
            mind_level (int, optional): The mind_cost level to use for evaluation. Defaults to None.

        Returns:
            int: The maximum damage value for the spell.
        """
        return sum(
            parse_expr_and_assume_max_roll(
                substitute_variables(component.damage_roll, actor, mind_level)
            )
            for component in self.damage
        )

    def to_dict(self) -> dict[str, Any]:
        """Converts the spell to a dictionary representation."""
        data = super().to_dict()
        # Add specific fields for SpellAttack
        data["damage"] = [component.to_dict() for component in self.damage]
        data["level"] = self.level
        # Include the effect if it exists.
        if self.effect:
            data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SpellAttack":
        """
        Creates a SpellAttack instance from a dictionary.
        Args:
            data (dict): Dictionary containing the action data.
        Returns:
            SpellAttack: An instance of SpellAttack.
        """
        return SpellAttack(
            name=data["name"],
            type=ActionType[data["type"]],
            cooldown=data.get("cooldown", 0),
            level=data["level"],
            mind_cost=data["mind_cost"],
            damage=[
                DamageComponent.from_dict(component) for component in data["damage"]
            ],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
            multi_target_expr=data.get("multi_target_expr", ""),
        )


class SpellHeal(Spell):
    def __init__(
        self,
        name: str,
        type: ActionType,
        cooldown: int,
        level: int,
        mind_cost: list[int],
        heal_roll: str,
        effect: Optional[Effect] = None,
        multi_target_expr: str = "",
    ):
        super().__init__(
            name,
            type,
            cooldown,
            level,
            mind_cost,
            ActionCategory.HEALING,
            multi_target_expr,
        )
        self.heal_roll: str = heal_roll
        self.effect: Optional[Effect] = effect

    def cast_spell(
        self, actor: Any, target: Any, mind_level: Optional[int] = None
    ) -> bool:
        """Casts a healing spell from the actor to the target.

        Args:
            actor (Any): The character casting the spell.
            target (Any): The character receiving the healing.
            mind_level (int, optional): The level of mind_cost to use for the spell. Defaults to -1.

        Returns:
            bool: True if the spell was cast successfully, False otherwise.
        """
        debug(
            f"{actor.name} attempts to cast {self.name} on {target.name}, expression {self.heal_roll}."
        )
        # Determine the mind_cost level to use.
        if actor.mind < mind_level:
            error(f"{actor.name} does not have enough mind_cost to cast {self.name}.")
            return False

        # If the action has a cooldown, add it to the actor's cooldowns.
        assert not actor.is_on_cooldown(self), "Action is on cooldown."
        if self.cooldown > 0:
            actor.add_cooldown(self, self.cooldown)

        # Prepare the actor and target strings for output.
        actor_str = f"[{get_character_type_color(actor.type)}]{actor.name}[/]"
        target_str = f"[{get_character_type_color(target.type)}]{target.name}[/]"

        # Compute the healing based on the mind_cost spent and roll
        heal_value, heal_desc, _ = roll_and_describe(self.heal_roll, actor, mind_level)

        # Apply healing to the target
        actual_healed = target.heal(heal_value)

        console.print(
            f"    ✳️ {actor_str} casts [bold]{self.name}[/] on {target_str}: "
            f"heals for [bold green]{actual_healed}[/] ([white]{heal_desc}[/]).",
            markup=True,
        )

        # Apply any effect.
        self.apply_effect_and_log(actor, target, self.effect, mind_level)

        return True

    def is_valid_target(self, actor: Any, target: Any) -> bool:
        """Checks if the target is valid for the action.

        Args:
            actor (Any): The character performing the action.
            target (Any): The character targeted by the action.

        Returns:
            bool: True if the target is valid, False otherwise.
        """
        # A target is valid if:
        # - It is not the actor itself.
        # - Both actor and target are alive.
        # - If the actor and the enemy are both allies or enemies.
        if not actor.is_alive() or not target.is_alive():
            return False
        if is_oponent(actor.type, target.type):
            return False
        return True

    def get_heal_expr(self, actor: Any, mind_level: Optional[int] = None) -> str:
        """Returns the healing expression with variables substituted.
        Args:
            actor (Any): The character casting the spell.
            mind_level (int, optional): The mind_cost level to use for evaluation. Defaults to None.
        Returns:
            str: The healing expression with variables substituted.
        """
        return substitute_variables(self.heal_roll, actor, mind_level)

    def get_min_heal(self, actor: Any, mind_level: Optional[int] = None) -> int:
        """Returns the minimum healing value for the spell.
        Args:
            actor (Any): The character casting the spell.
            mind_level (int, optional): The mind_cost level to use for evaluation. Defaults to None.
        Returns:
            int: The minimum healing value for the spell.
        """
        return parse_expr_and_assume_min_roll(
            substitute_variables(self.heal_roll, actor, mind_level)
        )

    def get_max_heal(self, actor: Any, mind_level: Optional[int] = None) -> int:
        """Returns the maximum healing value for the spell.
        Args:
            actor (Any): The character casting the spell.
            mind_level (int, optional): The mind_cost level to use for evaluation. Defaults to None.
        Returns:
            int: The maximum healing value for the spell.
        """
        return parse_expr_and_assume_max_roll(
            substitute_variables(self.heal_roll, actor, mind_level)
        )

    def to_dict(self):
        """Converts the spell to a dictionary representation."""
        data = super().to_dict()
        # Add specific fields for SpellHeal
        data["heal_roll"] = self.heal_roll
        # Include the effect if it exists.
        if self.effect:
            data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SpellHeal":
        """
        Creates a SpellHeal instance from a dictionary.
        Args:
            data (dict): Dictionary containing the action data.
        Returns:
            SpellHeal: An instance of SpellHeal.
        """
        return SpellHeal(
            name=data["name"],
            type=ActionType[data["type"]],
            cooldown=data.get("cooldown", 0),
            level=data["level"],
            mind_cost=data["mind_cost"],
            heal_roll=data["heal_roll"],
            effect=Effect.from_dict(data["effect"]) if data.get("effect") else None,
            multi_target_expr=data.get("multi_target_expr", ""),
        )


class SpellBuff(Spell):
    def __init__(
        self,
        name: str,
        type: ActionType,
        cooldown: int,
        level: int,
        mind_cost: list[int],
        effect: Buff,
        multi_target_expr: str = "",
    ):
        super().__init__(
            name,
            type,
            cooldown,
            level,
            mind_cost,
            ActionCategory.BUFF,
            multi_target_expr,
        )
        self.effect: Buff = effect
        # Ensure the effect is provided.
        assert self.effect is not None, "Effect must be provided for SpellBuff."

    def cast_spell(
        self, actor: Any, target: Any, mind_level: Optional[int] = None
    ) -> bool:
        """
        Executes a buff spell, applying a beneficial effect to the target.
        Uses mind_cost to cast the spell.
        """
        debug(f"{actor.name} attempts to cast {self.name} on {target.name}.")

        # Determine the mind_cost level to use.
        if actor.mind < mind_level:
            error(f"{actor.name} does not have enough mind_cost to cast {self.name}.")
            return False

        # If the action has a cooldown, add it to the actor's cooldowns.
        assert not actor.is_on_cooldown(self), "Action is on cooldown."
        if self.cooldown > 0:
            actor.add_cooldown(self, self.cooldown)

        # Prepare the actor and target strings for output.
        actor_str = f"[{get_character_type_color(actor.type)}]{actor.name}[/]"
        target_str = f"[{get_character_type_color(target.type)}]{target.name}[/]"

        # Informational log
        console.print(
            f"    {actor_str} casts [bold]{self.name}[/] on {target_str}.",
            markup=True,
        )

        # Apply any effect.
        self.apply_effect_and_log(actor, target, self.effect, mind_level)

        return True

    def is_valid_target(self, actor: Any, target: Any) -> bool:
        """Checks if the target is valid for the action.

        Args:
            actor (Any): The character performing the action.
            target (Any): The character targeted by the action.

        Returns:
            bool: True if the target is valid, False otherwise.
        """
        # A target is valid if:
        # - It is not the actor itself.
        # - Both actor and target are alive.
        # - If the actor and the enemy are both allies or enemies.
        if not actor.is_alive() or not target.is_alive():
            return False
        if is_oponent(actor.type, target.type):
            return False
        return True

    def get_modifier_expressions(
        self, actor: Any, mind_level: Optional[int] = None
    ) -> dict[BonusType, str]:
        """Returns the dictionary of modifier expressions for the buff.
        Args:
            actor (Any): The character casting the spell.
            mind_level (int, optional): The mind_cost level to use for evaluation. Defaults to None.
        Returns:
            dict[BonusType, str]: A dictionary mapping BonusType to expressions with variables substituted.
        """
        expressions: dict[BonusType, str] = {}
        for bonus_type, value in self.effect.modifiers.items():
            if isinstance(value, DamageComponent):
                expressions[bonus_type] = substitute_variables(
                    value.damage_roll, actor, mind_level
                )
            elif isinstance(value, str):
                # If the value is a string, substitute variables directly.
                expressions[bonus_type] = substitute_variables(value, actor, mind_level)
            else:
                expressions[bonus_type] = value
        return expressions

    def to_dict(self):
        """Converts the spell to a dictionary representation."""
        data = super().to_dict()
        # Add specific fields for SpellBuff
        data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SpellBuff":
        """
        Creates a SpellBuff instance from a dictionary.
        Args:
            data (dict): Dictionary containing the action data.
        Returns:
            SpellBuff: An instance of SpellBuff.
        """
        return SpellBuff(
            name=data["name"],
            type=ActionType[data["type"]],
            cooldown=data.get("cooldown", 0),
            level=data["level"],
            mind_cost=data["mind_cost"],
            effect=Buff.from_dict(data["effect"]),
            multi_target_expr=data.get("multi_target_expr", ""),
        )


class SpellDebuff(Spell):
    def __init__(
        self,
        name: str,
        type: ActionType,
        cooldown: int,
        level: int,
        mind_cost: list[int],
        effect: Debuff,
        multi_target_expr: str = "",
    ):
        super().__init__(
            name,
            type,
            cooldown,
            level,
            mind_cost,
            ActionCategory.DEBUFF,
            multi_target_expr,
        )
        self.effect: Debuff = effect
        # Ensure the effect is provided.
        assert self.effect is not None, "Effect must be provided for SpellDebuff."

    def cast_spell(
        self, actor: Any, target: Any, mind_level: Optional[int] = None
    ) -> bool:
        """
        Executes a debuff spell, applying a detrimental effect to the target.
        Uses mind_cost to cast the spell.
        """
        debug(f"{actor.name} attempts to cast {self.name} on {target.name}.")

        # Determine the mind_cost level to use.
        if actor.mind < mind_level:
            error(f"{actor.name} does not have enough mind_cost to cast {self.name}.")
            return False

        # If the action has a cooldown, add it to the actor's cooldowns.
        assert not actor.is_on_cooldown(self), "Action is on cooldown."
        if self.cooldown > 0:
            actor.add_cooldown(self, self.cooldown)

        # Prepare the actor and target strings for output.
        actor_str = f"[{get_character_type_color(actor.type)}]{actor.name}[/]"
        target_str = f"[{get_character_type_color(target.type)}]{target.name}[/]"

        console.print(
            f"    {actor_str} casts [bold]{self.name}[/] on {target_str}.",
            markup=True,
        )

        # Apply any effect.
        self.apply_effect_and_log(actor, target, self.effect, mind_level)

        return True

    def is_valid_target(self, actor: Any, target: Any) -> bool:
        """Checks if the target is valid for the action.

        Args:
            actor (Any): The character performing the action.
            target (Any): The character targeted by the action.

        Returns:
            bool: True if the target is valid, False otherwise.
        """
        # A target is valid if:
        # - It is not the actor itself.
        # - Both actor and target are alive.
        # - If the actor and the enemy are not both allies or enemies.
        if target == actor:
            return False
        if not actor.is_alive() or not target.is_alive():
            return False
        if not is_oponent(actor.type, target.type):
            return False
        return True

    def get_modifier_expressions(
        self, actor: Any, mind_level: Optional[int] = None
    ) -> dict[BonusType, str]:
        """Returns the dictionary of modifier expressions for the buff.
        Args:
            actor (Any): The character casting the spell.
            mind_level (int, optional): The mind_cost level to use for evaluation. Defaults to None.
        Returns:
            dict[BonusType, str]: A dictionary mapping BonusType to expressions with variables substituted.
        """
        expressions: dict[BonusType, str] = {}
        for bonus_type, expr in self.effect.modifiers.items():
            expressions[bonus_type] = substitute_variables(expr, actor, mind_level)
        return expressions

    def to_dict(self):
        """Converts the spell to a dictionary representation."""
        data = super().to_dict()
        # Add specific fields for SpellDebuff
        data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SpellDebuff":
        """
        Creates a SpellDebuff instance from a dictionary.
        Args:
            data (dict): Dictionary containing the action data.
        Returns:
            SpellDebuff: An instance of SpellDebuff.
        """
        return SpellDebuff(
            name=data["name"],
            type=ActionType[data["type"]],
            cooldown=data.get("cooldown", 0),
            level=data["level"],
            mind_cost=data["mind_cost"],
            effect=Debuff.from_dict(data["effect"]),
            multi_target_expr=data.get("multi_target_expr", ""),
        )


def load_actions(filename: str) -> dict[str, BaseAction]:
    """Loads an action from a dictionary.

    Args:
        data (dict): The dictionary containing the action data.

    Returns:
        BaseAction: The loaded action.
    """
    actions: dict[str, BaseAction] = {}
    with open(filename, "r") as f:
        action_data = json.load(f)
        for action_data in action_data:
            action = BaseAction.from_dict(action_data)
            actions[action.name] = action
    return actions
