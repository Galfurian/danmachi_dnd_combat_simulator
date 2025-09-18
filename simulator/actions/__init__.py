"""
Actions system module for the DanMachi D&D Combat Simulator.

This module contains all combat actions including attacks, spells, and abilities.
It provides the base action framework and specific implementations for different
types of combat actions that characters can perform.
"""

from .base_action import BaseAction

__all__ = ["BaseAction"]
