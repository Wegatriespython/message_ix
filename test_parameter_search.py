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

# Create a Westeros scenario (simple MESSAGE test model)
print("Creating Westeros scenario...")
scen = make_westeros(mp, solve=False, quiet=False)

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
print("\nAdding tight growth_activity_up constraint for coal_ppl...")
with scen.transact("Add growth_activity_up constraint"):
    # Set wind growth to 0 - no growth allowed, forces coal to meet demand
    scen.add_par(
        "growth_activity_up", ["Westeros", "wind_ppl", 710, "year"], 0.0, "GWa"
    )
    scen.add_par(
        "growth_activity_up", ["Westeros", "wind_ppl", 720, "year"], 0.0, "GWa"
    )

    # Add a VERY tight growth constraint on coal power plants
    # This should make the model infeasible, forcing binary search to find relaxation
    scen.add_par(
        "growth_activity_up",
        ["Westeros", "coal_ppl", 710, "year"],
        0.001,  # 0.1% growth limit - too tight, should be infeasible
        "GWa",
    )
    scen.add_par(
        "growth_activity_up",
        ["Westeros", "coal_ppl", 720, "year"],
        0.001,  # 0.1% growth limit - too tight, should be infeasible
        "GWa",
    )

print(f"\nScenario: {scen.model}/{scen.scenario}")
print("Growth activity up values:")
print(scen.par("growth_activity_up"))

# Add binary search configuration using the new parameter approach
print("\nConfiguring binary search via growth_activity_up_search parameter...")
with scen.transact("Add binary search configuration"):
    # First, add the search_config set elements
    scen.add_set("search_config", ["lo", "hi", "tol"])

    # Define search bounds for specific (node, tec, year, time) tuples
    search_df = pd.DataFrame(
        {
            "node_loc": [
                "Westeros",
                "Westeros",
                "Westeros",
                "Westeros",
                "Westeros",
                "Westeros",
            ],
            "technology": [
                "coal_ppl",
                "coal_ppl",
                "coal_ppl",
                "coal_ppl",
                "coal_ppl",
                "coal_ppl",
            ],
            "year_act": [710, 710, 710, 720, 720, 720],
            "time": ["year", "year", "year", "year", "year", "year"],
            "search_config": ["lo", "hi", "tol", "lo", "hi", "tol"],
            "value": [
                0.01,
                1,
                0.0001,
                0.01,
                1,
                0.0001,
            ],  # Search range: 0.1% to 1% with 0.01% tolerance
            "unit": ["-", "-", "-", "-", "-", "-"],
        }
    )
    scen.add_par("growth_activity_up_search", search_df)

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
if isinstance(obj_val, float):
    print(f"\nObjective value: {obj_val:.2f}")
else:
    print(f"\nObjective value: {obj_val['lvl'].values[0]:.2f}")

# The growth_activity_up parameter should now contain the calibrated values
print("\nCalibrated growth_activity_up values:")
print(scen.par("growth_activity_up"))

print("\nCheck the GAMS log output above for binary search details:")
print("  - Number of iterations")
print("  - Best feasible multiplier found")
print("  - Modified parameter values")
