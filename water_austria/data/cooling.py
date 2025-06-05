"""
Direct integration of water cooling technologies for Austria.

This module extracts the essential parts from the water module
to add cooling technologies to Austria without the full Context framework.
"""

import logging
from typing import List

from message_ix_models import ScenarioInfo

from message_ix import Scenario, make_df

log = logging.getLogger(__name__)


def add_cooling(scenario: Scenario, **options) -> None:
    """
    Add cooling technologies by extracting essential water module functionality.

    This function bypasses the Context framework and directly applies
    the cooling technology structure and data.
    """

    log.info("Adding cooling technologies via direct integration")

    # 1. Get scenario info
    info = ScenarioInfo(scenario)

    # 2. Add cooling technology sets
    _add_cooling_sets(scenario)

    # 3. Get parent technologies that need cooling
    parent_techs = _get_parent_technologies(scenario)

    # 4. Add cooling technology variants
    cooling_techs = _add_cooling_technology_variants(scenario, parent_techs)

    # 5. Add cooling technology data
    _add_cooling_data(scenario, parent_techs, cooling_techs, info)

    log.info(f"Added {len(cooling_techs)} cooling technology variants")


def _add_cooling_sets(scenario: Scenario) -> None:
    """Add required sets for cooling technologies."""

    # Add cooling-related commodities
    cooling_commodities = ["freshwater", "ot_fresh", "cl_fresh", "air", "ot_saline"]

    # Add water levels
    water_levels = ["water_supply", "cooling", "share"]

    # Add addon types
    addon_types = ["cooling"]

    # Add to scenario
    for comm in cooling_commodities:
        if comm not in scenario.set("commodity"):
            scenario.add_set("commodity", comm)

    for level in water_levels:
        if level not in scenario.set("level"):
            scenario.add_set("level", level)

    for addon in addon_types:
        if addon not in scenario.set("type_addon"):
            scenario.add_set("type_addon", addon)


def _get_parent_technologies(scenario: Scenario) -> List[str]:
    """Get technologies that can have cooling variants."""

    # Get technologies that produce electricity
    output_df = scenario.par(
        "output", filters={"commodity": "electricity", "level": ["secondary", "final"]}
    )

    # Filter for power plants
    techs = output_df["technology"].unique()
    parent_techs = [t for t in techs if t.endswith("_ppl") and t != "import"]

    return parent_techs


def _add_cooling_technology_variants(
    scenario: Scenario, parent_techs: List[str]
) -> List[str]:
    """Add cooling technology variants for each parent technology."""

    cooling_types = ["ot_fresh", "cl_fresh", "air", "ot_saline"]
    cooling_techs = []

    # First, add all cooling technologies
    for parent in parent_techs:
        for cooling in cooling_types:
            cooling_tech = f"{parent}__{cooling}"
            scenario.add_set("technology", cooling_tech)
            cooling_techs.append(cooling_tech)

            # Add to addon set
            scenario.add_set("addon", cooling_tech)

    # Add parent technology to addon type mapping (2D set)
    for parent in parent_techs:
        scenario.add_set("map_tec_addon", [parent, "cooling"])

    # Add addon technology categorization
    for cooling_tech in cooling_techs:
        scenario.add_set("cat_addon", ["cooling", cooling_tech])

    return cooling_techs


def _add_cooling_data(
    scenario: Scenario,
    parent_techs: List[str],
    cooling_techs: List[str],
    info: ScenarioInfo,
) -> None:
    """Add cooling technology parameters."""

    # Get year structure
    year_df = scenario.vintage_and_active_years()
    vtg_years = year_df["year_vtg"]
    act_years = year_df["year_act"]

    # Get nodes - for Austria this is just "Austria"
    node = list(scenario.set("node"))[0]  # Single node for Austria

    # Cooling parameters (simplified for Austria demo)
    cooling_params = {
        "ot_fresh": {
            "water_withdrawal_rate": 2.5,  # m³/MWh
            "water_consumption_rate": 0.1,  # m³/MWh
            "efficiency_penalty": 0.95,  # relative to parent
            "parasitic_electricity": 0.01,  # fraction
        },
        "cl_fresh": {
            "water_withdrawal_rate": 0.8,
            "water_consumption_rate": 0.6,
            "efficiency_penalty": 0.92,
            "parasitic_electricity": 0.02,
        },
        "air": {
            "water_withdrawal_rate": 0.0,
            "water_consumption_rate": 0.0,
            "efficiency_penalty": 0.88,
            "parasitic_electricity": 0.03,
        },
        "ot_saline": {
            "water_withdrawal_rate": 2.3,
            "water_consumption_rate": 0.05,
            "efficiency_penalty": 0.94,
            "parasitic_electricity": 0.012,
        },
    }

    # Add parameters for each cooling technology
    for cooling_tech in cooling_techs:
        parent, cooling_type = cooling_tech.split("__")
        params = cooling_params[cooling_type]

        # Technical lifetime (30 years for all cooling)
        lifetime_df = make_df(
            "technical_lifetime",
            node_loc=node,
            technology=cooling_tech,
            year_vtg=info.Y,
            value=30,
            unit="y",
        )
        scenario.add_par("technical_lifetime", lifetime_df)

        # Capacity factor (inherit from parent with adjustment)
        parent_cf = scenario.par("capacity_factor", filters={"technology": parent})
        if not parent_cf.empty:
            cf_df = parent_cf.copy()
            cf_df["technology"] = cooling_tech
            cf_df["value"] *= params["efficiency_penalty"]
            scenario.add_par("capacity_factor", cf_df)

        # Water input (if not air cooling)
        if params["water_withdrawal_rate"] > 0:
            # Convert m³/MWh to appropriate model units
            # Assuming model uses MCM/GWa: 1 GWa = 8760 MWh, 1 MCM = 1e6 m³
            water_rate = params["water_withdrawal_rate"] * 8760 / 1e6

            water_input = make_df(
                "input",
                node_loc=node,
                technology=cooling_tech,
                year_vtg=vtg_years,
                year_act=act_years,
                mode="standard",
                node_origin=node,
                commodity="freshwater",
                level="water_supply",
                time="year",
                time_origin="year",
                value=water_rate,
                unit="-",
            )
            scenario.add_par("input", water_input)

        # Cooling output (the cooling service)
        cooling_output = make_df(
            "output",
            node_loc=node,
            technology=cooling_tech,
            year_vtg=vtg_years,
            year_act=act_years,
            mode="standard",
            node_dest=node,
            commodity=cooling_type,
            level="cooling",
            time="year",
            time_dest="year",
            value=1.0,
            unit="-",
        )
        scenario.add_par("output", cooling_output)

        # Addon conversion (cooling fraction)
        addon_df = make_df(
            "addon_conversion",
            node=node,
            technology=parent,
            year_vtg=info.Y,
            year_act=info.Y,
            mode="standard",
            time="year",
            type_addon="cooling",
            value=0.3,  # Simplified cooling fraction
            unit="-",
        )
        scenario.add_par("addon_conversion", addon_df)

    # Add basic water supply technology
    if "extract_freshwater" not in scenario.set("technology"):
        scenario.add_set("technology", "extract_freshwater")

        # Water extraction output
        water_output = make_df(
            "output",
            node_loc=node,
            technology="extract_freshwater",
            year_vtg=info.Y,
            year_act=info.Y,
            mode="standard",
            node_dest=node,
            commodity="freshwater",
            level="water_supply",
            time="year",
            time_dest="year",
            value=1.0,
            unit="-",
        )
        scenario.add_par("output", water_output)

        # Technical lifetime
        water_lifetime = make_df(
            "technical_lifetime",
            node_loc=node,
            technology="extract_freshwater",
            year_vtg=info.Y,
            value=60,
            unit="y",
        )
        scenario.add_par("technical_lifetime", water_lifetime)

        # Capacity factor
        water_cf = make_df(
            "capacity_factor",
            node_loc=node,
            technology="extract_freshwater",
            year_vtg=info.Y,
            year_act=info.Y,
            time="year",
            value=0.9,
            unit="-",
        )
        scenario.add_par("capacity_factor", water_cf)

        # Variable cost (small extraction cost)
        water_cost = make_df(
            "var_cost",
            node_loc=node,
            technology="extract_freshwater",
            year_vtg=info.Y,
            year_act=info.Y,
            mode="standard",
            time="year",
            value=0.1,
            unit="USD/kWa",
        )
        scenario.add_par("var_cost", water_cost)
