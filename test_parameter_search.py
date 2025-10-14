#!/usr/bin/env python3
"""Test script for binary search parameter calibration

This script demonstrates the new Python API for binary search that uses
the growth_activity_up_search parameter instead of CLI arguments.
"""

import pandas as pd
from ixmp import Platform

from message_ix.testing import make_westeros

# Create a local test platform
mp = Platform(name="local")

# Create a Westeros scenario with 10 periods (simple MESSAGE test model)
print("Creating Westeros scenario with 10 periods...")
model_horizon = [700, 710, 720, 730, 740, 750, 760, 770, 780, 790]
scen = make_westeros(mp, solve=False, quiet=False, model_horizon=model_horizon)

# Modify demand to grow at 5% per year
print("\nModifying demand to grow at 5% per year...")
with scen.transact("Set growing demand"):
    demand_df = scen.par("demand")
    base_year = 700

    for idx in demand_df.index:
        if demand_df.loc[idx, "year"] > base_year:
            elapsed = demand_df.loc[idx, "year"] - base_year
            demand_df.loc[idx, "value"] = demand_df.loc[idx, "value"] * (
                1.05 ** (elapsed / 10)
            )

    scen.remove_par("demand", demand_df)
    scen.add_par("demand", demand_df)

# Add some growth_activity_up constraints to test the binary search
print("\nAdding growth_activity_up constraints for all periods...")
with scen.transact("Add growth_activity_up constraint"):
    # Set wind growth to 0 - forces coal to meet demand
    for year in model_horizon:
        scen.add_par(
            "growth_activity_up", ["Westeros", "wind_ppl", year, "year"], 0.0, "GWa"
        )

    # Add tight growth constraints on coal for Westeros (to be calibrated)
    for year in model_horizon:
        scen.add_par(
            "growth_activity_up", ["Westeros", "coal_ppl", year, "year"], 0.001, "GWa"
        )

print(f"\nScenario: {scen.model}/{scen.scenario}")
print("Growth activity up values:")
print(scen.par("growth_activity_up"))

# Add binary search configuration using the new parameter approach
print("\nConfiguring binary search via growth_activity_up_search parameter...")
print(
    "Searching for minimum feasible growth for Westeros coal across all 10 periods..."
)
with scen.transact("Add binary search configuration"):
    # First, add the search_config set elements
    scen.add_set("search_config", ["lo", "hi", "tol"])

    # Define search bounds for Westeros coal across all 10 periods
    # Each period gets lo, hi, tol entries
    search_data = []
    for year in model_horizon:
        search_data.extend(
            [
                {
                    "node_loc": "Westeros",
                    "technology": "coal_ppl",
                    "year_act": year,
                    "time": "year",
                    "search_config": "lo",
                    "value": 0.001,
                    "unit": "-",
                },
                {
                    "node_loc": "Westeros",
                    "technology": "coal_ppl",
                    "year_act": year,
                    "time": "year",
                    "search_config": "hi",
                    "value": 0.15,
                    "unit": "-",
                },
                {
                    "node_loc": "Westeros",
                    "technology": "coal_ppl",
                    "year_act": year,
                    "time": "year",
                    "search_config": "tol",
                    "value": 0.001,
                    "unit": "-",
                },
            ]
        )

    search_df = pd.DataFrame(search_data)
    scen.add_par("growth_activity_up_search", search_df)

print(f"\nConfigured binary search for {len(model_horizon)} periods in Westeros")

print("\nBinary search configuration added:")
print(scen.par("growth_activity_up_search"))

print("\n" + "=" * 80)
print("Solving with binary search (auto-detected from parameter)...")
print("This will search for the minimum feasible growth_activity_up value")
print("-" * 80)

# Solve - binary search runs automatically if parameter exists
# No gams_args needed!
scen.solve()

print("\n" + "=" * 80)
print("Solve complete!")
print("=" * 80)

# Check the results
obj_val = scen.var("OBJ")
if isinstance(obj_val, pd.DataFrame):
    print(f"\nObjective value: {obj_val['lvl'].values[0]:.2f}")
elif isinstance(obj_val, dict):
    print(f"\nObjective value: {obj_val['lvl']:.2f}")
else:
    print(f"\nObjective value: {obj_val:.2f}")

# The growth_activity_up parameter should now contain the calibrated values
print("\nCalibrated growth_activity_up values:")
print(scen.par("growth_activity_up"))

print("\nCheck the GAMS log output above for binary search details:")
print("  - Number of iterations")
print("  - Best feasible multiplier found")
print("  - Modified parameter values")
