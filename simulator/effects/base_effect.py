from typing import Any

from combat.damage import DamageComponent
from core.dice_parser import VarInfo
from core.utils import cprint
from pydantic import BaseModel, Field

from .event_system import DamageTakenEvent, HitEvent


class Effect(BaseModel):
    """
    Base class for all game effects that can be applied to characters.

    Effects can modify character stats, deal damage over time, provide healing,
    or trigger special behaviors under certain conditions.
    """

    name: str = Field(
        description="The name of the effect.",
    )
    description: str = Field(
        "",
        description="A brief description of the effect.",
    )
    duration: int | None = Field(
        default=None,
        description=(
            "The duration of the effect in turns. "
            "None for permanent effects, 0 for instant effects."
        ),
    )

    @property
    def display_name(self) -> str:
        return self.name.lower().capitalize()

    @property
    def color(self) -> str:
        """Returns the color string associated with this effect type."""
        return "dim white"  # Default fallback

    @property
    def colored_name(self) -> str:
        """Returns the effect name with color formatting applied."""
        return self.colorize(self.display_name)

    @property
    def emoji(self) -> str:
        """Returns the emoji associated with this effect type."""
        return "❔"  # Default fallback

    def colorize(self, message: str) -> str:
        """Applies effect color formatting to a message."""
        return f"[{self.color}]{message}[/]"

    def is_permanent(self) -> bool:
        """Check if the effect is permanent (i.e., has no duration limit).

        Returns:
            bool: True if the effect is permanent (None duration) or instant (0 duration), False otherwise.

        """
        return self.duration is None or self.duration <= 0

    def can_apply(
        self,
        actor: Any,
        target: Any,
    ) -> bool:
        """
        Check if the effect can be applied to the target.

        Args:
            actor (Character):
                The character applying the effect.
            target (Character):
                The character receiving the effect.

        Returns:
            bool:
                True if the effect can be applied, False otherwise.

        """
        from character.main import Character

        assert isinstance(actor, Character), "Actor must be an object"
        assert isinstance(target, Character), "Target must be an object"

        if actor.is_dead():
            cprint(f"    [bold red]{actor.name} is dead and cannot apply effects![/]")
            return False
        if target.is_dead():
            cprint(
                f"    [bold red]{target.name} is dead and cannot receive effects![/]"
            )
            return False
        # Check if the target is already affected by the same modifiers.
        return target.can_add_effect(
            actor,
            self,
            actor.get_expression_variables(),
        )


class EventResponse(BaseModel):
    """
    Represents a response to a combat event, indicating whether an effect should be removed.
    """

    effect: Effect = Field(
        description="The effect that generated this response.",
    )
    remove_effect: bool = Field(
        False,
        description="Indicates if the effect should be removed after handling the event.",
    )
    new_effects: list[Effect] = Field(
        default_factory=list,
        description="New effects to apply as a result of the event.",
    )
    damage_bonus: list[DamageComponent] = Field(
        default_factory=list,
        description="Additional damage components applied as a result of the event.",
    )
    message: str | None = Field(
        None,
        description="Optional message to display as a result of the event.",
    )


class ActiveEffect(BaseModel):
    """
    Represents an active effect applied to a character, including its source,
    target, effect details, mind level, and duration.
    """

    source: Any = Field(
        description="The source of the effect (the caster)",
    )
    target: Any = Field(
        description="The target of the effect (the recipient)",
    )
    effect: Effect = Field(
        description="The effect being applied",
    )
    duration: int | None = Field(
        default=None,
        description="Remaining duration in turns, None for indefinite effects",
    )
    variables: list[VarInfo] = Field(
        default_factory=list,
        description="List of variable info for dynamic calculations",
    )

    def turn_update(self) -> None:
        """
        Update the effect for the current turn by calling the effect's
        turn_update method.
        """
        raise NotImplementedError("Subclasses must implement turn_update.")

    def on_hit(self, event: HitEvent) -> EventResponse | None:
        """
        Handle hit event for the effect.

        Args:
            event (HitEvent):
                The hit event.

        Returns:
            EventResponse | None:
                The response to the hit event. If the effect does not
                respond to hits, return None.

        """
        return None

    def on_damage_taken(self, event: DamageTakenEvent) -> EventResponse | None:
        """
        Handle damage taken event for the effect.

        Args:
            event (DamageTakenEvent):
                The damage taken event.

        Returns:
            EventResponse | None:
                The response to the damage taken event. If the effect does not
                respond to damage, return None.

        """
        return None

    def model_post_init(self, _) -> None:
        if not isinstance(self.effect, Effect):
            raise ValueError("Effect must be an Effect instance.")
        if self.duration is not None and self.duration < 0:
            raise ValueError("Duration must be a non-negative integer or None.")
        if not all(isinstance(var, VarInfo) for var in self.variables):
            raise ValueError("All items in variables must be VarInfo instances.")
