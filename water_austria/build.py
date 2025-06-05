"""
Core integration functions for water-Austria model building.

This module provides the main entry points for building water-enhanced
Austria scenarios by integrating functional subsets from the water module.
"""

import logging

from message_ix import Scenario

log = logging.getLogger(__name__)


def build_water_austria_scenario(
    base_scenario: Scenario,
    **options,
) -> Scenario:
    """
    Build a water-enhanced Austria scenario from a base Austria scenario.

    This function takes an existing Austria energy scenario and adds
    cooling technologies to power plants.

    Parameters
    ----------
    base_scenario : Scenario
        Base Austria energy scenario to enhance with water features
    **options
        Additional options passed to integration functions

    Returns
    -------
    Scenario
        New scenario with cooling technologies added

    Examples
    --------
    >>> from water_austria import build_water_austria_scenario
    >>> water_scenario = build_water_austria_scenario(austria_base)
    """

    log.info("Building water-Austria scenario with cooling technologies")

    # Clone the base scenario
    water_scenario = base_scenario.clone(
        model=f"{base_scenario.model} + Water",
        scenario=f"{base_scenario.scenario}_water_cooling",
        annotation="Water-enhanced Austria model with cooling technologies",
    )

    # Check out for editing
    water_scenario.check_out()

    from .data.cooling import add_cooling
    add_cooling(water_scenario, **options)

    return water_scenario


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
