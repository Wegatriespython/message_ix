import os  # For checking if scaler file exists

import ixmp

from message_ix.core import Scenario

# 1. Initialize Platform and get/create Scenario
# Replace with your platform connection details if needed

mp = ixmp.Platform(name="ixmp_dev", jvmargs=["-Xmx14G"])


# Original scenario (assuming it exists and has data)
model_name = "clone_geidco_test_SSP2_v5.3"
base_scenario_name = "baseline_geidco_test_cooling"

# Cloned scenario for scaled solve
scaled_scenario_name = base_scenario_name + "_scaled"

try:
    scen_to_clone = Scenario(
        mp,
        model=model_name,
        scenario=base_scenario_name,
    )
    print(f"Found base scenario: {scen_to_clone.model}/{scen_to_clone.scenario}")

    scen_scaled = scen_to_clone.clone(
        model=model_name,  # Usually keep the same model name
        scenario=scaled_scenario_name,
        annotation="Attempting scaled solve",
        keep_solution=False,
    )
    scen_scaled.check_out()
    print(f"Cloned to: {scen_scaled.model}/{scen_scaled.scenario} for scaled solve.")

except Exception as e:
    print(f"Error accessing or cloning scenario: {e}")
    print(
        "Please ensure the base scenario exists and you have a working ixmp connection."
    )
    mp.close_db()
    exit()


scaler_file_full_path = (
    r"C:\Users\raghunathan\Documents\Work\message_ix\model\scaler\MsgScaler_clone_geidco_test_SSP2_v5.3_baseline_geidco_test_cooling.gms"
)

if not os.path.exists(scaler_file_full_path):
    print(f"WARNING: Scaler file {scaler_file_full_path} not found.")
    print(
        "Make sure you have generated the scaler file for the target scenario (model/scenario names must match the cloned one)."
    )



# 3. Solve the cloned scenario using the scaler
print(
    f"Attempting to solve {scen_scaled.model}/{scen_scaled.scenario} with scaler: {scaler_file_full_path}"
)

# Define GAMS options
# The make_scaler tool already includes `MESSAGE_LP.scaleopt = 1` in the GMS file.
# So, only `scaler` option is strictly needed here.
gams_solve_options = {"scaler": "MsgScaler_clone_geidco_test_SSP2_v5.3_baseline_geidco_test_cooling"}

try:
    # Solve the scenario
    scen_scaled.solve(model="MESSAGE", gams_options=gams_solve_options)

    if scen_scaled.has_solution():
        print(
            f"Scenario {scen_scaled.model}/{scen_scaled.scenario} solved successfully with scaling."
        )
    else:
        print(
            f"Scenario {scen_scaled.model}/{scen_scaled.scenario} solve attempt finished, but no solution was found."
        )

except Exception as e:
    print(f"Error during solve of {scen_scaled.model}/{scen_scaled.scenario}: {e}")

finally:
    # Commit changes and close the database connection
    scen_scaled.commit("Finished scaled solve attempt.")
    mp.close_db()
    print("Platform connection closed.")
