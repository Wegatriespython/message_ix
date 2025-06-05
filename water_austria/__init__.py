"""
MESSAGEix Water-Austria Integration Module

A reduced-form water-energy nexus model that integrates functional subsets
of the MESSAGEix water module with the Austria energy system tutorial.
"""

__version__ = "0.1.0"
__author__ = "MESSAGEix Development Team"

from .build import build_water_austria_scenario

__all__ = ["build_water_austria_scenario"]
