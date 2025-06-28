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

    def apply_effect(self, actor: Character, target: Character, effect=None):
        """
        Applies an effect to the target character.
        This is a placeholder for actions that may apply effects.
        """
        if effect:
            debug(f"Applying effect {effect.name} from {actor.name} to {target.name}.")
            # Apply the effect to the target.
            effect.apply(actor, target)
            # Add the effect to the target's effects list.
            target.add_effect(actor, effect)

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
    def from_dict(data) -> "BaseAction":
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
        if data.get("class") == "BuffSpell":
            return BuffSpell.from_dict(data)
        if data.get("class") == "DebuffSpell":
            return DebuffSpell.from_dict(data)
        raise ValueError(f"Unknown action class: {data.get('class')}")


class WeaponAttack(BaseAction):
    def __init__(
        self,
        name: str,
        type: ActionType,
        damage_type: DamageType,
        attack_roll: str,
        damage_roll: str,
        effect=None,
    ):
        super().__init__(name, type, ActionCategory.OFFENSIVE)
        self.damage_type: DamageType = damage_type
        self.attack_roll: str = attack_roll
        self.damage_roll: str = damage_roll
        self.effect = effect

    def execute(self, actor: Character, target: Character):
        """
        Executes a weapon attack from the actor to the target.
        Applies attack and damage modifiers from the actor's active effects.
        """
        debug(f"{actor.name} attempts a {self.name} on {target.name}.")
        # Format once and for all the actor name and target name.
        actor_str = (
            f"[{'bold green' if actor.is_player else 'bold red'}]{actor.name}[/]"
        )
        target_str = (
            f"[{'bold green' if target.is_player else 'bold red'}]{target.name}[/]"
        )
        # Build the full attack expression by combining base roll with all attack modifiers
        full_attack_expr = self.attack_roll
        for _, bonus_expr in actor.attack_modifiers.items():
            # Correctly append the bonus expression string, preceded by a '+'
            full_attack_expr += f"+{bonus_expr}"
        debug(f"Weapon Attack Expression: {full_attack_expr}")
        # Roll the attack result. Pass actor to roll_expression to resolve stat modifiers.
        attack = roll_expression(full_attack_expr, actor)
        # Check against the target AC
        if attack >= target.ac:
            # Build the full damage expression by combining base roll with all damage modifiers
            full_damage_expr = self.damage_roll
            for _, bonus_expr in actor.damage_modifiers.items():
                # Correctly append the bonus expression string, preceded by a '+'
                full_damage_expr += f"+{bonus_expr}"
            debug(f"Weapon Damage Expression: {full_damage_expr}")
            # Compute the damage. Pass actor to roll_expression to resolve stat modifiers.
            damage = roll_expression(full_damage_expr, actor)
            # Apply the damage.
            damage = target.take_damage(damage, self.damage_type)
            # Apply effect.
            self.apply_effect(actor, target, self.effect)
            # Log the successful attack.
            console.print(
                f"{actor_str} attacks {target_str} with [cyan]{self.name}[/]: "
                f"rolled [white]{attack}[/] vs AC [yellow]{target.ac}[/], "
                f"hits for [bold magenta]{damage}[/] "
                f"[italic]{self.damage_type.name.lower()}[/] damage.",
                markup=True,
            )
            if self.effect:
                console.print(
                    f"    [yellow]Effect {self.effect.name} applied to {target_str} by {actor_str}.[/]"
                )
        else:
            console.print(
                f"{actor_str} attacks {target_str} with [cyan]{self.name}[/]: "
                f"rolled [red]{attack}[/] vs AC [yellow]{target.ac}[/], [red]misses[/]."
            )
        return True

    def to_dict(self) -> dict:
        # Get the base dictionary representation.
        data = super().to_dict()
        # Add specific fields for WeaponAttack
        data["damage_type"] = self.damage_type.name
        data["attack_roll"] = self.attack_roll
        data["damage_roll"] = self.damage_roll
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
            damage_type=DamageType[data["damage_type"]],
            attack_roll=data["attack_roll"],
            damage_roll=data["damage_roll"],
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

    def target_count(self, actor: Character, mind: int = -1) -> int:
        """Number of targets this ability can affect. Default is 1 (single-target)."""
        # First, get the mind level to use.
        mind = mind if mind >= 0 else self.mind
        # Second, check if there is a multi-target expression.
        if self.multi_target_expr and isinstance(self.multi_target_expr, str):
            # Evaluate the multi-target expression to get the number of targets.
            return evaluate_expression(
                self.multi_target_expr, entity=actor, mind_level=mind
            )
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
        Executes a spell attack from the actor to the target.
        """
        debug(f"{actor.name} attempts to cast {self.name} on {target.name}.")
        # Get the actual mind level to use for the spell.
        mind_level = mind_level if mind_level >= 0 else self.mind
        # Check if the actor has enough mind to cast the spell.
        if actor.mind < mind_level:
            error(f"{actor.name} does not have enough mind to cast {self.name}.")
            return False
        # Format once and for all the actor name and target name.
        actor_str = (
            f"[{'bold green' if actor.is_player else 'bold red'}]{actor.name}[/]"
        )
        target_str = (
            f"[{'bold green' if target.is_player else 'bold red'}]{target.name}[/]"
        )
        # Build the full spell attack expression. This uses the character's intrinsic spell attack bonus.
        full_attack_expr = "1D20 + " + str(actor.get_spell_attack_bonus(self.level))
        # Also include any additional attack modifiers from effects (if applicable to spells)
        for bonus_name, bonus_expr in actor.attack_modifiers.items():
            full_attack_expr += f"+{bonus_expr}"
        debug(f"Spell Attack Expression: {full_attack_expr}")
        # Roll the attack result. Pass actor to roll_expression to resolve stat modifiers.
        attack = roll_expression(full_attack_expr, actor, mind_level)
        # Check against the target AC
        if attack >= target.ac:
            # Compute the damage based on the mind spent and any damage modifiers
            full_damage_expr = self.damage_roll
            for bonus_name, bonus_expr in actor.damage_modifiers.items():
                full_damage_expr += f"+{bonus_expr}"
            debug(f"Spell Damage Expression: {full_damage_expr}")
            damage = roll_expression(full_damage_expr, actor, mind_level)
            # Apply the damage.
            damage = target.take_damage(damage, self.damage_type)
            # Apply effect.
            self.apply_effect(actor, target, self.effect)
            # Log the successful attack.
            console.print(
                f"{actor_str} casts [bold]{self.name}[/] on {target_str}: "
                f"rolled [white]{attack}[/] vs AC [yellow]{target.ac}[/], "
                f"hits for [bold magenta]{damage}[/] "
                f"[italic]{self.damage_type.name.lower()}[/] damage."
            )
            if self.effect:
                console.print(
                    f"    [yellow]Effect {self.effect.name} applied to {target_str} by {actor_str}.[/]"
                )
        else:
            console.print(
                f"{actor_str} casts [bold magenta]{self.name}[/] on {target_str}: "
                f"rolled [red]{attack}[/] vs AC [yellow]{target.ac}[/], [red]misses[/]."
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
        # Get the actual mind level to use for the spell.
        mind_level = mind_level if mind_level >= 0 else self.mind
        # Check if the actor has enough mind to cast the spell.
        if actor.mind < mind_level:
            error(f"{actor.name} does not have enough mind to cast {self.name}.")
            return False
        # Format once and for all the actor name and target name.
        actor_str = (
            f"[{'bold green' if actor.is_player else 'bold red'}]{actor.name}[/]"
        )
        target_str = (
            f"[{'bold green' if target.is_player else 'bold red'}]{target.name}[/]"
        )
        # Compute the healing based on the mind spent and heal roll.
        heal = roll_expression(self.heal_roll, actor, mind_level)
        # Apply the healing.
        heal = target.heal(heal)
        # Apply effect.
        self.apply_effect(actor, target, self.effect)
        # Log the successful healing.
        console.print(
            f"{actor_str} casts [bold]{self.name}[/] on {target_str}: "
            f"heals for [bold green]{heal}[/]."
        )
        if self.effect:
            console.print(
                f"    [yellow]Effect {self.effect.name} applied to {target_str} by {actor_str}.[/]"
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


class BuffSpell(Spell):
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
        assert self.effect is not None, "Effect must be provided for BuffSpell."

    def cast_spell(
        self, actor: Character, target: Character, mind_level: int = -1
    ) -> bool:
        """
        Executes a buff spell, applying a beneficial effect to the target.
        Uses mind to cast the spell.
        """
        debug(f"{actor.name} attempts to cast {self.name} on {target.name}.")
        # Get the actual mind level to use for the spell.
        mind_level = mind_level if mind_level >= 0 else self.mind
        # Check if the actor has enough mind to cast the spell.
        if actor.mind < mind_level:
            error(f"{actor.name} does not have enough mind to cast {self.name}.")
            return False
        # Format once and for all the actor name and target name.
        actor_str = (
            f"[{'bold green' if actor.is_player else 'bold red'}]{actor.name}[/]"
        )
        target_str = (
            f"[{'bold green' if target.is_player else 'bold red'}]{target.name}[/]"
        )
        # Apply effect.
        self.apply_effect(actor, target, self.effect)
        console.print(
            f"{actor_str} casts [bold]{self.name}[/] on {target_str}, applying effect [bold]{self.effect.name}[/]."
        )
        if self.effect:
            console.print(
                f"    [yellow]Effect {self.effect.name} applied to {target_str} by {actor_str}.[/]"
            )
        return True

    def to_dict(self):
        """Converts the spell to a dictionary representation."""
        data = super().to_dict()
        # Add specific fields for BuffSpell
        data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data):
        """
        Creates a BuffSpell instance from a dictionary.
        Args:
            data (dict): Dictionary containing the action data.
        Returns:
            BuffSpell: An instance of BuffSpell.
        """
        return BuffSpell(
            name=data["name"],
            type=ActionType[data["type"]],
            level=data["level"],
            mind=data["mind"],
            effect=Effect.from_dict(data.get("effect", None)),
            multi_target_expr=data.get("multi_target_expr", None),
            upscale_choices=data.get("upscale_choices", None),
        )


class DebuffSpell(Spell):
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
        assert self.effect is not None, "Effect must be provided for DebuffSpell."

    def cast_spell(
        self, actor: Character, target: Character, mind_level: int = -1
    ) -> bool:
        """
        Executes a debuff spell, applying a detrimental effect to the target.
        Uses mind to cast the spell.
        """
        debug(f"{actor.name} attempts to cast {self.name} on {target.name}.")
        # Get the actual mind level to use for the spell.
        mind_level = mind_level if mind_level >= 0 else self.mind
        # Check if the actor has enough mind to cast the spell.
        if actor.mind < mind_level:
            error(f"{actor.name} does not have enough mind to cast {self.name}.")
            return False
        # Format once and for all the actor name and target name.
        actor_str = (
            f"[{'bold green' if actor.is_player else 'bold red'}]{actor.name}[/]"
        )
        target_str = (
            f"[{'bold green' if target.is_player else 'bold red'}]{target.name}[/]"
        )
        # Apply effect.
        self.apply_effect(actor, target, self.effect)
        # Log the successful debuff.
        console.print(
            f"{actor_str} casts [bold]{self.name}[/] on {target_str}, applying effect [bold]{self.effect.name}[/]."
        )
        if self.effect:
            console.print(
                f"    [yellow]Effect {self.effect.name} applied to {target_str} by {actor_str}.[/]"
            )
        return True

    def to_dict(self):
        """Converts the spell to a dictionary representation."""
        data = super().to_dict()
        # Add specific fields for DebuffSpell
        data["effect"] = self.effect.to_dict()
        return data

    @staticmethod
    def from_dict(data):
        """
        Creates a DebuffSpell instance from a dictionary.
        Args:
            data (dict): Dictionary containing the action data.
        Returns:
            DebuffSpell: An instance of DebuffSpell.
        """
        return DebuffSpell(
            name=data["name"],
            type=ActionType[data["type"]],
            level=data["level"],
            mind=data["mind"],
            effect=Effect.from_dict(data.get("effect", None)),
            multi_target_expr=data.get("multi_target_expr", None),
            upscale_choices=data.get("upscale_choices", None),
        )
