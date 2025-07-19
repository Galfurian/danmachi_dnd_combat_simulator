from abc import abstractmethod
from logging import debug, error
from typing import Any, Optional

from actions.base_action import BaseAction
from combat.damage import DamageComponent, roll_damage_components
from core.constants import (
    ActionCategory,
    ActionType,
    BonusType,
    GLOBAL_VERBOSE_LEVEL,
    get_character_type_color,
    get_effect_color,
    is_oponent,
)
from core.error_handling import log_error, log_warning, log_critical
from core.utils import (
    evaluate_expression,
    parse_expr_and_assume_max_roll,
    parse_expr_and_assume_min_roll,
    roll_and_describe,
    simplify_expression,
    substitute_variables,
    cprint,
)
from effects.effect import Buff, Debuff, Effect, ModifierEffect


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
        target_expr: str = "",
        requires_concentration: bool = False,
        target_restrictions: list[str] | None = None,
    ):
        try:
            super().__init__(
                name,
                type,
                category,
                description,
                cooldown,
                maximum_uses,
                target_restrictions,
            )

            # Validate level
            if not isinstance(level, int) or level < 0:
                log_error(
                    f"Spell {name} level must be non-negative integer, got: {level}",
                    {"name": name, "level": level},
                )
                level = max(0, int(level) if isinstance(level, (int, float)) else 0)

            # Validate mind_cost
            if not isinstance(mind_cost, list):
                log_error(
                    f"Spell {name} mind_cost must be list, got: {mind_cost.__class__.__name__}",
                    {"name": name, "mind_cost": mind_cost},
                )
                mind_cost = []
            else:
                # Validate each mind cost
                for i, cost in enumerate(mind_cost):
                    if not isinstance(cost, int) or cost < 0:
                        log_warning(
                            f"Spell {name} mind_cost[{i}] must be non-negative integer, got: {cost}",
                            {"name": name, "cost_index": i, "cost": cost},
                        )

            # Validate target_expr
            if not isinstance(target_expr, str):
                log_warning(
                    f"Spell {name} target_expr must be string, got: {target_expr.__class__.__name__}",
                    {"name": name, "target_expr": target_expr},
                )
                target_expr = str(target_expr) if target_expr is not None else ""

            # Validate requires_concentration
            if not isinstance(requires_concentration, bool):
                log_warning(
                    f"Spell {name} requires_concentration must be boolean, got: {requires_concentration.__class__.__name__}",
                    {"name": name, "requires_concentration": requires_concentration},
                )
                requires_concentration = bool(requires_concentration)

            self.level: int = level
            self.mind_cost: list[int] = mind_cost
            self.target_expr: str = target_expr
            self.requires_concentration: bool = requires_concentration

        except Exception as e:
            log_critical(
                f"Error initializing Spell {name}: {str(e)}",
                {"name": name, "error": str(e)},
                e,
            )
            raise

    def is_single_target(self) -> bool:
        """Check if the spell is single-target.

        Returns:
            bool: True if single-target, False otherwise.
        """
        return not self.target_expr or self.target_expr.strip() == ""

    def target_count(self, actor: Any, mind_level: int) -> int:
        """Returns the number of targets this ability can affect.

        Args:
            actor (Any): The character casting the spell.
            mind_level (int): The mind_cost level to use for evaluation.

        Returns:
            int: The number of targets this ability can affect.
        """
        if self.target_expr:
            variables = actor.get_expression_variables()
            variables["MIND"] = mind_level
            # Evaluate the multi-target expression to get the number of targets.
            return evaluate_expression(self.target_expr, variables)
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

    def apply_effect(
        self,
        actor: Any,
        target: Any,
        effect: Optional[Effect],
        mind_level: Optional[int] = 0,
    ) -> bool:
        """
        Override apply_effect to handle concentration requirements from spells.

        Args:
            actor: The character applying the effect.
            target: The character receiving the effect.
            effect: The effect to apply.
            mind_level: The spell level used.

        Returns:
            bool: True if the effect was successfully applied.
        """
        if not effect:
            return False
        if not actor.is_alive():
            return False
        if not target.is_alive():
            return False

        # If this spell requires concentration and effect exists, mark it as requiring concentration
        if self.requires_concentration and effect:
            effect.requires_concentration = True

        # For spells, pass the spell reference to the effect manager
        if target.effect_manager.add_effect(actor, effect, mind_level, self):
            debug(f"Applied effect {effect.name} from {actor.name} to {target.name}.")
            return True
        debug(f"Not applied effect {effect.name} from {actor.name} to {target.name}.")
        return False

    def to_dict(self) -> dict[str, Any]:
        """Converts the spell to a dictionary representation."""
        data = super().to_dict()
        # Add specific fields for Spell
        data["level"] = self.level
        data["mind_cost"] = self.mind_cost
        data["requires_concentration"] = self.requires_concentration
        # Include the multi-target expression if it exists.
        if self.target_expr:
            data["target_expr"] = self.target_expr
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
        target_expr: str = "",
        requires_concentration: bool = False,
        target_restrictions: list[str] | None = None,
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
            target_expr,
            requires_concentration,
            target_restrictions,
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
            target_expr=data.get("target_expr", ""),
            requires_concentration=data.get("requires_concentration", False),
            target_restrictions=data.get("target_restrictions"),
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
        target_expr: str = "",
        requires_concentration: bool = False,
        target_restrictions: list[str] | None = None,
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
            target_expr,
            requires_concentration,
            target_restrictions,
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

    def to_dict(self) -> dict[str, Any]:
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
            target_expr=data.get("target_expr", ""),
            requires_concentration=data.get("requires_concentration", False),
            target_restrictions=data.get("target_restrictions", []),
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
        effect: Effect,  # Changed from Buff to Effect
        target_expr: str = "",
        requires_concentration: bool = False,
        target_restrictions: list[str] | None = None,
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
            target_expr,
            requires_concentration,
            target_restrictions,
        )
        self.effect: Effect = effect  # Changed from Buff to Effect
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

        # Handle effects that have modifiers (Buff/Debuff)
        if isinstance(self.effect, ModifierEffect):
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
                    expressions[bonus_type] = str(value)
        # OnHitTrigger and other effect types don't need modifier expressions here

        return expressions

    def to_dict(self) -> dict[str, Any]:
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
            effect=Effect.from_dict(data["effect"]),
            target_expr=data.get("target_expr", ""),
            requires_concentration=data.get("requires_concentration", False),
            target_restrictions=data.get("target_restrictions", []),
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
        target_expr: str = "",
        requires_concentration: bool = False,
        target_restrictions: list[str] | None = None,
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
            target_expr,
            requires_concentration,
            target_restrictions,
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
            expressions[bonus_type] = substitute_variables(
                str(modifier.value), variables
            )
        return expressions

    def to_dict(self) -> dict[str, Any]:
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
            target_expr=data.get("target_expr", ""),
            requires_concentration=data.get("requires_concentration", False),
            target_restrictions=data.get("target_restrictions", []),
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
