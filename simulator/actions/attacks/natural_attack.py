from typing import Any

from .base_attack import BaseAttack
from combat.damage import DamageComponent
from core.constants import ActionType
from effects.base_effect import Effect


class NaturalAttack(BaseAttack):
    """A natural or innate attack that is part of a creature's biology.

    Examples include bites, claws, tail slaps, or other attacks that do not
    require weapons and are intrinsic to the creature's anatomy.
    """

