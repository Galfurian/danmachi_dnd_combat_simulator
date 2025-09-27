"""
Module defining the NaturalAttack class for natural or innate attacks.
"""

from typing import Literal

from .base_attack import BaseAttack


class NaturalAttack(BaseAttack):
    """A natural or innate attack that is part of a creature's biology.

    Examples include bites, claws, tail slaps, or other attacks that do not
    require weapons and are intrinsic to the creature's anatomy.
    """

    action_type: Literal["NaturalAttack"] = "NaturalAttack"
