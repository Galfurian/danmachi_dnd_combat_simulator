from core.utils import *
from typing import Any
from core.constants import *
from core.error_handling import log_error, log_warning, log_critical
from combat.damage import *
from .modifier import Modifier


class Effect:
    def __init__(
        self,
        name: str,
        description: str = "",
        max_duration: int = 0,
        requires_concentration: bool = False,
    ):
        # Validate inputs
        if not name or not isinstance(name, str):
            log_error(
                f"Effect name must be a non-empty string, got: {name}",
                {"name": name, "type": type(name).__name__},
            )
            raise ValueError(f"Invalid effect name: {name}")

        if not isinstance(description, str):
            log_warning(
                f"Effect description must be a string, got: {type(description).__name__}",
                {"name": name, "description": description},
            )
            description = str(description) if description is not None else ""

        if not isinstance(max_duration, int) or max_duration < 0:
            log_error(
                f"Effect max_duration must be a non-negative integer, got: {max_duration}",
                {"name": name, "max_duration": max_duration},
            )
            max_duration = max(
                0, int(max_duration) if isinstance(max_duration, (int, float)) else 0
            )

        if not isinstance(requires_concentration, bool):
            log_warning(
                f"Effect requires_concentration must be boolean, got: {type(requires_concentration).__name__}",
                {"name": name, "requires_concentration": requires_concentration},
            )
            requires_concentration = bool(requires_concentration)

        self.name: str = name
        self.description: str = description
        self.max_duration: int = max_duration
        self.requires_concentration: bool = requires_concentration

    def turn_update(self, actor: Any, target: Any, mind_level: int = 0) -> None:
        """Update the effect for the current turn.

        Args:
            actor (Any): The character applying the effect.
            target (Any): The character receiving the effect.
            mind_level (int, optional): The mind level of the actor. Defaults to 0.
        """
        try:
            if not actor:
                log_error(
                    f"Actor cannot be None for effect {self.name}",
                    {"effect": self.name},
                )
                return

            if not target:
                log_error(
                    f"Target cannot be None for effect {self.name}",
                    {"effect": self.name},
                )
                return

            if not isinstance(mind_level, int) or mind_level < 0:
                log_warning(
                    f"Mind level must be non-negative integer for effect {self.name}, got: {mind_level}",
                    {"effect": self.name, "mind_level": mind_level},
                )
                mind_level = max(
                    0, int(mind_level) if isinstance(mind_level, (int, float)) else 0
                )

        except Exception as e:
            log_critical(
                f"Error during turn_update validation for effect {self.name}: {str(e)}",
                {
                    "effect": self.name,
                    "actor": getattr(actor, "name", "unknown"),
                    "target": getattr(target, "name", "unknown"),
                },
                e,
            )

    def is_permanent(self) -> bool:
        """Check if the effect is permanent (i.e., has no duration).

        Returns:
            bool: True if the effect is permanent, False otherwise.
        """
        return self.max_duration <= 0

    def validate(self):
        """Validate the effect's properties."""
        try:
            if not self.name:
                log_error("Effect name must not be empty", {"name": self.name})
                raise ValueError("Effect name must not be empty")

            if not isinstance(self.description, str):
                log_warning(
                    f"Effect description must be a string, got {type(self.description).__name__}",
                    {"name": self.name, "description": self.description},
                )
                raise ValueError("Effect description must be a string")

        except Exception as e:
            if not isinstance(e, ValueError):
                log_critical(
                    f"Unexpected error during effect validation: {str(e)}",
                    {"effect": self.name},
                    e,
                )
            raise

    def can_apply(self, actor: Any, target: Any) -> bool:
        """Check if the effect can be applied to the target.

        Args:
            actor (Any): The character applying the effect.
            target (Any): The character receiving the effect.

        Returns:
            bool: True if the effect can be applied, False otherwise.
        """
        try:
            if not actor:
                log_warning(
                    f"Actor cannot be None when checking if effect {self.name} can be applied",
                    {"effect": self.name},
                )
                return False

            if not target:
                log_warning(
                    f"Target cannot be None when checking if effect {self.name} can be applied",
                    {"effect": self.name},
                )
                return False

            return False  # Base implementation

        except Exception as e:
            log_error(
                f"Error checking if effect {self.name} can be applied: {str(e)}",
                {"effect": self.name},
                e,
            )
            return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.__class__.__name__,
            "name": self.name,
            "description": self.description,
            "max_duration": self.max_duration,
            "requires_concentration": self.requires_concentration,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Effect":
        """Creates an Effect instance from a dictionary representation.

        Args:
            data (dict[str, Any]): The dictionary representation of the effect.

        Returns:
            Effect: An instance of the Effect class.
        """
        assert data is not None, "Data must not be None."
        effect_type = data.get("type")

        if effect_type == "Buff":
            return Buff.from_dict(data)
        if effect_type == "Debuff":
            return Debuff.from_dict(data)
        if effect_type == "DoT":
            return DoT.from_dict(data)
        if effect_type == "HoT":
            return HoT.from_dict(data)
        if effect_type == "OnHitTrigger":
            return OnHitTrigger.from_dict(data)
        if effect_type == "OnLowHealthTrigger":
            return OnLowHealthTrigger.from_dict(data)
        if effect_type == "IncapacitatingEffect":
            from .incapacitation_effect import IncapacitatingEffect
            return IncapacitatingEffect.from_dict(data)
        raise ValueError(f"Unknown effect type: {effect_type}")


class ModifierEffect(Effect):
    def __init__(
        self,
        name: str,
        description: str,
        max_duration: int,
        modifiers: list[Modifier],
        requires_concentration: bool = False,
    ):
        super().__init__(name, description, max_duration, requires_concentration)
        self.modifiers: list[Modifier] = modifiers
        self.validate()

    def validate(self):
        super().validate()
        assert isinstance(self.modifiers, list), "Modifiers must be a list."
        for modifier in self.modifiers:
            assert isinstance(
                modifier, Modifier
            ), f"Modifier '{modifier}' must be of type Modifier."

    def can_apply(self, actor: Any, target: Any) -> bool:
        if not target.is_alive():
            return False
        # Check if the target is already affected by the same modifiers.
        for modifier in self.modifiers:
            existing_modifiers = target.effect_manager.get_modifier(modifier.bonus_type)
            if not existing_modifiers:
                continue
            # Check if the target already has this exact modifier
            if modifier in existing_modifiers:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["modifiers"] = [modifier.to_dict() for modifier in self.modifiers]
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Buff | Debuff":
        assert data is not None, "Data must not be None."
        if data.get("type") == "Buff":
            return Buff.from_dict(data)
        if data.get("type") == "Debuff":
            return Debuff.from_dict(data)
        raise ValueError(f"Unknown modifier effect type: {data.get('type')}")


class Buff(ModifierEffect):
    def __init__(
        self,
        name: str,
        description: str,
        max_duration: int,
        modifiers: list[Modifier],
    ):
        super().__init__(name, description, max_duration, modifiers)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Buff":
        assert data is not None, "Data must not be None."
        modifiers: list[Modifier] = []

        # Handle both old dict format and new list format for backward compatibility
        if "modifiers" in data:
            modifier_data = data["modifiers"]
            if isinstance(modifier_data, dict):
                # Old format: convert dict to list of Modifier objects
                for k, v in modifier_data.items():
                    bonus_type = BonusType[k.upper()]
                    if bonus_type == BonusType.DAMAGE:
                        value = DamageComponent.from_dict(v)
                    elif bonus_type in [
                        BonusType.HP,
                        BonusType.MIND,
                        BonusType.AC,
                        BonusType.INITIATIVE,
                    ]:
                        value = int(v)
                    elif bonus_type == BonusType.ATTACK:
                        value = str(v)
                    else:
                        value = str(v)
                    modifiers.append(Modifier(bonus_type, value))
            elif isinstance(modifier_data, list):
                # New format: list of modifier dicts
                modifiers = [Modifier.from_dict(mod_data) for mod_data in modifier_data]

        return Buff(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            modifiers=modifiers,
        )


class Debuff(ModifierEffect):
    def __init__(
        self,
        name: str,
        description: str,
        max_duration: int,
        modifiers: list[Modifier],
    ):
        super().__init__(name, description, max_duration, modifiers)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Debuff":
        assert data is not None, "Data must not be None."
        modifiers: list[Modifier] = []

        # Handle both old dict format and new list format for backward compatibility
        if "modifiers" in data:
            modifier_data = data["modifiers"]
            if isinstance(modifier_data, dict):
                # Old format: convert dict to list of Modifier objects
                for k, v in modifier_data.items():
                    bonus_type = BonusType[k.upper()]
                    if bonus_type == BonusType.DAMAGE:
                        value = DamageComponent.from_dict(v)
                    elif bonus_type in [
                        BonusType.HP,
                        BonusType.MIND,
                        BonusType.AC,
                        BonusType.INITIATIVE,
                    ]:
                        value = int(v)
                    elif bonus_type == BonusType.ATTACK:
                        value = str(v)
                    else:
                        value = str(v)
                    modifiers.append(Modifier(bonus_type, value))
            elif isinstance(modifier_data, list):
                # New format: list of modifier dicts
                modifiers = [Modifier.from_dict(mod_data) for mod_data in modifier_data]

        return Debuff(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            modifiers=modifiers,
        )


class DoT(Effect):
    def __init__(
        self,
        name: str,
        description: str,
        max_duration: int,
        damage: DamageComponent,
    ):
        super().__init__(name, description, max_duration)
        self.damage: DamageComponent = damage

        self.validate()

    def turn_update(self, actor: Any, target: Any, mind_level: Optional[int] = 1):
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        # Calculate the damage amount using the provided expression.
        dot_value, dot_desc, _ = roll_and_describe(self.damage.damage_roll, variables)
        # Asser that the damage value is a positive integer.
        assert (
            isinstance(dot_value, int) and dot_value >= 0
        ), f"DoT '{self.name}' must have a non-negative integer damage value, got {dot_value}."
        # Apply the damage to the target.
        base, adjusted, taken = target.take_damage(dot_value, self.damage.damage_type)
        # If the damage value is positive, print the damage message.
        dot_str = f"    {get_effect_emoji(self)} "
        dot_str += apply_character_type_color(target.type, target.name) + " takes "
        # Create a damage string for display.
        dot_str += apply_damage_type_color(
            self.damage.damage_type,
            f"{taken} {get_damage_type_emoji(self.damage.damage_type)} ",
        )
        # If the base damage differs from the adjusted damage (due to resistances),
        # include the original and adjusted values in the damage string.
        if base != adjusted:
            dot_str += f"[dim](reduced: {base} → {adjusted})[/] "
        # Append the rolled damage expression to the damage string.
        dot_str += f"({dot_desc})"
        # Add the damage string to the list of damage details.
        cprint(dot_str)
        # If the target is defeated, print a message.
        if not target.is_alive():
            cprint(f"    [bold red]{target.name} has been defeated![/]")

    def validate(self):
        super().validate()
        assert self.max_duration > 0, "DoT duration must be greater than 0."
        assert isinstance(
            self.damage, DamageComponent
        ), "Damage must be of type DamageComponent."

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["damage"] = self.damage.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "DoT":
        assert data is not None, "Data must not be None."
        return DoT(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            damage=DamageComponent.from_dict(data["damage"]),
        )


class HoT(Effect):
    def __init__(
        self,
        name: str,
        description: str,
        max_duration: int,
        heal_per_turn: str,
    ):
        super().__init__(name, description, max_duration)
        self.heal_per_turn = heal_per_turn

        self.validate()

    def turn_update(self, actor: Any, target: Any, mind_level: Optional[int] = 1):
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        # Calculate the heal amount using the provided expression.
        hot_value, hot_desc, _ = roll_and_describe(self.heal_per_turn, variables)
        # Assert that the heal value is a positive integer.
        assert (
            isinstance(hot_value, int) and hot_value >= 0
        ), f"HoT '{self.name}' must have a non-negative integer heal value, got {hot_value}."
        # Apply the heal to the target.
        hot_value = target.heal(hot_value)
        # If the heal value is positive, print the heal message.
        message = f"    {get_effect_emoji(self)} "
        message += apply_character_type_color(target.type, target.name)
        message += f" heals for {hot_value} ([white]{hot_desc}[/]) hp from "
        message += apply_effect_color(self, self.name) + "."
        cprint(message)

    def validate(self):
        super().validate()
        assert self.max_duration > 0, "HoT duration must be greater than 0."
        assert isinstance(
            self.heal_per_turn, str
        ), "Heal per turn must be a string expression."

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["heal_per_turn"] = self.heal_per_turn
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "HoT":
        assert data is not None, "Data must not be None."
        return HoT(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            heal_per_turn=data["heal_per_turn"],
        )


class OnHitTrigger(Effect):
    """Effect that activates when the character makes their next weapon/natural attack."""

    def __init__(
        self,
        name: str,
        description: str,
        max_duration: int,
        trigger_effects: list["Effect"],
        damage_bonus: list[DamageComponent] | None = None,
        consumes_on_trigger: bool = True,
        requires_concentration: bool = False,
    ):
        super().__init__(name, description, max_duration, requires_concentration)
        self.trigger_effects: list[Effect] = trigger_effects or []
        self.damage_bonus: list[DamageComponent] = damage_bonus or []
        self.consumes_on_trigger: bool = consumes_on_trigger
        self.validate()

    def validate(self):
        super().validate()
        assert isinstance(self.trigger_effects, list), "Trigger effects must be a list."
        for effect in self.trigger_effects:
            assert isinstance(
                effect, Effect
            ), f"Trigger effect '{effect}' must be of type Effect."
        assert isinstance(self.damage_bonus, list), "Damage bonus must be a list."
        for damage_comp in self.damage_bonus:
            assert isinstance(
                damage_comp, DamageComponent
            ), f"Damage component '{damage_comp}' must be of type DamageComponent."

    def can_apply(self, actor: Any, target: Any) -> bool:
        """OnHitTrigger can be applied to any living target."""
        return target.is_alive()

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["trigger_effects"] = [effect.to_dict() for effect in self.trigger_effects]
        data["damage_bonus"] = [damage.to_dict() for damage in self.damage_bonus]
        data["consumes_on_trigger"] = self.consumes_on_trigger
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "OnHitTrigger":
        assert data is not None, "Data must not be None."

        # Parse trigger effects
        trigger_effects = []
        for effect_data in data.get("trigger_effects", []):
            trigger_effects.append(Effect.from_dict(effect_data))

        # Parse damage bonus components
        damage_bonus = []
        for damage_data in data.get("damage_bonus", []):
            damage_bonus.append(DamageComponent.from_dict(damage_data))

        return OnHitTrigger(
            name=data["name"],
            description=data.get("description", ""),
            max_duration=data.get("max_duration", 0),
            trigger_effects=trigger_effects,
            damage_bonus=damage_bonus,
            consumes_on_trigger=data.get("consumes_on_trigger", True),
            requires_concentration=data.get("requires_concentration", False),
        )


class OnLowHealthTrigger(Effect):
    """Effect that activates when the character's HP drops below a threshold percentage."""

    def __init__(
        self,
        name: str,
        description: str,
        hp_threshold_percent: float,  # 0.25 for 25% HP
        trigger_effects: list["Effect"],
        damage_bonus: list[DamageComponent] | None = None,
        consumes_on_trigger: bool = True,
    ):
        # No max_duration - these are permanent passive abilities
        super().__init__(
            name, description, max_duration=0, requires_concentration=False
        )
        self.hp_threshold_percent: float = hp_threshold_percent
        self.trigger_effects: list[Effect] = trigger_effects or []
        self.damage_bonus: list[DamageComponent] = damage_bonus or []
        self.consumes_on_trigger: bool = consumes_on_trigger
        self.has_triggered: bool = False  # Track if already activated
        self.validate()

    def validate(self):
        super().validate()
        assert (
            0.0 <= self.hp_threshold_percent <= 1.0
        ), "HP threshold must be between 0.0 and 1.0"
        assert isinstance(self.trigger_effects, list), "Trigger effects must be a list."
        for effect in self.trigger_effects:
            assert isinstance(
                effect, Effect
            ), f"Trigger effect '{effect}' must be of type Effect."
        assert isinstance(self.damage_bonus, list), "Damage bonus must be a list."
        for damage_comp in self.damage_bonus:
            assert isinstance(
                damage_comp, DamageComponent
            ), f"Damage component '{damage_comp}' must be of type DamageComponent."

    def can_apply(self, actor: Any, target: Any) -> bool:
        """OnLowHealthTrigger can be applied to any living target."""
        return target.is_alive()

    def should_trigger(self, character: Any) -> bool:
        """Check if the trigger condition is met and hasn't already been activated."""
        if self.has_triggered and self.consumes_on_trigger:
            return False

        hp_ratio = character.hp / character.HP_MAX if character.HP_MAX > 0 else 0
        return hp_ratio <= self.hp_threshold_percent

    def activate(
        self, character: Any
    ) -> tuple[list[DamageComponent], list[tuple[Effect, int]]]:
        """Activate the trigger and return damage bonuses and effects to apply."""
        self.has_triggered = True

        # Return damage bonuses and effects with mind level 0 (passive triggers don't use mind)
        trigger_effects_with_levels = [(effect, 0) for effect in self.trigger_effects]

        return self.damage_bonus.copy(), trigger_effects_with_levels

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["hp_threshold_percent"] = self.hp_threshold_percent
        data["trigger_effects"] = [effect.to_dict() for effect in self.trigger_effects]
        data["damage_bonus"] = [damage.to_dict() for damage in self.damage_bonus]
        data["consumes_on_trigger"] = self.consumes_on_trigger
        data["has_triggered"] = self.has_triggered
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "OnLowHealthTrigger":
        assert data is not None, "Data must not be None."

        # Parse trigger effects
        trigger_effects = []
        for effect_data in data.get("trigger_effects", []):
            trigger_effects.append(Effect.from_dict(effect_data))

        # Parse damage bonus components
        damage_bonus = []
        for damage_data in data.get("damage_bonus", []):
            damage_bonus.append(DamageComponent.from_dict(damage_data))

        trigger = OnLowHealthTrigger(
            name=data["name"],
            description=data.get("description", ""),
            hp_threshold_percent=data.get("hp_threshold_percent", 0.25),
            trigger_effects=trigger_effects,
            damage_bonus=damage_bonus,
            consumes_on_trigger=data.get("consumes_on_trigger", True),
        )

        # Restore triggered state if loading from save
        trigger.has_triggered = data.get("has_triggered", False)

        return trigger
