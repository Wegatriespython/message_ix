"""
Direct integration of water module functions with Austria base scenario.

This script follows the approach from test_full_water_build to apply
water module functions directly to the Austria base scenario.
"""

import logging
import traceback
from typing import List

import ixmp as ix
import pandas as pd
from message_ix_models import ScenarioInfo
from message_ix_models.model.water.data.demands import (
    add_irrigation_demand,
    add_sectoral_demands,
    add_water_availability,
)
from message_ix_models.model.water.data.infrastructure import (
    add_desalination,
    add_infrastructure_techs,
)
from message_ix_models.model.water.data.irrigation import add_irr_structure
from message_ix_models.model.water.data.water_for_ppl import cool_tech, non_cooling_tec
from message_ix_models.model.water.data.water_supply import add_e_flow, add_water_supply
from message_ix_models.model.water.utils import read_config
from message_ix_models.util import add_par_data
from scripts.build_austria_base import build_austria_base_scenario

from message_ix import Scenario

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Water constants from test_water_build_comprehensive
WATER_COMMODITIES = [
    "electr",
    "gas",
    "coal",
    "uranium",
    "biomass",
    "oil",
    "lightoil",
    "fueloil",
    "surfacewater_basin",
    "groundwater_basin",
    "freshwater_basin",
    "freshwater",
    "saline_ppl",
    "cl_fresh",
    "ot_fresh",
    "air",
    "ot_saline",
    "cl_saline",
    "urban_mw",
    "rural_mw",
    "industry_mw",
    "freshwater_supply",
    "saline_supply",
    "urban_collected_wst",
    "rural_collected_wst",
    "industry_collected_wst",
    "urban_uncollected_wst",
    "rural_uncollected_wst",
    "industry_uncollected_wst",
    "urban_treated",
    "rural_treated",
    "industry_treated",
    "urban_disconnected",
    "rural_disconnected",
    "industry_disconnected",
]

WATER_LEVELS = [
    "secondary",
    "primary",
    "final",
    "water_treat",
    "water_avail_basin",
    "water_supply_basin",
    "water_supply",
    "saline_supply",
    "share",
    "water_demand",
    "municipal_mw",
    "industry_mw",
    "irr_cereal",
    "irr_oilcrops",
    "irr_sugarcrops",
    "waste_management",
    "urban_discharge",
    "rural_discharge",
    "industry_discharge",
]

WATER_EMISSIONS = ["fresh_return", "CO2", "water_consumption"]


def _add_par_data(scenario, data):
    """Robust version of add_par_data that filters out None/NaN years."""
    for par_name, df in data.items():
        if isinstance(df, pd.DataFrame):
            # Ensure node columns are strings
            node_cols = [c for c in df.columns if "node" in c]
            for col in node_cols:
                df[col] = df[col].astype(str)

            # Filter out invalid years
            for year_col in ["year_vtg", "year_act", "year"]:
                if year_col in df.columns:
                    original_rows = len(df)
                    df = df[df[year_col].notna()]
                    if len(df) < original_rows:
                        logger.info(
                            f"Filtered {original_rows - len(df)} rows with invalid years from '{par_name}'"
                        )
                    data[par_name] = df

    add_par_data(scenario, data, dry_run=False)


def _apply_and_commit(scenario, context, data_func, comment, **kwargs):
    """Helper to apply a data function using a transaction."""
    func_name = data_func.__name__
    logger.info(f"Calling {func_name}...")

    try:
        data = data_func(context, scenario=scenario, **kwargs)
        if not data:
            logger.warning(f"{func_name} returned no data, skipping.")
            return

        with scenario.transact(comment):
            _add_par_data(scenario, data)

        logger.info(f"{func_name} applied successfully.")

    except Exception as e:
        logger.error(f"{func_name} failed: {e}")
        traceback.print_exc()


def _add_items_to_set(scenario: Scenario, set_name: str, items: List[str]):
    """Add a list of items to a scenario set, handling existing items gracefully."""
    existing_items = set(scenario.set(set_name))
    items_to_add = [item for item in items if item not in existing_items]
    if items_to_add:
        scenario.add_set(set_name, items_to_add)


def create_austria_water_context():
    """Create water context for Austria following test pattern."""
    # Use local platform
    mp = ix.Platform(name="local")

    # Create context similar to test_water_build_comprehensive
    class MockContext:
        def __init__(self):
            self.SDG = "baseline"
            self.time = ["year"]
            self.type_reg = "global"
            self.regions = "R12"  # Use R12 region which includes Austria (WEU)
            self.RCP = "7p0"
            self.REL = "low"
            self.nexus_set = "nexus"
            self.ssp = "baseline"
            self.map_ISO_c = {"AT": "Austria"}
            self._mp = mp

        def get_platform(self):
            return self._mp

        def set_scenario(self, scenario):
            self.scenario = scenario

        def __getitem__(self, key):
            if isinstance(key, str):
                return getattr(self, key.replace(" ", "_"), None)
            return None

        def __setitem__(self, key, value):
            if isinstance(key, str):
                setattr(self, key.replace(" ", "_"), value)

        def __contains__(self, key):
            if isinstance(key, str):
                return hasattr(self, key.replace(" ", "_"))
            return False

    ctx = MockContext()

    # Read water config
    read_config(ctx)

    return ctx, mp


def setup_austria_scenario_for_water(scenario):
    """Add required sets and parameters for water integration."""
    logger.info("Setting up Austria scenario for water integration...")

    with scenario.transact("Added water sets and parameters"):
        # Add water commodities
        _add_items_to_set(scenario, "commodity", WATER_COMMODITIES)

        # Add water levels
        _add_items_to_set(scenario, "level", WATER_LEVELS)

        # Add water emissions
        _add_items_to_set(scenario, "emission", WATER_EMISSIONS)

        # Add required shares for water functions
        water_shares = [
            "share_basin",
            "share_wat_recycle",
            "share_low_lim_GWat",
            "share_cooling_air",
            "share_cooling_ot_saline",
        ]
        _add_items_to_set(scenario, "shares", water_shares)

        # Add modes for water
        _add_items_to_set(scenario, "mode", ["M1", "Mf"])

        # Add time
        _add_items_to_set(scenario, "time", ["year"])

        # Add basin nodes from R12 region
        logger.info("Adding basin nodes from R12...")
        basin_file = "/home/raghunathan/message-ix-models/message_ix_models/data/water/delineation/basins_by_region_simpl_R12.csv"
        basin_df = pd.read_csv(basin_file)

        # Add basin nodes
        basin_nodes = [f"B{bcu}" for bcu in basin_df["BCU_name"]]
        _add_items_to_set(scenario, "node", basin_nodes)

        # Add basin modes
        basin_modes = [f"M{bcu}" for bcu in basin_df["BCU_name"]]
        _add_items_to_set(scenario, "mode", basin_modes)

        # Add R12 regional nodes
        r12_regions = [
            "R12_AFR",
            "R12_CPA",
            "R12_EEU",
            "R12_FSU",
            "R12_LAM",
            "R12_MEA",
            "R12_NAM",
            "R12_PAO",
            "R12_PAS",
            "R12_SAS",
            "R12_WEU",
            "R12_GLB",
        ]
        _add_items_to_set(scenario, "node", r12_regions)

        logger.info(
            f"Added {len(basin_nodes)} basin nodes and {len(r12_regions)} regional nodes"
        )


def apply_water_functions_to_austria():
    """Main function to apply water functions to Austria base scenario."""
    logger.info("=== Starting Water-Austria Integration ===")

    # Create water context
    context, mp = create_austria_water_context()

    try:
        # Build Austria base scenario
        logger.info("Building Austria base scenario...")
        base_scenario = build_austria_base_scenario(mp)

        # Clone for water integration
        water_scenario = base_scenario.clone(
            model="Austrian energy model + Water",
            scenario="water_integration",
            annotation="Austria with water module integration",
        )

        # Set up scenario for water
        setup_austria_scenario_for_water(water_scenario)

        # Set scenario in context
        context.set_scenario(water_scenario)

        # Add required ScenarioInfo
        info = ScenarioInfo(water_scenario)
        info.y0 = 2020
        context["water build info"] = info

        # Apply water functions in sequence from test_full_water_build
        logger.info("=== Applying Water Functions ===")

        data_functions = [
            (add_water_supply, "Applied water supply"),
            (add_e_flow, "Applied environmental flow"),
            (cool_tech, "Applied cooling tech data"),
            (add_infrastructure_techs, "Applied infrastructure data"),
            (add_desalination, "Applied desalination data"),
            (non_cooling_tec, "Applied non-cooling nexus data"),
            (add_sectoral_demands, "Applied sectoral water demands"),
            (add_water_availability, "Applied water availability constraints"),
            (add_irrigation_demand, "Applied irrigation demands"),
            (add_irr_structure, "Applied irrigation structure"),
        ]

        for func, comment in data_functions:
            _apply_and_commit(water_scenario, context, func, comment)

        logger.info("=== Water Integration Complete ===")

        # Try to solve
        logger.info("Attempting to solve water-integrated scenario...")
        water_scenario.solve()

        obj_value = water_scenario.var("OBJ")["lvl"]
        logger.info(f"✅ Solved successfully! Objective value: {obj_value}")

        return water_scenario

    except Exception as e:
        logger.error(f"Integration failed: {e}")
        traceback.print_exc()
        return None

    finally:
        mp.close_db()


if __name__ == "__main__":
    scenario = apply_water_functions_to_austria()
    if scenario:
        print("✅ Water-Austria integration completed successfully!")
    else:
        print("❌ Water-Austria integration failed!")
