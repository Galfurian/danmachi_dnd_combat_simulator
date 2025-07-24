from typing import Any, Optional, Callable
from enum import Enum

from core.error_handling import log_error, log_warning
from combat.damage import DamageComponent

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


class TriggerEffect(Effect):
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
        duration: int,
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
            duration (int): Duration in turns (0 for permanent).
            trigger_condition (TriggerCondition): Condition that activates the trigger.
            trigger_effects (list[Effect]): Effects to apply when triggered.
            damage_bonus (list[DamageComponent], optional): Additional damage when triggered.
            consumes_on_trigger (bool): Whether the effect is consumed when triggered.
            cooldown_turns (int): Number of turns before trigger can activate again.
            max_triggers (int): Maximum number of times trigger can activate (-1 for unlimited).
        """
        super().__init__(name, description, duration)
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
        Validate the TriggerEffect effect's properties.

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
        """TriggerEffect effects can be applied to any living target."""
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
    condition = TriggerCondition(
        TriggerType.ON_HIT, description="when hitting with an attack"
    )
    return TriggerEffect(
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
    condition = TriggerCondition(TriggerType.ON_LOW_HEALTH, threshold=hp_threshold)
    return TriggerEffect(
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
    condition = TriggerCondition(
        TriggerType.ON_SPELL_CAST, spell_category=spell_category
    )
    return TriggerEffect(
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
    condition = TriggerCondition(TriggerType.ON_DAMAGE_TAKEN, damage_type=damage_type)
    return TriggerEffect(
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
    condition = TriggerCondition(trigger_type)
    return TriggerEffect(
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
    condition = TriggerCondition(
        TriggerType.ON_CRITICAL_HIT, description="when scoring a critical hit"
    )
    return TriggerEffect(
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
    condition = TriggerCondition(
        TriggerType.ON_KILL, description="when defeating an enemy"
    )
    return TriggerEffect(
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
    condition = TriggerCondition(
        TriggerType.ON_HIT,  # Placeholder type for custom conditions
        custom_condition=custom_condition,
        description=description,
    )
    return TriggerEffect(
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

    return TriggerEffect(
        name=config["name"],
        description=config["description"],
        duration=config.get("duration", 0),
        trigger_condition=condition,
        trigger_effects=trigger_effects,
        damage_bonus=damage_bonus,
        consumes_on_trigger=config.get("consumes", True),
        cooldown_turns=config.get("cooldown", 0),
        max_triggers=config.get("max_uses", -1),
    )
