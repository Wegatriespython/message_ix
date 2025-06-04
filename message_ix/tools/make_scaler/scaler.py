import os
import re
from typing import Literal, Union

import pandas as pd

from message_ix.tools.lp_diag import LPdiag

# Import parallel implementations
from .parallel import make_scaler_parallel
from .utils import (
    _process_scaling_step,
    replace_spaces_in_quotes,
    show_range,
)


def _make_scaler_standard(
    path, scen_model, scen_scenario, bounds=4, steps=1, display_range=True
):
    """
    Standard implementation of make_scaler.

    Process to generate prescale_args in GAMS to improve
    matrix coefficients.

    This function shifts matrix coefficient exponents to improve
    the scaling properties of the matrix. The function returns
    prescale arguments (prescale_args) to be passed to the GAMS model.

    Parameters:
    -----------
    path: str
        Pathways to locate the mps file.
    bounds: int or list of 2 integers
        Exponent threshold used to identify outlier coefficients.
        If a single integer is provided, the bounds are set to +/- that value.
        If a list of 2 integers is provided, they represent
        the lower and upper bounds of the threshold.
    steps: int
        Number of times the prescaler generation process is repeated.
        Larger values may lead to more refined prescale_args but
        also increase computation time.
    display_range: boolean
        Option to show the coefficient exponents range before and after scaling.
        If True, the function will display the range; otherwise, it will not.

    Returns:
    --------
    prescale_args: dict
        A dictionary of prescale arguments to be passed to the GAMS model.
    """

    # Aligning mps file content with lp_diag naming formats
    quoted_pattern = re.compile(r"'([^']*)'")

    with open(path, "r+") as f:
        old = f.readlines()  # Pull the file contents to a list
        f.seek(0)  # Jump to start, so we overwrite instead of appending
        f.truncate()  # Clear the file before writing
        for line in old:
            # Replace spaces inside single-quoted substrings
            new_line = quoted_pattern.sub(replace_spaces_in_quotes, line)
            f.write(new_line)
    lp = LPdiag()
    # Start making the scaler
    lp.read_mps(path)

    data = lp.read_matrix()

    matrix = data

    if display_range is True:
        show_range(matrix, "\nUnscaled range     ")

    scalers = {"row": [], "col": []}

    counter = 0
    while counter < steps:
        for s in scalers.keys():
            matrix = _process_scaling_step(
                matrix, scalers, s, bounds, counter, display_range
            )

        if display_range is True:
            show_range(matrix, f"Scaled range step {counter + 1}")

        counter += 1

    # generating prescaler arguments for GAMS
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
                    constraint_name = k[: k.index("(")]
                    params = k[k.index("(") + 1 : k.index(")")].split(",")
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
            # Note: We do NOT replace ___ with spaces to avoid breaking strings
            scaler_dict[k_] = v

    # add this line to active scaling option
    scaler_dict["MESSAGE_LP.scaleopt"] = 1

    scaler_df = pd.DataFrame(scaler_dict, index=["val"]).transpose()
    scaler_df.index = scaler_df.index.rename("key", inplace=False)

    scaler_list = [f"{k}={v};" for k, v in scaler_dict.items()]
    scaler_args_txt = "\n".join(scaler_list)

    # Find the message_ix root directory by looking for the model/scaler directory
    current_file = os.path.abspath(__file__)
    # Go up from tools/make_scaler/__init__.py to message_ix root
    message_ix_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

    scaler_gms_name = "_".join(s.replace(" ", "_") for s in [scen_model, scen_scenario])

    scaler_dir = os.path.join(message_ix_root, "model", "scaler")
    os.makedirs(scaler_dir, exist_ok=True)  # Create directory if it doesn't exist

    scaler_gms_dir = os.path.join(scaler_dir, f"MsgScaler_{scaler_gms_name}.gms")

    with open(scaler_gms_dir, "w") as txtfile:
        # Write some text to the file
        txtfile.write(scaler_args_txt)

    return scaler_df


def make_scaler(
    path: str,
    scen_model: str,
    scen_scenario: str,
    bounds: Union[int, list] = 4,
    steps: int = 1,
    display_range: bool = True,
    mode: Literal["standard", "parallel", "auto"] = "auto",
    n_workers: int = None,
    **kwargs,
) -> pd.DataFrame:
    """
    Process to generate prescale_args in GAMS to improve matrix coefficients.

    This function uses single dispatch to automatically choose the best implementation
    based on the mode parameter:
    - "standard": Sequential processing (good for small files)
    - "parallel": Parallel processing (good for large files)
    - "auto": Automatically choose based on file size (default)

    Parameters:
    -----------
    path: str
        Path to the .mps file.
    scen_model: str
        Model name for scaler file naming.
    scen_scenario: str
        Scenario name for scaler file naming.
    bounds: int or list of 2 integers
        Exponent threshold for outlier coefficients.
    steps: int
        Number of scaling iterations.
    display_range: bool
        Whether to display coefficient ranges.
    mode: str
        Implementation mode: "standard", "parallel", or "auto".
    n_workers: int, optional
        Number of worker processes for parallel mode.
    **kwargs: dict
        Additional arguments passed to implementation functions.

    Returns:
    --------
    scaler_df: pandas.DataFrame
        Scaling parameters for GAMS.
    """

    if mode == "standard":
        return _make_scaler_standard(
            path, scen_model, scen_scenario, bounds, steps, display_range
        )
    elif mode == "parallel":
        return make_scaler_parallel(
            path,
            scen_model,
            scen_scenario,
            bounds,
            steps,
            display_range,
            n_workers,
            **kwargs,
        )
    elif mode == "auto":
        # Automatically choose based on file size
        file_size_mb = os.path.getsize(path) / (1024 * 1024)

        if file_size_mb > 100:
            print(f"File size: {file_size_mb:.1f}MB - Using parallel implementation")
            return make_scaler_parallel(
                path,
                scen_model,
                scen_scenario,
                bounds,
                steps,
                display_range,
                n_workers,
                **kwargs,
            )
        else:
            print(f"File size: {file_size_mb:.1f}MB - Using standard implementation")
            return _make_scaler_standard(
                path, scen_model, scen_scenario, bounds, steps, display_range
            )
    else:
        raise ValueError(
            f"Invalid mode: {mode}. Choose from 'standard', 'parallel', or 'auto'."
        )
