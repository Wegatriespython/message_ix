"""
Optimized implementations for make_scaler helper functions and an optimized make_scaler.

These functions aim to improve performance while preserving GAMS syntax generation logic.
"""

import os
import re

import numpy as np
import pandas as pd

from . import replace_spaces_in_quotes, return_spaces_in_quotes, get_scaler_args
from message_ix.tools.lp_diag import LPdiag


def optimized_make_logdf(data):
    """Faster log10 of absolute non-zero DataFrame 'val' column."""
    arr = data["val"].to_numpy()
    mask = arr != 0
    log_arr = np.zeros_like(arr, dtype=float)
    log_arr[mask] = np.log10(np.abs(arr[mask]))
    return pd.DataFrame({"val": log_arr}, index=data.index)


def optimized_filter_df(data, bounds):
    """Faster extraction of outlier coefficients based on exponent bounds."""
    if isinstance(bounds, int):
        lo_bound = -bounds
        up_bound = bounds
    else:
        lo_bound, up_bound = bounds
    arr = data["val"].to_numpy()
    mask = (arr <= lo_bound) | (arr >= up_bound)
    return data.loc[mask]


def get_lvl_ix(data, lvl):
    """Get level index (optimized alias)."""
    return data.index.get_level_values(lvl)


def show_range(data, pretext):
    """Display coefficient exponent range (using optimized logdf)."""
    log_absdf = optimized_make_logdf(data)
    print(
        f"{pretext}:",
        "[",
        np.int32(np.min(log_absdf)),
        "|",
        np.int32(np.max(log_absdf)),
        "]",
    )


def make_scaler(path, scen_model, scen_scenario, bounds=4, steps=1, display_range=True):
    """
    Optimized version of make_scaler: process to generate prescale_args for GAMS,
    with faster DataFrame operations.
    """
    quoted_pattern = re.compile(r"'([^']*)'")

    with open(path, "r+") as f:
        old = f.readlines()
        f.seek(0)
        f.truncate()
        for line in old:
            f.write(quoted_pattern.sub(replace_spaces_in_quotes, line))

    lp = LPdiag()
    lp.read_mps(path)
    matrix = lp.read_matrix()

    if display_range:
        show_range(matrix, "\nUnscaled range     ")

    scalers = {"row": [], "col": []}
    counter = 0
    while counter < steps:
        for s in scalers.keys():
            log_absmatrix = optimized_make_logdf(matrix)
            log_absmatrix_solv = optimized_filter_df(log_absmatrix, bounds)

            objective_ix = "_obj" if s == "row" else "constobj"
            levels_solv = [
                lvl for lvl in get_lvl_ix(log_absmatrix_solv, s) if lvl != objective_ix
            ]

            if levels_solv:
                grp = log_absmatrix["val"].groupby(level=s)
                bounds_df = grp.agg(["min", "max"]).astype(int)
                mids = ((bounds_df["min"] + bounds_df["max"]) / 2).astype(int)
                exps = mids if s == "row" else -mids
                SFs = (10.0**exps).to_dict()
                SFs = {k: v for k, v in SFs.items() if k in levels_solv}
            else:
                SFs = {}

            return_index = list(set(get_lvl_ix(log_absmatrix, s)))
            multiplier = (
                1 if counter == 0 else scalers[s].reindex(return_index).fillna(1)
            )

            step_scaler = pd.DataFrame(data=SFs, index=["val"]).transpose()
            step_scaler.index.name = s
            step_scaler = step_scaler.reindex(return_index).fillna(1)

            scalers[s] = step_scaler.mul(multiplier)
            matrix = matrix.div(step_scaler) if s == "row" else matrix.mul(step_scaler)

        if display_range:
            show_range(matrix, f"Scaled range step {counter + 1}")
        counter += 1

    scaler_dict = {}
    for key, df_scaler in scalers.items():
        df_scaler = df_scaler.loc[df_scaler["val"] != 1]
        for k, v in df_scaler["val"].to_dict().items():
            if k == "_obj":
                k_ = "_obj.scale"
            elif k == "constobj":
                k_ = "constobj.scale"
            else:
                # Check if this is a multi-dimensional constraint (has parentheses)
                if "(" in k and ")" in k:
                    # Extract constraint name and parameters
                    constraint_name = k[:k.index("(")]
                    params = k[k.index("(")+1:k.index(")")].split(",")
                    # Quote each parameter only if not already quoted
                    quoted_params = []
                    for p in params:
                        p = p.strip()
                        if p.startswith("'") and p.endswith("'"):
                            # Already quoted, use as-is
                            quoted_params.append(p)
                        else:
                            # Not quoted, add quotes
                            quoted_params.append(f"'{p}'")
                    # Reconstruct with quotes
                    k_ = f"{constraint_name}.scale({','.join(quoted_params)})"
                else:
                    # Simple constraint name without dimensions
                    k_ = k + ".scale"
            # Note: We do NOT replace ___ with spaces anymore to avoid breaking quoted strings
            scaler_dict[k_] = v

    scaler_dict["MESSAGE_LP.scaleopt"] = 1
    scaler_df = pd.DataFrame(scaler_dict, index=["val"]).transpose()
    scaler_df.index = scaler_df.index.rename("key", inplace=False)

    scaler_list = [f"{k}={v};" for k, v in scaler_dict.items()]
    scaler_args_txt = "\n".join(scaler_list)

    # Find the message_ix root directory by looking for the model/scaler directory
    current_file = os.path.abspath(__file__)
    # Go up from tools/make_scaler/scaler_optim.py to message_ix root
    message_ix_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    
    scaler_gms_name = "_".join(s.replace(" ", "_") for s in [scen_model, scen_scenario])
    
    scaler_dir = os.path.join(message_ix_root, "model", "scaler")
    os.makedirs(scaler_dir, exist_ok=True)  # Create directory if it doesn't exist
    
    scaler_gms_dir = os.path.join(scaler_dir, f"MsgScaler_{scaler_gms_name}.gms")
    
    with open(scaler_gms_dir, "w") as txtfile:
        txtfile.write(scaler_args_txt)

    return scaler_df
