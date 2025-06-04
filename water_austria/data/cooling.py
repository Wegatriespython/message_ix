"""
Power plant cooling technology integration for Austria.

This module uses the direct cooling integration approach to add
cooling technologies from the water module to Austria scenarios.
"""

import logging

from message_ix import Scenario

# Import the direct cooling integration
from .cooling_direct import add_cooling_direct

log = logging.getLogger(__name__)


def add_cooling_technologies(scenario: Scenario, **options) -> None:
    """
    Add power plant cooling technologies to Austria scenario.
    
    This uses the direct integration approach to add cooling
    technologies without requiring the full water module Context.
    
    Parameters
    ----------
    scenario : Scenario
        Austria scenario to enhance with cooling technologies
    **options
        Additional options for cooling technology configuration
    """
    
    log.info("Adding cooling technologies to Austria scenario")
    
    # Use the direct cooling integration
    add_cooling_direct(scenario, **options)