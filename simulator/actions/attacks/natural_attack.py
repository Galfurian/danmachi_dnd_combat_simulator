"""
Natural attack module for the simulator.

Defines natural or innate attacks that are part of a creature's biology,
such as bites, claws, or tail slaps.
"""

from typing import Literal

from .base_attack import BaseAttack


class NaturalAttack(BaseAttack):
    """A natural or innate attack that is part of a creature's biology.

    Examples include bites, claws, tail slaps, or other attacks that do not
    require weapons and are intrinsic to the creature's anatomy.
    """

    action_type: Literal["NaturalAttack"] = "NaturalAttack"
