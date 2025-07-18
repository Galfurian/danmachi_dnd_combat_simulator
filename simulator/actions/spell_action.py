from abc import abstractmethod
from logging import debug, error
from typing import Any, Optional

from combat.damage import *
from core.utils import *
from core.constants import *
from actions.base_action import *
from effects.effect import *


class Spell(BaseAction):
    def __init__(
        self,
        name: str,
        type: ActionType,
        description: str,
        cooldown: int,
        maximum_uses: int,
        level: int,
        mind_cost: list[int],
        category: ActionCategory,
        multi_target_expr: str = "",
    ):
        super().__init__(name, type, category, description, cooldown, maximum_uses)
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
            variables = actor.get_expression_variables()
            variables["MIND"] = mind_level
            # Evaluate the multi-target expression to get the number of targets.
            return evaluate_expression(self.multi_target_expr, variables)
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


class SpellAttack(Spell):
    def __init__(
        self,
        name: str,
        type: ActionType,
        description: str,
        cooldown: int,
        maximum_uses: int,
        level: int,
        mind_cost: list[int],
        damage: list[DamageComponent],
        effect: Optional[Effect] = None,
        multi_target_expr: str = "",
    ):
        super().__init__(
            name,
            type,
            description,
            cooldown,
            maximum_uses,
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

        actor_str = f"[{get_character_type_color(actor.type)}]{actor.name}[/]"
        target_str = f"[{get_character_type_color(target.type)}]{target.name}[/]"

        # --- Build and roll attack expression ---

        # Get the spell attack bonus for the actor.
        spell_attack_bonus = actor.get_spell_attack_bonus(self.level)

        # Get the attack modifier from the actor's effect manager.
        attack_modifier = actor.effect_manager.get_modifier(BonusType.ATTACK)

        # Roll the attack.
        attack_total, attack_roll_desc, d20_roll = self.roll_attack_with_crit(
            actor, spell_attack_bonus, attack_modifier
        )

        # Detect crit and fumble.
        is_crit = d20_roll == 20
        is_fumble = d20_roll == 1

        msg = f"    🎯 {actor_str} casts [bold]{self.name}[/] on {target_str}"

        # --- Outcome: FUMBLE ---

        if is_fumble:
            if GLOBAL_VERBOSE_LEVEL >= 1:
                msg += f" rolled ({attack_roll_desc}) [magenta]{attack_total}[/] vs AC [yellow]{target.AC}[/]"
            msg += " and [magenta]fumble![/]"
            cprint(msg)
            return True

        # --- Outcome: MISS ---

        if attack_total < target.AC and not is_crit:
            if GLOBAL_VERBOSE_LEVEL >= 1:
                msg += f" rolled ({attack_roll_desc}) [red]{attack_total}[/] vs AC [yellow]{target.AC}[/]"
            msg += " and [red]miss![/]"
            cprint(msg)
            return True

        # --- Outcome: HIT ---

        # Create a list of tuples with damage components and mind levels.
        damage_components = [(component, mind_level) for component in self.damage]

        # First roll the attack damage from the attack.
        total_damage, damage_details = roll_damage_components(
            actor, target, damage_components
        )

        # Check if the target is still alive after the attack.
        is_dead = not target.is_alive()

        # Print the damage breakdown.
        if GLOBAL_VERBOSE_LEVEL == 0:
            msg += f" dealing {total_damage} damage"
            if is_dead:
                msg += f" defeating {target_str}"
            elif self.effect and self.apply_effect(actor, target, self.effect):
                msg += f" and applying the effect "
                msg += f"[{get_effect_color(self.effect)}]{self.effect.name}[/]"
            msg += "."
        elif GLOBAL_VERBOSE_LEVEL >= 1:
            msg += f" rolled ({attack_roll_desc}) {attack_total} vs AC [yellow]{target.AC}[/] → "
            msg += "[magenta]crit![/]\n" if is_crit else "[green]hit![/]\n"
            msg += f"        Dealing {total_damage} damage to {target_str} → "
            msg += " + ".join(damage_details) + ".\n"
            if is_dead:
                msg += f"        {target_str} is defeated."
            elif self.effect and self.apply_effect(actor, target, self.effect):
                msg += f"        {target_str} is affected by "
                msg += f"[{get_effect_color(self.effect)}]{self.effect.name}[/]."
        cprint(msg)

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

    def get_damage_expr(self, actor: Any, mind_level: Optional[int] = 1) -> str:
        """Returns the damage expression with variables substituted.

        Args:
            actor (Any): The character casting the spell.
            mind_level (int, optional): The mind_cost level to use for evaluation. Defaults to 1.

        Returns:
            str: The damage expression with variables substituted.
        """
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return " + ".join(
            substitute_variables(component.damage_roll, variables)
            for component in self.damage
        )

    def get_min_damage(self, actor: Any, mind_level: Optional[int] = 1) -> int:
        """Returns the minimum damage value for the spell.

        Args:
            actor (Any): The character casting the spell.
            mind_level (int, optional): The mind_cost level to use for evaluation. Defaults to 1.

        Returns:
            int: The minimum damage value for the spell.
        """
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return sum(
            parse_expr_and_assume_min_roll(
                substitute_variables(
                    component.damage_roll,
                    variables,
                )
            )
            for component in self.damage
        )

    def get_max_damage(self, actor: Any, mind_level: Optional[int] = 1) -> int:
        """Returns the maximum damage value for the spell.

        Args:
            actor (Any): The character casting the spell.
            mind_level (int, optional): The mind_cost level to use for evaluation. Defaults to 1.

        Returns:
            int: The maximum damage value for the spell.
        """
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return sum(
            parse_expr_and_assume_max_roll(
                substitute_variables(component.damage_roll, variables)
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
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
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
        description: str,
        cooldown: int,
        maximum_uses: int,
        level: int,
        mind_cost: list[int],
        heal_roll: str,
        effect: Optional[Effect] = None,
        multi_target_expr: str = "",
    ):
        super().__init__(
            name,
            type,
            description,
            cooldown,
            maximum_uses,
            level,
            mind_cost,
            ActionCategory.HEALING,
            multi_target_expr,
        )
        self.heal_roll: str = heal_roll
        self.effect: Optional[Effect] = effect

    def cast_spell(
        self, actor: Any, target: Any, mind_level: Optional[int] = 1
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

        # Prepare the actor and target strings for output.
        actor_str = f"[{get_character_type_color(actor.type)}]{actor.name}[/]"
        target_str = f"[{get_character_type_color(target.type)}]{target.name}[/]"

        # Compute the healing based on the mind_cost spent and roll
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        heal_value, heal_desc, _ = roll_and_describe(self.heal_roll, variables)

        # Apply healing to the target
        actual_healed = target.heal(heal_value)

        msg = f"    ✳️ {actor_str} casts [bold]{self.name}[/] on {target_str}"
        msg += f" healing for [bold green]{actual_healed}[/]"
        if GLOBAL_VERBOSE_LEVEL >= 1:
            msg += f" ({heal_desc})"
        if self.effect:
            if self.apply_effect(actor, target, self.effect):
                msg += f" and applying "
            else:
                msg += f" but failing to apply "
            msg += f"[{get_effect_color(self.effect)}]{self.effect.name}[/]"
        msg += f"."
        cprint(msg)

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
        # - The target is not at full health.
        if not actor.is_alive() or not target.is_alive():
            return False
        if is_oponent(actor.type, target.type):
            return False
        if target.hp >= target.HP_MAX:
            return False
        return True

    def get_heal_expr(self, actor: Any, mind_level: Optional[int] = 1) -> str:
        """Returns the healing expression with variables substituted.
        Args:
            actor (Any): The character casting the spell.
            mind_level (int, optional): The mind_cost level to use for evaluation. Defaults to 1.
        Returns:
            str: The healing expression with variables substituted.
        """
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return simplify_expression(self.heal_roll, variables)

    def get_min_heal(self, actor: Any, mind_level: Optional[int] = 1) -> int:
        """Returns the minimum healing value for the spell.
        Args:
            actor (Any): The character casting the spell.
            mind_level (int, optional): The mind_cost level to use for evaluation. Defaults to 1.
        Returns:
            int: The minimum healing value for the spell.
        """
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return parse_expr_and_assume_min_roll(
            substitute_variables(self.heal_roll, variables)
        )

    def get_max_heal(self, actor: Any, mind_level: Optional[int] = 1) -> int:
        """Returns the maximum healing value for the spell.
        Args:
            actor (Any): The character casting the spell.
            mind_level (int, optional): The mind_cost level to use for evaluation. Defaults to 1.
        Returns:
            int: The maximum healing value for the spell.
        """
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        return parse_expr_and_assume_max_roll(
            substitute_variables(self.heal_roll, variables)
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
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
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
        description: str,
        cooldown: int,
        maximum_uses: int,
        level: int,
        mind_cost: list[int],
        effect: Buff,
        multi_target_expr: str = "",
    ):
        super().__init__(
            name,
            type,
            description,
            cooldown,
            maximum_uses,
            level,
            mind_cost,
            ActionCategory.BUFF,
            multi_target_expr,
        )
        self.effect: Buff = effect
        # Ensure the effect is provided.
        assert self.effect is not None, "Effect must be provided for SpellBuff."

    def cast_spell(
        self, actor: Any, target: Any, mind_level: Optional[int] = 1
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

        # Prepare the actor and target strings for output.
        actor_str = f"[{get_character_type_color(actor.type)}]{actor.name}[/]"
        target_str = f"[{get_character_type_color(target.type)}]{target.name}[/]"

        # Informational log.
        msg = f"    {actor_str} casts [bold]{self.name}[/] on {target_str} "
        if self.effect:
            if self.apply_effect(actor, target, self.effect, mind_level):
                msg += f"applying "
            else:
                msg += f"failing to apply "
            msg += f"[{get_effect_color(self.effect)}]{self.effect.name}[/]"
        msg += "."

        cprint(msg)

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
        self, actor: Any, mind_level: Optional[int] = 1
    ) -> dict[BonusType, str]:
        """Returns the dictionary of modifier expressions for the buff.
        Args:
            actor (Any): The character casting the spell.
            mind_level (int, optional): The mind_cost level to use for evaluation. Defaults to 1.
        Returns:
            dict[BonusType, str]: A dictionary mapping BonusType to expressions with variables substituted.
        """
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        expressions: dict[BonusType, str] = {}
        for modifier in self.effect.modifiers:
            bonus_type = modifier.bonus_type
            value = modifier.value
            if isinstance(value, DamageComponent):
                expressions[bonus_type] = substitute_variables(
                    value.damage_roll, variables
                )
            elif isinstance(value, str):
                # If the value is a string, substitute variables directly.
                expressions[bonus_type] = substitute_variables(value, variables)
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
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
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
        description: str,
        cooldown: int,
        maximum_uses: int,
        level: int,
        mind_cost: list[int],
        effect: Debuff,
        multi_target_expr: str = "",
    ):
        super().__init__(
            name,
            type,
            description,
            cooldown,
            maximum_uses,
            level,
            mind_cost,
            ActionCategory.DEBUFF,
            multi_target_expr,
        )
        self.effect: Debuff = effect
        # Ensure the effect is provided.
        assert self.effect is not None, "Effect must be provided for SpellDebuff."

    def cast_spell(
        self, actor: Any, target: Any, mind_level: Optional[int] = 1
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

        # Prepare the actor and target strings for output.
        actor_str = f"[{get_character_type_color(actor.type)}]{actor.name}[/]"
        target_str = f"[{get_character_type_color(target.type)}]{target.name}[/]"

        # Informational log.
        msg = f"    {actor_str} casts [bold]{self.name}[/] on {target_str} "
        if self.effect:
            if self.apply_effect(actor, target, self.effect, mind_level):
                msg += f"applying "
            else:
                msg += f"failing to apply "
            msg += f"[{get_effect_color(self.effect)}]{self.effect.name}[/]"
        msg += "."

        cprint(msg)

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
        self, actor: Any, mind_level: Optional[int] = 1
    ) -> dict[BonusType, str]:
        """Returns the dictionary of modifier expressions for the buff.
        Args:
            actor (Any): The character casting the spell.
            mind_level (int, optional): The mind_cost level to use for evaluation. Defaults to 1.
        Returns:
            dict[BonusType, str]: A dictionary mapping BonusType to expressions with variables substituted.
        """
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        expressions: dict[BonusType, str] = {}
        for modifier in self.effect.modifiers:
            bonus_type = modifier.bonus_type
            expr = modifier.value
            expressions[bonus_type] = substitute_variables(expr, variables)
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
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 0),
            maximum_uses=data.get("maximum_uses", -1),
            level=data["level"],
            mind_cost=data["mind_cost"],
            effect=Debuff.from_dict(data["effect"]),
            multi_target_expr=data.get("multi_target_expr", ""),
        )


def from_dict_spell(data: dict[str, Any]) -> Optional[Spell]:
    """Factory function to create a Spell instance from a dictionary."""
    if data["class"] == "SpellAttack":
        return SpellAttack.from_dict(data)
    elif data["class"] == "SpellHeal":
        return SpellHeal.from_dict(data)
    elif data["class"] == "SpellBuff":
        return SpellBuff.from_dict(data)
    elif data["class"] == "SpellDebuff":
        return SpellDebuff.from_dict(data)
    return None
