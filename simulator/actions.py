from abc import ABC, abstractmethod
from logging import info, debug, warning, error
from re import I
from rich.console import Console


from character import Character
from colors import *
from character import *
from effect import *
from effect import Character
from utils import *
from constants import *

console = Console()


class BaseAction(ABC):
    def __init__(self, name: str, type: ActionType, category: ActionCategory):
        self.name: str = name
        self.type: ActionType = type
        self.category: ActionCategory = category

    def execute(self, actor: Character, target: Character) -> bool:
        """Abstract method for executables.

        Args:
            actor (Character): The character performing the action.
            target (Character): The character targeted by the action.

        Returns:
            bool: True if the action was successfully executed, False otherwise.
        """
        ...

    def apply_effect(
        self, actor: Character, target: Character, effect, mind_level: int = 0
    ):
        """Applies an effect to a target character.

        Args:
            actor (Character): The character performing the action.
            target (Character): The character targeted by the action.
            effect (Effect): The effect to apply.
            mind_level (int, optional): The mind level to use for the effect. Defaults to 0.
        """
        debug(f"Applying effect {effect.name} from {actor.name} to {target.name}.")
        # Apply the effect to the target.
        effect.apply(actor, target, mind_level)
        # Add the effect to the target's effects list.
        target.add_effect(actor, effect, mind_level)

    def to_dict(self) -> dict:
        """Converts the action to a dictionary representation.

        Returns:
            dict: A dictionary containing the executable's data.
        """
        return {
            "class": self.__class__.__name__,
            "name": self.name,
            "type": self.type.name,
            "category": self.category.name,
        }

    @staticmethod
    def from_dict(data):
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


from utils import substitute_variables, roll_expression


class WeaponAttack(BaseAction):
    def __init__(
        self,
        name: str,
        type: ActionType,
        hands_required: int,
        attack_roll: str,
        damage_components: list[dict],
        effect=None,
    ):
        super().__init__(name, type, ActionCategory.OFFENSIVE)
        self.hands_required = hands_required
        self.attack_roll = attack_roll
        self.damage_components = damage_components
        self.effect = effect

        for component in self.damage_components:
            if "roll" not in component or "type" not in component:
                raise ValueError("Each damage component must have 'roll' and 'type'.")
            if component["type"] not in DamageType.__members__:
                raise ValueError(f"Invalid damage type: {component['type']}")

    def execute(self, actor: Character, target: Character):
        debug(f"{actor.name} attempts a {self.name} on {target.name}.")
        actor_str = (
            f"[{'bold green' if actor.is_player else 'bold red'}]{actor.name}[/]"
        )
        target_str = (
            f"[{'bold green' if target.is_player else 'bold red'}]{target.name}[/]"
        )

        # --- Build & resolve attack roll ---
        attack_expr = self.attack_roll
        for _, bonus_expr in actor.attack_modifiers.items():
            attack_expr += f"+{bonus_expr}"
        attack_result, attack_roll_desc = roll_and_describe(attack_expr, actor)

        # --- Outcome: HIT ---
        if attack_result >= target.ac:
            total_damage = 0
            damage_details = []
            for component in self.damage_components:
                damage_expr = substitute_variables(component["roll"], actor)
                damage_amount = roll_expression(damage_expr, actor)
                damage_type = DamageType[component["type"]]
                applied_damage = target.take_damage(damage_amount, damage_type)
                total_damage += applied_damage
                damage_details.append(
                    f"{applied_damage} {damage_type.name.lower()} ({damage_expr})"
                )
            console.print(
                f"    {actor_str} attacks {target_str} with [cyan]{self.name}[/]: "
                f"rolled {attack_result} ({attack_roll_desc}) vs AC [yellow]{target.ac}[/] — [green]hit![/]",
                markup=True,
            )
            console.print(
                f"        🗡️ [bold magenta]Damage:[/] {total_damage} total — "
                + " + ".join(damage_details),
                markup=True,
            )

            if self.effect:
                self.apply_effect(actor, target, self.effect)
                console.print(
                    f"        ✨ [yellow]Effect [bold]{self.effect.name}[/] applied to {target_str}[/]",
                    markup=True,
                )

        # --- Outcome: MISS ---
        else:
            console.print(
                f"    {actor_str} attacks {target_str} with [cyan]{self.name}[/]: "
                f"rolled [red]{attack_result}[/] ({attack_roll_desc}) vs AC [yellow]{target.ac}[/] — [red]miss[/]",
                markup=True,
            )

        return True

    def to_dict(self) -> dict:
        # Get the base dictionary representation.
        data = super().to_dict()
        # Add specific fields for WeaponAttack
        data["hands_required"] = self.hands_required
        data["attack_roll"] = self.attack_roll
        data["damage_components"] = self.damage_components
        # Include the effect if it exists.
        if self.effect:
            data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data):
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
            hands_required=data["hands_required"],
            attack_roll=data["attack_roll"],
            damage_components=data["damage_components"],
            effect=Effect.from_dict(data.get("effect", None)),
        )


class Spell(BaseAction):
    def __init__(
        self,
        name,
        type: ActionType,
        level: int,
        mind: int,
        category: ActionCategory,
        multi_target_expr=None,
        upscale_choices=None,
    ):
        super().__init__(name, type, category)
        self.level: int = level
        self.mind: int = mind
        self.multi_target_expr = multi_target_expr
        self.upscale_choices = upscale_choices or [mind]

    def is_single_target(self) -> bool:
        """Returns True if this spell is single-target, False otherwise."""
        return not self.multi_target_expr or not isinstance(self.multi_target_expr, str)

    def target_count(self, actor: Character, mind_level: int = -1) -> int:
        """Number of targets this ability can affect. Default is 1 (single-target)."""
        if not self.is_single_target():
            # First, get the mind level to use.
            mind_level = mind_level if mind_level >= 0 else self.mind
            # Evaluate the multi-target expression to get the number of targets.
            return evaluate_expression(self.multi_target_expr, actor, mind_level)
        return 1

    def mind_choices(self) -> list[int]:
        """Returns valid MIND levels this spell can be cast at. Default is [self.mind]."""
        return self.upscale_choices or [self.mind]

    def execute(self, actor: Character, target: Character) -> bool:
        """
        Spells should not be executed directly from the base class.
        """
        raise NotImplementedError("Spells must use the cast_spell method.")

    @abstractmethod
    def cast_spell(self, actor: Character, target: Character, mind_level: int) -> bool:
        """
        Abstract method for executing an action.
        Args:
            actor (Character): The character performing the action.
            target (Character): The character targeted by the action.
        Returns:
            bool: True if the action was successfully executed, False otherwise.
        """
        pass

    def to_dict(self) -> dict:
        """Converts the spell to a dictionary representation."""
        data = super().to_dict()
        # Add specific fields for Spell
        data["level"] = self.level
        data["mind"] = self.mind
        # Include the multi-target expression if it exists.
        if self.multi_target_expr:
            data["multi_target_expr"] = self.multi_target_expr
        # Include the upscale choices if they exist.
        if self.upscale_choices:
            data["upscale_choices"] = self.upscale_choices
        return data


class SpellAttack(Spell):
    def __init__(
        self,
        name: str,
        type: ActionType,
        level: int,
        mind: int,
        damage_type: DamageType,
        damage_roll: str,
        effect=None,
        multi_target_expr=None,
        upscale_choices=None,
    ):
        super().__init__(
            name,
            type,
            level,
            mind,
            ActionCategory.OFFENSIVE,
            multi_target_expr,
            upscale_choices,
        )
        self.damage_type: DamageType = damage_type
        self.damage_roll: str = damage_roll
        self.effect = effect

    def cast_spell(
        self, actor: Character, target: Character, mind_level: int = -1
    ) -> bool:
        """
        Executes a spell attack from the actor to the target with breakdown logs.
        """
        debug(f"{actor.name} attempts to cast {self.name} on {target.name}.")
        mind_level = mind_level if mind_level >= 0 else self.mind

        if actor.mind < mind_level:
            error(f"{actor.name} does not have enough mind to cast {self.name}.")
            return False

        actor_str = (
            f"[{'bold green' if actor.is_player else 'bold red'}]{actor.name}[/]"
        )
        target_str = (
            f"[{'bold green' if target.is_player else 'bold red'}]{target.name}[/]"
        )

        # --- Build and roll attack expression ---
        full_attack_expr = "1D20 + " + str(actor.get_spell_attack_bonus(self.level))
        for _, bonus_expr in actor.attack_modifiers.items():
            full_attack_expr += f"+{bonus_expr}"

        attack_roll, attack_desc = roll_and_describe(
            full_attack_expr, actor, mind_level
        )

        # --- Hit logic ---
        if attack_roll >= target.ac:
            full_damage_expr = self.damage_roll
            for _, bonus_expr in actor.damage_modifiers.items():
                full_damage_expr += f"+{bonus_expr}"
            damage_roll, damage_desc = roll_and_describe(
                full_damage_expr, actor, mind_level
            )
            applied_damage = target.take_damage(damage_roll, self.damage_type)
            console.print(
                f"    {actor_str} casts [bold]{self.name}[/] on {target_str}: "
                f"rolled [white]{attack_roll}[/] ({attack_desc}) vs AC [yellow]{target.ac}[/] — [green]hit![/]",
                markup=True,
            )
            console.print(
                f"        🗡️ [bold magenta]Damage:[/] {applied_damage} "
                f"[italic]{self.damage_type.name.lower()}[/] ({damage_desc})",
                markup=True,
            )
            if self.effect:
                self.apply_effect(actor, target, self.effect)
                console.print(
                    f"        ✨ [yellow]Effect [bold]{self.effect.name}[/] applied to {target_str}[/]",
                    markup=True,
                )
        # --- Miss logic ---
        else:
            console.print(
                f"    {actor_str} casts [bold magenta]{self.name}[/] on {target_str}: "
                f"rolled [red]{attack_roll}[/] ({attack_desc}) vs AC [yellow]{target.ac}[/] — [red]miss[/]",
                markup=True,
            )

        return True

    def to_dict(self) -> dict:
        """Converts the spell to a dictionary representation."""
        data = super().to_dict()
        # Add specific fields for SpellAttack
        data["damage_type"] = self.damage_type.name
        data["damage_roll"] = self.damage_roll
        # Include the effect if it exists.
        if self.effect:
            data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data):
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
            level=data["level"],
            mind=data["mind"],
            damage_type=DamageType[data["damage_type"]],
            damage_roll=data["damage_roll"],
            effect=Effect.from_dict(data.get("effect", None)),
            multi_target_expr=data.get("multi_target_expr", None),
            upscale_choices=data.get("upscale_choices", None),
        )


class SpellHeal(Spell):
    def __init__(
        self,
        name: str,
        type: ActionType,
        level: int,
        mind: int,
        heal_roll: str,
        effect=None,
        multi_target_expr=None,
        upscale_choices=None,
    ):
        super().__init__(
            name,
            type,
            level,
            mind,
            ActionCategory.HEALING,
            multi_target_expr,
            upscale_choices,
        )
        self.heal_roll: str = heal_roll
        self.effect = effect

    def cast_spell(
        self, actor: Character, target: Character, mind_level: int = -1
    ) -> bool:
        """
        Executes a healing spell from the actor to the target.
        Uses mind to cast the spell.
        """
        debug(
            f"{actor.name} attempts to cast {self.name} on {target.name}, expression {self.heal_roll}."
        )
        mind_level = mind_level if mind_level >= 0 else self.mind

        if actor.mind < mind_level:
            error(f"{actor.name} does not have enough mind to cast {self.name}.")
            return False

        actor_str = (
            f"[{'bold green' if actor.is_player else 'bold red'}]{actor.name}[/]"
        )
        target_str = (
            f"[{'bold green' if target.is_player else 'bold red'}]{target.name}[/]"
        )

        # Compute the healing based on the mind spent and roll
        heal_value, heal_desc = roll_and_describe(self.heal_roll, actor, mind_level)

        # Apply healing to the target
        actual_healed = target.heal(heal_value)

        console.print(
            f"    {actor_str} casts [bold]{self.name}[/] on {target_str}: "
            f"heals for [bold green]{actual_healed}[/] ([white]{heal_desc}[/]).",
            markup=True,
        )

        if self.effect:
            self.apply_effect(actor, target, self.effect)
            console.print(
                f"        ✨ [yellow]Effect [bold]{self.effect.name}[/] applied to {target_str}[/]",
                markup=True,
            )

        return True

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
    def from_dict(data):
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
            level=data["level"],
            mind=data["mind"],
            heal_roll=data["heal_roll"],
            effect=Effect.from_dict(data.get("effect", None)),
            multi_target_expr=data.get("multi_target_expr", None),
            upscale_choices=data.get("upscale_choices", None),
        )


class SpellBuff(Spell):
    def __init__(
        self,
        name: str,
        type: ActionType,
        level: int,
        mind: int,
        effect,
        multi_target_expr=None,
        upscale_choices=None,
    ):
        super().__init__(
            name,
            type,
            level,
            mind,
            ActionCategory.BUFF,
            multi_target_expr,
            upscale_choices,
        )
        self.effect = effect
        # Ensure the effect is provided.
        assert self.effect is not None, "Effect must be provided for SpellBuff."

    def cast_spell(
        self, actor: Character, target: Character, mind_level: int = -1
    ) -> bool:
        """
        Executes a buff spell, applying a beneficial effect to the target.
        Uses mind to cast the spell.
        """
        debug(f"{actor.name} attempts to cast {self.name} on {target.name}.")
        mind_level = mind_level if mind_level >= 0 else self.mind

        if actor.mind < mind_level:
            error(f"{actor.name} does not have enough mind to cast {self.name}.")
            return False

        actor_str = (
            f"[{'bold green' if actor.is_player else 'bold red'}]{actor.name}[/]"
        )
        target_str = (
            f"[{'bold green' if target.is_player else 'bold red'}]{target.name}[/]"
        )

        # Informational log
        console.print(
            f"    {actor_str} casts [bold]{self.name}[/] on {target_str}.",
            markup=True,
        )

        # Apply the effect
        if self.effect:
            self.apply_effect(actor, target, self.effect)
            console.print(
                f"        ✨ [yellow]Effect [bold]{self.effect.name}[/] applied to {target_str}[/]",
                markup=True,
            )

        return True

    def to_dict(self):
        """Converts the spell to a dictionary representation."""
        data = super().to_dict()
        # Add specific fields for SpellBuff
        data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data):
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
            level=data["level"],
            mind=data["mind"],
            effect=Effect.from_dict(data.get("effect", None)),
            multi_target_expr=data.get("multi_target_expr", None),
            upscale_choices=data.get("upscale_choices", None),
        )


class SpellDebuff(Spell):
    def __init__(
        self,
        name: str,
        type: ActionType,
        level: int,
        mind: int,
        effect,
        multi_target_expr=None,
        upscale_choices=None,
    ):
        super().__init__(
            name,
            type,
            level,
            mind,
            ActionCategory.DEBUFF,
            multi_target_expr,
            upscale_choices,
        )
        self.effect = effect
        # Ensure the effect is provided.
        assert self.effect is not None, "Effect must be provided for SpellDebuff."

    def cast_spell(
        self, actor: Character, target: Character, mind_level: int = -1
    ) -> bool:
        """
        Executes a debuff spell, applying a detrimental effect to the target.
        Uses mind to cast the spell.
        """
        debug(f"{actor.name} attempts to cast {self.name} on {target.name}.")
        mind_level = mind_level if mind_level >= 0 else self.mind

        if actor.mind < mind_level:
            error(f"{actor.name} does not have enough mind to cast {self.name}.")
            return False

        actor_str = (
            f"[{'bold green' if actor.is_player else 'bold red'}]{actor.name}[/]"
        )
        target_str = (
            f"[{'bold green' if target.is_player else 'bold red'}]{target.name}[/]"
        )

        # Informational log
        console.print(
            f"    {actor_str} casts [bold]{self.name}[/] on {target_str}.",
            markup=True,
        )

        # Apply the debuff effect
        if self.effect:
            self.apply_effect(actor, target, self.effect)
            console.print(
                f"        ✨ [yellow]Effect [bold]{self.effect.name}[/] applied to {target_str}[/]",
                markup=True,
            )

        return True

    def to_dict(self):
        """Converts the spell to a dictionary representation."""
        data = super().to_dict()
        # Add specific fields for SpellDebuff
        data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data):
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
            level=data["level"],
            mind=data["mind"],
            effect=Effect.from_dict(data.get("effect", None)),
            multi_target_expr=data.get("multi_target_expr", None),
            upscale_choices=data.get("upscale_choices", None),
        )
