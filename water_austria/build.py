"""
Core integration functions for water-Austria model building.

This module provides the main entry points for building water-enhanced
Austria scenarios by integrating functional subsets from the water module.
"""

import logging
from typing import Optional

import pandas as pd
from message_ix import Scenario

log = logging.getLogger(__name__)


def build_water_austria_scenario(
    base_scenario: Scenario,
    phase: str = "cooling",
    fictional_enhancements: bool = True,
    **options
) -> Scenario:
    """
    Build a water-enhanced Austria scenario from a base Austria scenario.
    
    This function takes an existing Austria energy scenario and adds
    water technologies and constraints by extracting functional subsets
    from the MESSAGEix water module.
    
    Parameters
    ----------
    base_scenario : Scenario
        Base Austria energy scenario to enhance with water features
    phase : str, default "cooling"
        Integration phase: "cooling", "supply", or "nexus"
    fictional_enhancements : bool, default True
        Whether to add fictional elements to better demonstrate water dynamics
    **options
        Additional options passed to integration functions
        
    Returns
    -------
    Scenario
        New scenario with water technologies and constraints added
        
    Examples
    --------
    >>> from water_austria import build_water_austria_scenario
    >>> water_scenario = build_water_austria_scenario(austria_base, phase="cooling")
    """
    
    log.info(f"Building water-Austria scenario, phase: {phase}")
    
    # Clone the base scenario
    water_scenario = base_scenario.clone(
        model=f"{base_scenario.model} + Water",
        scenario=f"{base_scenario.scenario}_water_{phase}",
        annotation=f"Water-enhanced Austria model, phase: {phase}"
    )
    
    # Check out for editing
    water_scenario.check_out()
    
    if phase == "cooling":
        from .data.cooling import add_cooling_technologies
        add_cooling_technologies(water_scenario, **options)
        
    elif phase == "supply":
        from .data.cooling import add_cooling_technologies
        from .data.supply import add_water_supply
        add_cooling_technologies(water_scenario, **options)
        add_water_supply(water_scenario, **options)
        
    elif phase == "nexus":
        from .data.cooling import add_cooling_technologies
        from .data.supply import add_water_supply
        from .data.demands import add_water_demands
        add_cooling_technologies(water_scenario, **options)
        add_water_supply(water_scenario, **options)
        add_water_demands(water_scenario, **options)
        
    else:
        raise ValueError(f"Unknown phase: {phase}. Must be 'cooling', 'supply', or 'nexus'")
    
    if fictional_enhancements:
        add_fictional_enhancements(water_scenario, phase)
    
    return water_scenario


def add_fictional_enhancements(scenario: Scenario, phase: str) -> None:
    """
    Add fictional elements to Austria to better demonstrate water dynamics.
    
    Parameters
    ----------
    scenario : Scenario
        Scenario to enhance with fictional elements
    phase : str
        Current integration phase
    """
    
    log.info("Adding fictional enhancements to Austria")
    
    if phase in ["supply", "nexus"]:
        # Add fictional coastal region for desalination
        scenario.add_spatial_sets({"region": ["Austria_Coastal"]})
        
        # Add fictional river basins
        fictional_basins = ["Danube_Basin", "Rhine_Basin", "Coastal_Basin"]
        scenario.add_set("node", [f"B{i}" for i, _ in enumerate(fictional_basins, 1)])
        
    # Additional fictional enhancements can be added here based on phase


def get_austria_water_context(scenario: Scenario) -> dict:
    """
    Create a context dictionary for Austria water integration.
    
    This function extracts relevant information from the Austria scenario
    and creates a context similar to the water module's Context class.
    
    Parameters
    ----------
    scenario : Scenario
        Austria scenario to extract context from
        
    Returns
    -------
    dict
        Context dictionary for water integration
    """
    
    context = {
        "scenario": scenario,
        "regions": "Austria",  # Single region
        "type_reg": "country",
        "time": list(scenario.set("year")),
        "nexus_set": "cooling",  # Start with cooling only
    }
    
    return context