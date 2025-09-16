from typing import Any, ClassVar, Optional, Callable
from enum import Enum

from combat.damage import DamageComponent
from pydantic import BaseModel, Field, model_validator

from .base_effect import Effect


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


class TriggerCondition(BaseModel):
    """
    Defines the condition that must be met for a trigger to activate.

    This class provides a flexible way to define various trigger conditions
    with parameters, thresholds, and custom validation logic.
    """

    trigger_type: TriggerType = Field(
        ...,
        description="Type of trigger event.",
    )
    threshold: float | None = Field(
        default=None,
        description="Numerical threshold (e.g., 0.25 for 25% HP).",
    )
    damage_type: Any | None = Field(
        default=None,
        description="Specific damage type to trigger on (if applicable).",
    )
    spell_category: Any | None = Field(
        default=None,
        description="Specific spell category to trigger on (if applicable).",
    )
    custom_condition: Optional[Callable[[Any, dict], bool]] = Field(
        default=None,
        description="Custom function to evaluate the trigger condition.",
    )
    description: str = Field(
        default="",
        description="Human-readable description of the condition.",
    )

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
            print(
                f"Error evaluating trigger condition: {str(e)}",
                {
                    "trigger_type": self.trigger_type.value,
                    "character": getattr(character, "name", "unknown"),
                },
                e,
            )
            return False


class TriggerEffect(Effect):
    """
    Universal trigger effect that can respond to various game events.

    This unified system allows for flexible trigger-based effects that can
    activate on hits, health thresholds, spell casts, and many other conditions.
    Effects can stack, have cooldowns, and provide both immediate and ongoing benefits.
    """

    trigger_condition: TriggerCondition = Field(
        ...,
        description="Condition that activates the trigger.",
    )
    trigger_effects: list[Effect] = Field(
        ..., description="Effects to apply when triggered."
    )
    damage_bonus: list[DamageComponent] | None = Field(
        default_factory=list,
        description="Additional damage components applied when triggered.",
    )
    consumes_on_trigger: bool = Field(
        True,
        description="Whether the effect is consumed when triggered.",
    )
    cooldown_turns: int = Field(
        0,
        ge=0,
        description="Number of turns before trigger can activate again.",
    )
    max_triggers: int | None = Field(
        None,
        description="Maximum number of times trigger can activate (None for unlimited).",
    )

    # Runtime state.
    triggers_used: ClassVar[int] = 0
    cooldown_remaining: ClassVar[int] = 0
    has_triggered_this_turn: ClassVar[bool] = False

    @model_validator(mode="after")
    def check_trigger_condition(self) -> Any:
        if not isinstance(self.trigger_condition, TriggerCondition):
            raise ValueError("Trigger condition must be a TriggerCondition instance.")
        if not self.trigger_condition.description:
            self.trigger_condition.description = (
                self.trigger_condition._generate_description()
            )
        return self

    @model_validator(mode="after")
    def check_trigger_effects(self) -> Any:
        if not self.trigger_effects or not isinstance(self.trigger_effects, list):
            raise ValueError(
                "Trigger effects must be a non-empty list of Effect instances."
            )
        for effect in self.trigger_effects:
            if not isinstance(effect, Effect):
                raise ValueError(
                    f"Each trigger effect must be an Effect instance, got {type(effect)}"
                )
        return self

    @model_validator(mode="after")
    def check_damage_bonus(self) -> Any:
        if self.damage_bonus is None:
            self.damage_bonus = []
        elif not isinstance(self.damage_bonus, list):
            raise ValueError(
                "Damage bonus must be a list of DamageComponent instances."
            )
        else:
            for dmg in self.damage_bonus:
                if not isinstance(dmg, DamageComponent):
                    raise ValueError(
                        f"Each damage bonus must be a DamageComponent instance, got {type(dmg)}"
                    )
        return self

    @model_validator(mode="after")
    def check_cooldown_turns(self) -> Any:
        if self.cooldown_turns < 0:
            raise ValueError("Cooldown turns must be non-negative.")
        return self

    @model_validator(mode="after")
    def check_max_triggers(self) -> Any:
        if self.max_triggers is not None and self.max_triggers < 0:
            raise ValueError("Max triggers must be None (unlimited) or non-negative.")
        return self

    def can_apply(self, actor: Any, target: Any) -> bool:
        """TriggerEffect effects can be applied to any living target."""
        return target.is_alive()

    def can_trigger(self) -> bool:
        """
        Check if the trigger is currently available to activate.

        Returns:
            bool: True if the trigger can activate, False otherwise.
        """
        # Check if we've exceeded max triggers (None means unlimited)
        if self.max_triggers is not None and self.triggers_used >= self.max_triggers:
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
        self,
        character: Any,
        event_data: dict[str, Any],
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

        assert self.damage_bonus is not None

        return self.damage_bonus, trigger_effects_with_levels

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

        if self.max_triggers is not None:
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
    duration: int | None = None,
    consumes_on_trigger: bool = True,
    cooldown: int = 0,
    max_uses: int = -1,
) -> TriggerEffect:
    """
    Create a TriggerEffect that activates when the character hits with an attack.

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
        TriggerEffect: The created trigger effect.
    """
    trigger_condition = TriggerCondition(
        trigger_type=TriggerType.ON_HIT,
        description="when hitting with an attack",
    )
    return TriggerEffect(
        name=name,
        description=description,
        duration=duration,
        trigger_condition=trigger_condition,
        trigger_effects=trigger_effects,
        damage_bonus=damage_bonus,
        consumes_on_trigger=consumes_on_trigger,
        cooldown_turns=cooldown,
        max_triggers=max_uses,
    )


def create_low_health_trigger(
    name: str,
    description: str,
    hp_threshold: float,
    trigger_effects: list[Effect],
    damage_bonus: list[DamageComponent] | None = None,
    duration: int | None = None,
    consumes_on_trigger: bool = True,
    cooldown: int = 0,
    max_uses: int = -1,
) -> TriggerEffect:
    """
    Create a TriggerEffect that activates when HP drops below a threshold.

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
        TriggerEffect: The created trigger effect.
    """
    trigger_condition = TriggerCondition(
        trigger_type=TriggerType.ON_LOW_HEALTH,
        threshold=hp_threshold,
    )
    return TriggerEffect(
        name=name,
        description=description,
        duration=duration,
        trigger_condition=trigger_condition,
        trigger_effects=trigger_effects,
        damage_bonus=damage_bonus,
        consumes_on_trigger=consumes_on_trigger,
        cooldown_turns=cooldown,
        max_triggers=max_uses,
    )


def create_spell_cast_trigger(
    name: str,
    description: str,
    trigger_effects: list[Effect],
    spell_category: Optional[Any] = None,
    damage_bonus: list[DamageComponent] | None = None,
    duration: int | None = None,
    cooldown: int = 0,
    max_uses: int = -1,
) -> TriggerEffect:
    """
    Create a TriggerEffect that activates when casting spells.

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
        TriggerEffect: The created trigger effect.
    """
    trigger_condition = TriggerCondition(
        trigger_type=TriggerType.ON_SPELL_CAST,
        spell_category=spell_category,
    )
    return TriggerEffect(
        name=name,
        description=description,
        duration=duration,
        trigger_condition=trigger_condition,
        trigger_effects=trigger_effects,
        damage_bonus=damage_bonus,
        consumes_on_trigger=False,
        cooldown_turns=cooldown,
        max_triggers=max_uses,
    )  # Don't consume by default for spell triggers


def create_damage_taken_trigger(
    name: str,
    description: str,
    trigger_effects: list[Effect],
    damage_type: Optional[Any] = None,
    damage_bonus: list[DamageComponent] | None = None,
    duration: int | None = None,
    cooldown: int = 1,
    max_uses: int = -1,
) -> TriggerEffect:
    """
    Create a TriggerEffect that activates when taking damage.

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
        TriggerEffect: The created trigger effect.
    """
    trigger_condition = TriggerCondition(
        trigger_type=TriggerType.ON_DAMAGE_TAKEN,
        damage_type=damage_type,
    )
    return TriggerEffect(
        name=name,
        description=description,
        duration=duration,
        trigger_condition=trigger_condition,
        trigger_effects=trigger_effects,
        damage_bonus=damage_bonus,
        consumes_on_trigger=False,
        cooldown_turns=cooldown,
        max_triggers=max_uses,
    )


def create_turn_based_trigger(
    name: str,
    description: str,
    trigger_effects: list[Effect],
    trigger_on_start: bool = True,
    duration: int | None = None,
    max_uses: int = -1,
) -> TriggerEffect:
    """
    Create a TriggerEffect that activates at turn start or end.

    Args:
        name (str): Name of the trigger effect.
        description (str): Description of what the trigger does.
        trigger_effects (list[Effect]): Effects to apply when triggered.
        trigger_on_start (bool): True for turn start, False for turn end. Defaults to True.
        duration (int): Duration in turns (0 for permanent). Defaults to 0.
        max_uses (int): Maximum activations (-1 for unlimited). Defaults to -1.

    Returns:
        TriggerEffect: The created trigger effect.
    """
    trigger_type = (
        TriggerType.ON_TURN_START if trigger_on_start else TriggerType.ON_TURN_END
    )
    trigger_condition = TriggerCondition(
        trigger_type=trigger_type,
    )
    return TriggerEffect(
        name=name,
        description=description,
        duration=duration,
        trigger_condition=trigger_condition,
        trigger_effects=trigger_effects,
        damage_bonus=None,
        consumes_on_trigger=False,
        cooldown_turns=0,
        max_triggers=max_uses,
    )


def create_critical_hit_trigger(
    name: str,
    description: str,
    trigger_effects: list[Effect],
    damage_bonus: list[DamageComponent] | None = None,
    duration: int | None = None,
    consumes_on_trigger: bool = True,
    cooldown: int = 0,
) -> TriggerEffect:
    """
    Create a TriggerEffect that activates on critical hits.

    Args:
        name (str): Name of the trigger effect.
        description (str): Description of what the trigger does.
        trigger_effects (list[Effect]): Effects to apply when triggered.
        damage_bonus (list[DamageComponent], optional): Additional damage when triggered.
        duration (int): Duration in turns (0 for permanent). Defaults to 0.
        consumes_on_trigger (bool): Whether consumed after triggering. Defaults to True.
        cooldown (int): Turns before trigger can activate again. Defaults to 0.

    Returns:
        TriggerEffect: The created trigger effect.
    """
    trigger_condition = TriggerCondition(
        trigger_type=TriggerType.ON_CRITICAL_HIT,
        description="when scoring a critical hit",
    )
    return TriggerEffect(
        name=name,
        description=description,
        duration=duration,
        trigger_condition=trigger_condition,
        trigger_effects=trigger_effects,
        damage_bonus=damage_bonus,
        consumes_on_trigger=consumes_on_trigger,
        cooldown_turns=cooldown,
        max_triggers=-1,
    )


def create_kill_trigger(
    name: str,
    description: str,
    trigger_effects: list[Effect],
    damage_bonus: list[DamageComponent] | None = None,
    duration: int | None = None,
    cooldown: int = 0,
    max_uses: int = -1,
) -> TriggerEffect:
    """
    Create a TriggerEffect that activates when defeating an enemy.

    Args:
        name (str): Name of the trigger effect.
        description (str): Description of what the trigger does.
        trigger_effects (list[Effect]): Effects to apply when triggered.
        damage_bonus (list[DamageComponent], optional): Additional damage when triggered.
        duration (int): Duration in turns (0 for permanent). Defaults to 0.
        cooldown (int): Turns before trigger can activate again. Defaults to 0.
        max_uses (int): Maximum activations (-1 for unlimited). Defaults to -1.

    Returns:
        TriggerEffect: The created trigger effect.
    """
    trigger_condition = TriggerCondition(
        trigger_type=TriggerType.ON_KILL,
        description="when defeating an enemy",
    )
    return TriggerEffect(
        name=name,
        description=description,
        duration=duration,
        trigger_condition=trigger_condition,
        trigger_effects=trigger_effects,
        damage_bonus=damage_bonus,
        consumes_on_trigger=False,
        cooldown_turns=cooldown,
        max_triggers=max_uses,
    )


def create_custom_trigger(
    name: str,
    description: str,
    custom_condition: Callable[[Any, dict], bool],
    trigger_effects: list[Effect],
    damage_bonus: list[DamageComponent] | None = None,
    duration: int | None = None,
    consumes_on_trigger: bool = True,
    cooldown: int = 0,
    max_uses: int = -1,
) -> TriggerEffect:
    """
    Create a TriggerEffect with a custom condition function.

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
        TriggerEffect: The created trigger effect.
    """
    trigger_condition = TriggerCondition(
        trigger_type=TriggerType.ON_HIT,  # Placeholder type for custom conditions
        custom_condition=custom_condition,
        description=description,
    )
    return TriggerEffect(
        name=name,
        description=description,
        duration=duration,
        trigger_condition=trigger_condition,
        trigger_effects=trigger_effects,
        damage_bonus=damage_bonus,
        consumes_on_trigger=consumes_on_trigger,
        cooldown_turns=cooldown,
        max_triggers=max_uses,
    )


# =============================================================================
# JSON FACTORY FUNCTIONS FOR EASY CONFIGURATION
# =============================================================================


def create_trigger_from_json_config(config: dict[str, Any]) -> TriggerEffect:
    """
    Create a TriggerEffect from a simplified JSON configuration.

    This function provides a more user-friendly way to create triggers from JSON
    by handling common patterns and providing sensible defaults.

    Args:
        config (dict[str, Any]): Simplified trigger configuration.

    Returns:
        TriggerEffect: The created trigger effect.

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
    trigger_condition = TriggerCondition(
        trigger_type=trigger_type,
        threshold=config.get("threshold"),
        # damage_type and spell_category would be resolved from strings here
        description=config.get("condition_description", ""),
    )

    # Parse trigger effects
    trigger_effects = []
    for effect_config in config.get("effects", []):
        effect = Effect(**effect_config)
        if effect:
            trigger_effects.append(effect)

    # Parse damage bonuses
    damage_bonus = []
    for dmg_config in config.get("damage_bonus", []):
        # This would create DamageComponent from the config
        # damage_bonus.append(DamageComponent(dmg_config["roll"], DamageType[dmg_config["type"]]))
        pass

    return TriggerEffect(
        name=config["name"],
        description=config["description"],
        duration=config.get("duration", 0),
        trigger_condition=trigger_condition,
        trigger_effects=trigger_effects,
        damage_bonus=damage_bonus,
        consumes_on_trigger=config.get("consumes", True),
        cooldown_turns=config.get("cooldown", 0),
        max_triggers=config.get("max_triggers"),
    )
