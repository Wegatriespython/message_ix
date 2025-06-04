"""
Data preparation modules for water-Austria integration.

This package contains modules for preparing water-related data
that extends the Austria energy system tutorial.
"""

from .cooling import add_cooling_technologies
from .supply import add_water_supply
from .demands import add_water_demands

__all__ = ["add_cooling_technologies", "add_water_supply", "add_water_demands"]