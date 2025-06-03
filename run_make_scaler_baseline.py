#!/usr/bin/env python3
"""
Script to run make_scaler on the MESSAGEix baseline MPS file and generate a GAMS scaler file.

This script locates the 'basline.mps' file in the 'message_ix/model' directory,
runs the make_scaler function, and writes the corresponding '.gms' scaler file
to 'message_ix/model/scaler'. It also prints the resulting DataFrame of scaling factors.
"""

import os
import sys

# Ensure the project root is on the Python path for local imports
_here = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, _here)


from message_ix.tools.make_scaler import make_scaler


def main():
    mps_path = os.path.join(_here, "message_ix", "model", "basline.mps")
    if os.path.exists(mps_path):
        print(f"Running make_scaler on {mps_path}...")
        scaler_df = make_scaler(
            path=mps_path,
            scen_model="clone_geidco_test_SSP2_v5.3",
            scen_scenario="baseline_geidco_test1",
            bounds=4,
            steps=1,
            display_range=True,
        )
        print("\nScaler factors DataFrame:")
        print(scaler_df)
    else:
        print(f"mps_path not found at {mps_path}")


if __name__ == "__main__":
    main()
