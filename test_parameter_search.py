#!/usr/bin/env python3
"""Test script for binary search parameter calibration

This script tests the parameter_search_growth_activity_up.gms functionality
using a simple Westeros scenario.
"""

from ixmp import Platform

from message_ix.testing import make_westeros

# Create a local test platform
mp = Platform(name="local")

# Create a Westeros scenario (simple MESSAGE test model)
print("Creating Westeros scenario...")
scen = make_westeros(mp, solve=False, quiet=False)

# Add some growth_activity_up constraints to test the binary search
print("\nAdding tight growth_activity_up constraint for coal_ppl...")
with scen.transact("Add growth_activity_up constraint"):
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

# Note: Before running this, you must:
# 1. Edit message_ix/model/MESSAGE/parameter_search_growth_activity_up.gms
#    Set: $SETGLOBAL FILTER_TEC "coal_ppl"
# 2. Set search range (e.g., search_lo /0.5/, search_hi /3.0/)

print("\n" + "=" * 80)
print("IMPORTANT: Before running solve(), configure the GAMS search file:")
print("  File: message_ix/model/MESSAGE/parameter_search_growth_activity_up.gms")
print('  Set:  $SETGLOBAL FILTER_TEC "coal_ppl"')
print("  Set:  search_lo /0.5/  (test down to 50% of original)")
print("  Set:  search_hi /3.0/  (test up to 300% of original)")
print("=" * 80)

response = input("\nHave you configured the GAMS file? (y/n): ")
if response.lower() != "y":
    print("Please configure the file and run this script again.")
    exit(0)

print("\nSolving with binary search enabled...")
print("This will search for the minimum feasible growth_activity_up value")
print("-" * 80)

# Solve with binary search activated via gams_args
# Use double-dash for GAMS dollar control options
scen.solve(
    gams_args=["--SEARCH_GROWTH_ACTIVITY_UP=1"],  # Pass to GAMS as $SETGLOBAL option
)

print("\n" + "=" * 80)
print("Solve complete!")
print("=" * 80)

# Check the results
print(f"\nObjective value: {scen.var('OBJ')['lvl'].values[0]:.2f}")

# The growth_activity_up parameter should now contain the calibrated values
print("\nCalibrated growth_activity_up values:")
print(scen.par("growth_activity_up"))

print("\nCheck the GAMS log output above for binary search details:")
print("  - Number of iterations")
print("  - Best feasible multiplier found")
print("  - Modified parameter values")
