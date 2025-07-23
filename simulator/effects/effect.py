from typing import Any, Optional, Union

from core.constants import (
    BonusType,
    get_effect_emoji,
    apply_character_type_color,
    apply_damage_type_color,
    get_damage_type_emoji,
    apply_effect_color,
)
from core.error_handling import log_error, log_warning, log_critical
from core.utils import cprint, roll_and_describe
from combat.damage import DamageComponent


class Effect:
    """
    Base class for all game effects that can be applied to characters.

    Effects can modify character stats, deal damage over time, provide healing,
    or trigger special behaviors under certain conditions.
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        max_duration: int = 0,
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

        self.name: str = name
        self.description: str = description
        self.max_duration: int = max_duration

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

    def validate(self) -> None:
        """
        Validate the effect's properties.

        Raises:
            ValueError: If any property validation fails.
        """
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
        """Convert the effect to a dictionary representation."""
        from .effect_serialization import EffectSerializer

        return EffectSerializer.serialize(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Effect | None":
        """Creates an Effect instance from a dictionary representation.

        Args:
            data (dict[str, Any]): The dictionary representation of the effect.

        Returns:
            Effect: An instance of the Effect class.
        """
        from .effect_serialization import EffectDeserializer

        return EffectDeserializer.deserialize(data)


# =============================================================================
# TRIGGER SYSTEM
# =============================================================================

from typing import Callable
from enum import Enum


class TriggerType(Enum):
    """Enumeration of available trigger types for OnTrigger effects."""

    ON_HIT = "on_hit"  # When character hits with an attack
    ON_BEING_HIT = "on_being_hit"  # When character is hit by an attack
    ON_LOW_HEALTH = "on_low_health"  # When HP drops below threshold
    ON_HIGH_HEALTH = "on_high_health"  # When HP rises above threshold
    ON_TURN_START = "on_turn_start"  # At the beginning of character's turn
    ON_TURN_END = "on_turn_end"  # At the end of character's turn
    ON_DEATH = "on_death"  # When character reaches 0 HP
    ON_HEAL = "on_heal"  # When character is healed
    ON_SPELL_CAST = "on_spell_cast"  # When character casts a spell
    ON_CRITICAL_HIT = "on_critical_hit"  # When character scores a critical hit
    ON_MISS = "on_miss"  # When character misses an attack
    ON_DAMAGE_TAKEN = "on_damage_taken"  # When character takes damage
    ON_KILL = "on_kill"  # When character defeats an enemy


class TriggerCondition:
    """
    Defines the condition that must be met for a trigger to activate.

    This class provides a flexible way to define various trigger conditions
    with parameters, thresholds, and custom validation logic.
    """

    def __init__(
        self,
        trigger_type: TriggerType,
        threshold: Optional[float] = None,
        damage_type: Optional[Any] = None,
        spell_category: Optional[Any] = None,
        custom_condition: Optional[Callable[[Any, dict], bool]] = None,
        description: str = "",
    ):
        """
        Initialize a trigger condition.

        Args:
            trigger_type (TriggerType): The type of trigger event.
            threshold (Optional[float]): Numerical threshold (e.g., 0.25 for 25% HP).
            damage_type (Optional[Any]): Specific damage type to trigger on.
            spell_category (Optional[Any]): Specific spell category to trigger on.
            custom_condition (Optional[Callable]): Custom validation function.
            description (str): Human-readable description of the condition.
        """
        self.trigger_type = trigger_type
        self.threshold = threshold
        self.damage_type = damage_type
        self.spell_category = spell_category
        self.custom_condition = custom_condition
        self.description = description or self._generate_description()

    def _generate_description(self) -> str:
        """Generate a human-readable description of the trigger condition."""
        if self.trigger_type == TriggerType.ON_LOW_HEALTH:
            return f"when HP drops below {(self.threshold or 0.25) * 100:.0f}%"
        elif self.trigger_type == TriggerType.ON_HIGH_HEALTH:
            return f"when HP rises above {(self.threshold or 0.75) * 100:.0f}%"
        elif self.trigger_type == TriggerType.ON_DAMAGE_TAKEN and self.damage_type:
            return f"when taking {self.damage_type.name.lower()} damage"
        elif self.trigger_type == TriggerType.ON_SPELL_CAST and self.spell_category:
            return f"when casting {self.spell_category.name.lower()} spells"
        else:
            return self.trigger_type.value.replace("_", " ")

    def is_met(self, character: Any, event_data: dict[str, Any]) -> bool:
        """
        Check if the trigger condition is met.

        Args:
            character (Any): The character to evaluate the condition for.
            event_data (dict[str, Any]): Context data about the triggering event.

        Returns:
            bool: True if the condition is met, False otherwise.
        """
        try:
            # Handle custom conditions first
            if self.custom_condition:
                return self.custom_condition(character, event_data)

            # Handle standard trigger types
            if self.trigger_type == TriggerType.ON_LOW_HEALTH:
                threshold = self.threshold or 0.25
                hp_ratio = (
                    character.hp / character.HP_MAX if character.HP_MAX > 0 else 0
                )
                return hp_ratio <= threshold

            elif self.trigger_type == TriggerType.ON_HIGH_HEALTH:
                threshold = self.threshold or 0.75
                hp_ratio = (
                    character.hp / character.HP_MAX if character.HP_MAX > 0 else 0
                )
                return hp_ratio >= threshold

            elif self.trigger_type == TriggerType.ON_DAMAGE_TAKEN:
                if self.damage_type:
                    return event_data.get("damage_type") == self.damage_type
                return event_data.get("damage_taken", 0) > 0

            elif self.trigger_type == TriggerType.ON_SPELL_CAST:
                if self.spell_category:
                    return event_data.get("spell_category") == self.spell_category
                return event_data.get("spell_cast") is not None

            # Simple event-based triggers
            elif self.trigger_type in [
                TriggerType.ON_HIT,
                TriggerType.ON_BEING_HIT,
                TriggerType.ON_TURN_START,
                TriggerType.ON_TURN_END,
                TriggerType.ON_DEATH,
                TriggerType.ON_HEAL,
                TriggerType.ON_CRITICAL_HIT,
                TriggerType.ON_MISS,
                TriggerType.ON_KILL,
            ]:
                return event_data.get("event_type") == self.trigger_type.value

            return False

        except Exception as e:
            log_error(
                f"Error evaluating trigger condition: {str(e)}",
                {
                    "trigger_type": self.trigger_type.value,
                    "character": getattr(character, "name", "unknown"),
                },
                e,
            )
            return False


class OnTriggerEffect(Effect):
    """
    Universal trigger effect that can respond to various game events.

    This unified system allows for flexible trigger-based effects that can
    activate on hits, health thresholds, spell casts, and many other conditions.
    Effects can stack, have cooldowns, and provide both immediate and ongoing benefits.
    """

    def __init__(
        self,
        name: str,
        description: str,
        max_duration: int,
        trigger_condition: TriggerCondition,
        trigger_effects: list["Effect"],
        damage_bonus: list[DamageComponent] | None = None,
        consumes_on_trigger: bool = True,
        cooldown_turns: int = 0,
        max_triggers: int = -1,  # -1 for unlimited
    ):
        """
        Initialize a universal trigger effect.

        Args:
            name (str): Name of the effect.
            description (str): Description of what the effect does.
            max_duration (int): Maximum duration in turns (0 for permanent).
            trigger_condition (TriggerCondition): Condition that activates the trigger.
            trigger_effects (list[Effect]): Effects to apply when triggered.
            damage_bonus (list[DamageComponent], optional): Additional damage when triggered.
            consumes_on_trigger (bool): Whether the effect is consumed when triggered.
            cooldown_turns (int): Number of turns before trigger can activate again.
            max_triggers (int): Maximum number of times trigger can activate (-1 for unlimited).
        """
        super().__init__(name, description, max_duration)
        self.trigger_condition = trigger_condition
        self.trigger_effects: list[Effect] = trigger_effects or []
        self.damage_bonus: list[DamageComponent] = damage_bonus or []
        self.consumes_on_trigger = consumes_on_trigger
        self.cooldown_turns = cooldown_turns
        self.max_triggers = max_triggers

        # Runtime state
        self.triggers_used = 0
        self.cooldown_remaining = 0
        self.has_triggered_this_turn = False

        self.validate()

    def validate(self) -> None:
        """
        Validate the OnTriggerEffect effect's properties.

        Raises:
            AssertionError: If validation conditions are not met.
        """
        super().validate()
        assert isinstance(
            self.trigger_condition, TriggerCondition
        ), "Trigger condition must be a TriggerCondition instance."
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
        assert self.cooldown_turns >= 0, "Cooldown turns must be non-negative."
        assert (
            self.max_triggers >= -1
        ), "Max triggers must be -1 (unlimited) or positive."

    def can_apply(self, actor: Any, target: Any) -> bool:
        """OnTriggerEffect effects can be applied to any living target."""
        return target.is_alive()

    def can_trigger(self) -> bool:
        """
        Check if the trigger is currently available to activate.

        Returns:
            bool: True if the trigger can activate, False otherwise.
        """
        # Check if we've exceeded max triggers
        if self.max_triggers > 0 and self.triggers_used >= self.max_triggers:
            return False

        # Check if we're on cooldown
        if self.cooldown_remaining > 0:
            return False

        # Check if we've already triggered this turn (for per-turn limits)
        if self.has_triggered_this_turn and self.trigger_condition.trigger_type in [
            TriggerType.ON_TURN_START,
            TriggerType.ON_TURN_END,
        ]:
            return False

        return True

    def check_trigger(self, character: Any, event_data: dict[str, Any]) -> bool:
        """
        Check if the trigger should activate based on the current event.

        Args:
            character (Any): The character with this effect.
            event_data (dict[str, Any]): Context about the triggering event.

        Returns:
            bool: True if the trigger should activate, False otherwise.
        """
        if not self.can_trigger():
            return False

        return self.trigger_condition.is_met(character, event_data)

    def activate_trigger(
        self, character: Any, event_data: dict[str, Any]
    ) -> tuple[list[DamageComponent], list[tuple[Effect, int]]]:
        """
        Activate the trigger and return effects and damage bonuses.

        Args:
            character (Any): The character activating the trigger.
            event_data (dict[str, Any]): Context about the triggering event.

        Returns:
            tuple[list[DamageComponent], list[tuple[Effect, int]]]: Damage bonuses and effects with mind levels.
        """
        self.triggers_used += 1
        self.cooldown_remaining = self.cooldown_turns
        self.has_triggered_this_turn = True

        # Get mind level from event data or default to 1
        mind_level = event_data.get("mind_level", 1)

        # Prepare effects with mind levels
        trigger_effects_with_levels = [
            (effect, mind_level) for effect in self.trigger_effects
        ]

        # Log the trigger activation
        log_warning(
            f"Trigger activated: {self.name}",
            {
                "character": character.name,
                "trigger_type": self.trigger_condition.trigger_type.value,
                "triggers_used": self.triggers_used,
                "cooldown_set": self.cooldown_turns,
            },
        )

        return self.damage_bonus.copy(), trigger_effects_with_levels

    def turn_update(self, actor: Any, target: Any, mind_level: int = 0) -> None:
        """
        Update trigger state at the start/end of turns.

        Args:
            actor (Any): The character who applied the effect.
            target (Any): The character with the effect.
            mind_level (int): The mind level (unused for triggers).
        """
        super().turn_update(actor, target, mind_level)

        # Reset per-turn flags
        self.has_triggered_this_turn = False

        # Reduce cooldown
        if self.cooldown_remaining > 0:
            self.cooldown_remaining -= 1

    def get_status_text(self) -> str:
        """
        Get a human-readable status of the trigger effect.

        Returns:
            str: Status description including triggers used, cooldown, etc.
        """
        status_parts = [self.trigger_condition.description]

        if self.max_triggers > 0:
            status_parts.append(f"({self.triggers_used}/{self.max_triggers} uses)")
        elif self.triggers_used > 0:
            status_parts.append(f"({self.triggers_used} uses)")

        if self.cooldown_remaining > 0:
            status_parts.append(f"(cooldown: {self.cooldown_remaining} turns)")

        return " ".join(status_parts)


# =============================================================================
# CONVENIENCE FACTORY FUNCTIONS
# =============================================================================


def create_on_hit_trigger(
    name: str,
    description: str,
    trigger_effects: list[Effect],
    damage_bonus: list[DamageComponent] | None = None,
    duration: int = 0,
    consumes_on_trigger: bool = True,
    cooldown: int = 0,
    max_uses: int = -1,
) -> OnTriggerEffect:
    """
    Create a OnTriggerEffect that activates when the character hits with an attack.

    Args:
        name (str): Name of the trigger effect.
        description (str): Description of what the trigger does.
        trigger_effects (list[Effect]): Effects to apply when triggered.
        damage_bonus (list[DamageComponent], optional): Additional damage when triggered.
        duration (int): Duration in turns (0 for permanent). Defaults to 0.
        consumes_on_trigger (bool): Whether consumed after triggering. Defaults to True.
        cooldown (int): Turns before trigger can activate again. Defaults to 0.
        max_uses (int): Maximum activations (-1 for unlimited). Defaults to -1.

    Returns:
        OnTriggerEffect: The created trigger effect.
    """
    condition = TriggerCondition(
        TriggerType.ON_HIT, description="when hitting with an attack"
    )
    return OnTriggerEffect(
        name,
        description,
        duration,
        condition,
        trigger_effects,
        damage_bonus,
        consumes_on_trigger,
        cooldown,
        max_uses,
    )


def create_low_health_trigger(
    name: str,
    description: str,
    hp_threshold: float,
    trigger_effects: list[Effect],
    damage_bonus: list[DamageComponent] | None = None,
    duration: int = 0,
    consumes_on_trigger: bool = True,
    cooldown: int = 0,
    max_uses: int = -1,
) -> OnTriggerEffect:
    """
    Create a OnTriggerEffect that activates when HP drops below a threshold.

    Args:
        name (str): Name of the trigger effect.
        description (str): Description of what the trigger does.
        hp_threshold (float): HP percentage threshold (0.25 for 25%).
        trigger_effects (list[Effect]): Effects to apply when triggered.
        damage_bonus (list[DamageComponent], optional): Additional damage when triggered.
        duration (int): Duration in turns (0 for permanent). Defaults to 0.
        consumes_on_trigger (bool): Whether consumed after triggering. Defaults to True.
        cooldown (int): Turns before trigger can activate again. Defaults to 0.
        max_uses (int): Maximum activations (-1 for unlimited). Defaults to -1.

    Returns:
        OnTriggerEffect: The created trigger effect.
    """
    condition = TriggerCondition(TriggerType.ON_LOW_HEALTH, threshold=hp_threshold)
    return OnTriggerEffect(
        name,
        description,
        duration,
        condition,
        trigger_effects,
        damage_bonus,
        consumes_on_trigger,
        cooldown,
        max_uses,
    )


def create_spell_cast_trigger(
    name: str,
    description: str,
    trigger_effects: list[Effect],
    spell_category: Optional[Any] = None,
    damage_bonus: list[DamageComponent] | None = None,
    duration: int = 0,
    cooldown: int = 0,
    max_uses: int = -1,
) -> OnTriggerEffect:
    """
    Create a OnTriggerEffect that activates when casting spells.

    Args:
        name (str): Name of the trigger effect.
        description (str): Description of what the trigger does.
        trigger_effects (list[Effect]): Effects to apply when triggered.
        spell_category (Optional[Any]): Specific spell category to trigger on.
        damage_bonus (list[DamageComponent], optional): Additional damage when triggered.
        duration (int): Duration in turns (0 for permanent). Defaults to 0.
        cooldown (int): Turns before trigger can activate again. Defaults to 0.
        max_uses (int): Maximum activations (-1 for unlimited). Defaults to -1.

    Returns:
        OnTriggerEffect: The created trigger effect.
    """
    condition = TriggerCondition(
        TriggerType.ON_SPELL_CAST, spell_category=spell_category
    )
    return OnTriggerEffect(
        name,
        description,
        duration,
        condition,
        trigger_effects,
        damage_bonus,
        False,
        cooldown,
        max_uses,
    )  # Don't consume by default for spell triggers


def create_damage_taken_trigger(
    name: str,
    description: str,
    trigger_effects: list[Effect],
    damage_type: Optional[Any] = None,
    damage_bonus: list[DamageComponent] | None = None,
    duration: int = 0,
    cooldown: int = 1,
    max_uses: int = -1,
) -> OnTriggerEffect:
    """
    Create a OnTriggerEffect that activates when taking damage.

    Args:
        name (str): Name of the trigger effect.
        description (str): Description of what the trigger does.
        trigger_effects (list[Effect]): Effects to apply when triggered.
        damage_type (Optional[Any]): Specific damage type to trigger on.
        damage_bonus (list[DamageComponent], optional): Additional damage when triggered.
        duration (int): Duration in turns (0 for permanent). Defaults to 0.
        cooldown (int): Turns before trigger can activate again. Defaults to 1.
        max_uses (int): Maximum activations (-1 for unlimited). Defaults to -1.

    Returns:
        OnTriggerEffect: The created trigger effect.
    """
    condition = TriggerCondition(TriggerType.ON_DAMAGE_TAKEN, damage_type=damage_type)
    return OnTriggerEffect(
        name,
        description,
        duration,
        condition,
        trigger_effects,
        damage_bonus,
        False,
        cooldown,
        max_uses,
    )


def create_turn_based_trigger(
    name: str,
    description: str,
    trigger_effects: list[Effect],
    trigger_on_start: bool = True,
    duration: int = 0,
    max_uses: int = -1,
) -> OnTriggerEffect:
    """
    Create a OnTriggerEffect that activates at turn start or end.

    Args:
        name (str): Name of the trigger effect.
        description (str): Description of what the trigger does.
        trigger_effects (list[Effect]): Effects to apply when triggered.
        trigger_on_start (bool): True for turn start, False for turn end. Defaults to True.
        duration (int): Duration in turns (0 for permanent). Defaults to 0.
        max_uses (int): Maximum activations (-1 for unlimited). Defaults to -1.

    Returns:
        OnTriggerEffect: The created trigger effect.
    """
    trigger_type = (
        TriggerType.ON_TURN_START if trigger_on_start else TriggerType.ON_TURN_END
    )
    condition = TriggerCondition(trigger_type)
    return OnTriggerEffect(
        name,
        description,
        duration,
        condition,
        trigger_effects,
        None,
        False,
        0,
        max_uses,
    )


def create_critical_hit_trigger(
    name: str,
    description: str,
    trigger_effects: list[Effect],
    damage_bonus: list[DamageComponent] | None = None,
    duration: int = 0,
    consumes_on_trigger: bool = True,
    cooldown: int = 0,
) -> OnTriggerEffect:
    """
    Create a OnTriggerEffect that activates on critical hits.

    Args:
        name (str): Name of the trigger effect.
        description (str): Description of what the trigger does.
        trigger_effects (list[Effect]): Effects to apply when triggered.
        damage_bonus (list[DamageComponent], optional): Additional damage when triggered.
        duration (int): Duration in turns (0 for permanent). Defaults to 0.
        consumes_on_trigger (bool): Whether consumed after triggering. Defaults to True.
        cooldown (int): Turns before trigger can activate again. Defaults to 0.

    Returns:
        OnTriggerEffect: The created trigger effect.
    """
    condition = TriggerCondition(
        TriggerType.ON_CRITICAL_HIT, description="when scoring a critical hit"
    )
    return OnTriggerEffect(
        name,
        description,
        duration,
        condition,
        trigger_effects,
        damage_bonus,
        consumes_on_trigger,
        cooldown,
        -1,
    )


def create_kill_trigger(
    name: str,
    description: str,
    trigger_effects: list[Effect],
    damage_bonus: list[DamageComponent] | None = None,
    duration: int = 0,
    cooldown: int = 0,
    max_uses: int = -1,
) -> OnTriggerEffect:
    """
    Create a OnTriggerEffect that activates when defeating an enemy.

    Args:
        name (str): Name of the trigger effect.
        description (str): Description of what the trigger does.
        trigger_effects (list[Effect]): Effects to apply when triggered.
        damage_bonus (list[DamageComponent], optional): Additional damage when triggered.
        duration (int): Duration in turns (0 for permanent). Defaults to 0.
        cooldown (int): Turns before trigger can activate again. Defaults to 0.
        max_uses (int): Maximum activations (-1 for unlimited). Defaults to -1.

    Returns:
        OnTriggerEffect: The created trigger effect.
    """
    condition = TriggerCondition(
        TriggerType.ON_KILL, description="when defeating an enemy"
    )
    return OnTriggerEffect(
        name,
        description,
        duration,
        condition,
        trigger_effects,
        damage_bonus,
        False,
        cooldown,
        max_uses,
    )


def create_custom_trigger(
    name: str,
    description: str,
    custom_condition: Callable[[Any, dict], bool],
    trigger_effects: list[Effect],
    damage_bonus: list[DamageComponent] | None = None,
    duration: int = 0,
    consumes_on_trigger: bool = True,
    cooldown: int = 0,
    max_uses: int = -1,
) -> OnTriggerEffect:
    """
    Create a OnTriggerEffect with a custom condition function.

    Args:
        name (str): Name of the trigger effect.
        description (str): Description of what the trigger does.
        custom_condition (Callable): Function that evaluates trigger condition.
        trigger_effects (list[Effect]): Effects to apply when triggered.
        damage_bonus (list[DamageComponent], optional): Additional damage when triggered.
        duration (int): Duration in turns (0 for permanent). Defaults to 0.
        consumes_on_trigger (bool): Whether consumed after triggering. Defaults to True.
        cooldown (int): Turns before trigger can activate again. Defaults to 0.
        max_uses (int): Maximum activations (-1 for unlimited). Defaults to -1.

    Returns:
        OnTriggerEffect: The created trigger effect.
    """
    condition = TriggerCondition(
        TriggerType.ON_HIT,  # Placeholder type for custom conditions
        custom_condition=custom_condition,
        description=description,
    )
    return OnTriggerEffect(
        name,
        description,
        duration,
        condition,
        trigger_effects,
        damage_bonus,
        consumes_on_trigger,
        cooldown,
        max_uses,
    )


# =============================================================================
# JSON FACTORY FUNCTIONS FOR EASY CONFIGURATION
# =============================================================================


def create_trigger_from_json_config(config: dict[str, Any]) -> OnTriggerEffect:
    """
    Create a OnTriggerEffect from a simplified JSON configuration.

    This function provides a more user-friendly way to create triggers from JSON
    by handling common patterns and providing sensible defaults.

    Args:
        config (dict[str, Any]): Simplified trigger configuration.

    Returns:
        OnTriggerEffect: The created trigger effect.

    Example JSON configs:
        {
            "type": "on_hit",
            "name": "Flame Weapon",
            "description": "Adds fire damage on hit",
            "damage_bonus": [{"roll": "1d6", "type": "fire"}],
            "duration": 10
        }

        {
            "type": "low_health",
            "name": "Berserker Rage",
            "description": "Gain attack bonus at low health",
            "threshold": 0.25,
            "effects": [{"class": "Buff", "modifiers": [...]}],
            "consumes": false
        }
    """
    trigger_type_map = {
        "on_hit": TriggerType.ON_HIT,
        "on_being_hit": TriggerType.ON_BEING_HIT,
        "low_health": TriggerType.ON_LOW_HEALTH,
        "high_health": TriggerType.ON_HIGH_HEALTH,
        "turn_start": TriggerType.ON_TURN_START,
        "turn_end": TriggerType.ON_TURN_END,
        "on_death": TriggerType.ON_DEATH,
        "on_heal": TriggerType.ON_HEAL,
        "spell_cast": TriggerType.ON_SPELL_CAST,
        "critical_hit": TriggerType.ON_CRITICAL_HIT,
        "on_miss": TriggerType.ON_MISS,
        "damage_taken": TriggerType.ON_DAMAGE_TAKEN,
        "on_kill": TriggerType.ON_KILL,
    }

    # Get trigger type
    trigger_type_str = config.get("type", "on_hit")
    trigger_type = trigger_type_map.get(trigger_type_str, TriggerType.ON_HIT)

    # Create condition
    condition = TriggerCondition(
        trigger_type=trigger_type,
        threshold=config.get("threshold"),
        # damage_type and spell_category would be resolved from strings here
        description=config.get("condition_description", ""),
    )

    # Parse trigger effects
    trigger_effects = []
    for effect_config in config.get("effects", []):
        effect = Effect.from_dict(effect_config)
        if effect:
            trigger_effects.append(effect)

    # Parse damage bonuses
    damage_bonus = []
    for dmg_config in config.get("damage_bonus", []):
        # This would create DamageComponent from the config
        # damage_bonus.append(DamageComponent(dmg_config["roll"], DamageType[dmg_config["type"]]))
        pass

    return OnTriggerEffect(
        name=config["name"],
        description=config["description"],
        max_duration=config.get("duration", 0),
        trigger_condition=condition,
        trigger_effects=trigger_effects,
        damage_bonus=damage_bonus,
        consumes_on_trigger=config.get("consumes", True),
        cooldown_turns=config.get("cooldown", 0),
        max_triggers=config.get("max_uses", -1),
    )


class Modifier:
    """
    Handles different types of modifiers that can be applied to characters.

    Modifiers represent bonuses or penalties to various character attributes
    such as HP, AC, damage, or other stats.
    """

    def __init__(self, bonus_type: BonusType, value: Union[str, int, DamageComponent]):
        self.bonus_type = bonus_type
        self.value = value
        self.validate()

    def validate(self) -> None:
        """
        Validate the modifier's properties.

        Raises:
            ValueError: If the bonus type or value is invalid.
            AssertionError: If validation conditions are not met.
        """
        assert isinstance(
            self.bonus_type, BonusType
        ), f"Bonus type '{self.bonus_type}' must be of type BonusType."

        if self.bonus_type == BonusType.DAMAGE:
            assert isinstance(
                self.value, DamageComponent
            ), f"Modifier value for '{self.bonus_type}' must be a DamageComponent."
        elif self.bonus_type == BonusType.ATTACK:
            assert isinstance(
                self.value, str
            ), f"Modifier value for '{self.bonus_type}' must be a string expression."
        elif self.bonus_type in [
            BonusType.HP,
            BonusType.MIND,
            BonusType.AC,
            BonusType.INITIATIVE,
        ]:
            # Should be either an integer or a string expression
            if not isinstance(self.value, (int, str)):
                raise ValueError(
                    f"Modifier value for '{self.bonus_type}' must be an integer or string expression."
                )
        else:
            raise ValueError(f"Unknown bonus type: {self.bonus_type}")

    def to_dict(self) -> dict[str, Any]:
        """Convert the modifier to a dictionary representation."""
        from .effect_serialization import ModifierSerializer

        return ModifierSerializer.serialize(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Modifier | None":
        """Create a Modifier instance from a dictionary representation."""
        from .effect_serialization import ModifierDeserializer

        return ModifierDeserializer.deserialize(data)

    def __eq__(self, other: object) -> bool:
        """
        Check if two modifiers are equal.

        Args:
            other (object): The other object to compare with.

        Returns:
            bool: True if the modifiers are equal, False otherwise.
        """
        if not isinstance(other, Modifier):
            return False
        return self.bonus_type == other.bonus_type and self.value == other.value

    def __hash__(self) -> int:
        """Make the modifier hashable for use in sets and dictionaries."""
        if isinstance(self.value, DamageComponent):
            # For DamageComponent, use its string representation for hashing
            return hash(
                (self.bonus_type, self.value.damage_roll, self.value.damage_type)
            )
        return hash((self.bonus_type, self.value))

    def __repr__(self) -> str:
        """String representation of the modifier."""
        return f"Modifier({self.bonus_type.name}, {self.value})"


class ModifierEffect(Effect):
    """
    Base class for effects that apply stat modifiers to characters.

    This includes buffs and debuffs that temporarily modify character attributes
    like HP, AC, damage bonuses, etc.
    """

    def __init__(
        self,
        name: str,
        description: str,
        max_duration: int,
        modifiers: list[Modifier],
    ):
        super().__init__(name, description, max_duration)
        self.modifiers: list[Modifier] = modifiers
        self.validate()

    def validate(self) -> None:
        """
        Validate the modifier effect's properties.

        Raises:
            AssertionError: If validation conditions are not met.
        """
        super().validate()
        assert isinstance(self.modifiers, list), "Modifiers must be a list."
        for modifier in self.modifiers:
            assert isinstance(
                modifier, Modifier
            ), f"Modifier '{modifier}' must be of type Modifier."

    def can_apply(self, actor: Any, target: Any) -> bool:
        """
        Check if the modifier effect can be applied to the target.

        Args:
            actor (Any): The character applying the effect.
            target (Any): The character receiving the effect.

        Returns:
            bool: True if the effect can be applied, False otherwise.
        """
        if not target.is_alive():
            return False
        # Check if the target is already affected by the same modifiers.
        for modifier in self.modifiers:
            existing_modifiers = target.effects_module.get_modifier(modifier.bonus_type)
            if not existing_modifiers:
                continue
            # Check if the target already has this exact modifier
            if modifier in existing_modifiers:
                return False
        return True


class BuffEffect(ModifierEffect):
    """
    Positive effect that applies beneficial modifiers to a character.

    Buffs provide temporary bonuses to character attributes such as increased
    damage, improved AC, or additional HP.
    """

    def __init__(
        self,
        name: str,
        description: str,
        max_duration: int,
        modifiers: list[Modifier],
    ):
        super().__init__(name, description, max_duration, modifiers)


class DebuffEffect(ModifierEffect):
    """
    Negative effect that applies detrimental modifiers to a character.

    Debuffs provide temporary penalties to character attributes such as reduced
    damage, lowered AC, or decreased HP.
    """

    def __init__(
        self,
        name: str,
        description: str,
        max_duration: int,
        modifiers: list[Modifier],
    ):
        super().__init__(name, description, max_duration, modifiers)


class DamageOverTimeEffect(Effect):
    """
    Damage over Time effect that deals damage each turn.

    Damage over Time effects continuously damage the target for a specified duration,
    using a damage roll expression that can include variables like MIND level.
    """

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

    def turn_update(
        self, actor: Any, target: Any, mind_level: Optional[int] = 1
    ) -> None:
        """
        Apply damage over time to the target.

        Args:
            actor (Any): The character who applied the DoT effect.
            target (Any): The character receiving the damage.
            mind_level (Optional[int]): The mind level for damage calculation. Defaults to 1.
        """
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        # Calculate the damage amount using the provided expression.
        dot_value, dot_desc, _ = roll_and_describe(self.damage.damage_roll, variables)
        # Asser that the damage value is a positive integer.
        assert (
            isinstance(dot_value, int) and dot_value >= 0
        ), f"DamageOverTimeEffect '{self.name}' must have a non-negative integer damage value, got {dot_value}."
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

    def validate(self) -> None:
        """
        Validate the DoT effect's properties.

        Raises:
            AssertionError: If validation conditions are not met.
        """
        super().validate()
        assert self.max_duration > 0, "DamageOverTimeEffect duration must be greater than 0."
        assert isinstance(
            self.damage, DamageComponent
        ), "Damage must be of type DamageComponent."


class HealingOverTimeEffect(Effect):
    """
    Heal over Time effect that heals the target each turn.

    Healing over Time effects continuously heal the target for a specified duration,
    using a heal expression that can include variables like MIND level.
    """

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

    def turn_update(
        self, actor: Any, target: Any, mind_level: Optional[int] = 1
    ) -> None:
        """
        Apply healing over time to the target.

        Args:
            actor (Any): The character who applied the HoT effect.
            target (Any): The character receiving the healing.
            mind_level (Optional[int]): The mind level for healing calculation. Defaults to 1.
        """
        variables = actor.get_expression_variables()
        variables["MIND"] = mind_level
        # Calculate the heal amount using the provided expression.
        hot_value, hot_desc, _ = roll_and_describe(self.heal_per_turn, variables)
        # Assert that the heal value is a positive integer.
        assert (
            isinstance(hot_value, int) and hot_value >= 0
        ), f"HealingOverTimeEffect '{self.name}' must have a non-negative integer heal value, got {hot_value}."
        # Apply the heal to the target.
        hot_value = target.heal(hot_value)
        # If the heal value is positive, print the heal message.
        message = f"    {get_effect_emoji(self)} "
        message += apply_character_type_color(target.type, target.name)
        message += f" heals for {hot_value} ([white]{hot_desc}[/]) hp from "
        message += apply_effect_color(self, self.name) + "."
        cprint(message)

    def validate(self) -> None:
        """
        Validate the HoT effect's properties.

        Raises:
            AssertionError: If validation conditions are not met.
        """
        super().validate()
        assert self.max_duration > 0, "HealingOverTimeEffect duration must be greater than 0."
        assert isinstance(
            self.heal_per_turn, str
        ), "Heal per turn must be a string expression."


class IncapacitatingEffect(Effect):
    """
    Effect that prevents a character from taking actions.

    Unlike ModifierEffect which only applies stat penalties, IncapacitatingEffect
    completely prevents the character from acting during their turn.
    """

    def __init__(
        self,
        name: str,
        description: str,
        max_duration: int,
        incapacitation_type: str = "general",  # "sleep", "paralyzed", "stunned", etc.
        save_ends: bool = False,
        save_dc: int = 0,
        save_stat: str = "CON",
    ):
        super().__init__(name, description, max_duration)
        self.incapacitation_type = incapacitation_type
        self.save_ends = save_ends
        self.save_dc = save_dc
        self.save_stat = save_stat

    def prevents_actions(self) -> bool:
        """
        Check if this effect prevents the character from taking actions.

        Returns:
            bool: True if actions are prevented, False otherwise.
        """
        return True

    def prevents_movement(self) -> bool:
        """
        Check if this effect prevents movement.

        Returns:
            bool: True if movement is prevented, False otherwise.
        """
        return self.incapacitation_type in ["paralyzed", "stunned", "unconscious"]

    def auto_fails_saves(self) -> bool:
        """
        Check if character automatically fails certain saves.

        Returns:
            bool: True if saves are automatically failed, False otherwise.
        """
        return self.incapacitation_type in ["unconscious"]

    def can_apply(self, actor: Any, target: Any) -> bool:
        """Incapacitating effects can be applied to any living target."""
        return target.is_alive()
