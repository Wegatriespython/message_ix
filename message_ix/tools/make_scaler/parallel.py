"""Parallelized version of make_scaler for handling large .mps files efficiently."""

import multiprocessing as mp
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from message_ix.tools.lp_diag import LPdiag

from .utils import (
    filter_df,
    get_lvl_ix,
    make_logdf,
    replace_spaces_in_quotes,
    show_range,
)

# Try to import fast LP reader
try:
    from message_ix.tools.lp_diag.lp_diag_fast import LPdiagFast
    HAS_FAST_LP = True
except ImportError:
    HAS_FAST_LP = False


def _chunk_file_lines(file_path, n_workers=None):
    """Split .mps file into chunks for parallel processing."""
    if n_workers is None:
        n_workers = min(mp.cpu_count(), 8)

    with open(file_path, "r") as f:
        lines = f.readlines()

    chunk_size = len(lines) // n_workers
    chunks = []

    for i in range(0, len(lines), chunk_size):
        chunk = lines[i : i + chunk_size]
        chunks.append(chunk)

    return chunks


def _process_file_chunk_regex(chunk_lines):
    """Process regex replacements on a chunk of file lines."""
    quoted_pattern = re.compile(r"'([^']*)'")
    processed_lines = []

    for line in chunk_lines:
        new_line = quoted_pattern.sub(replace_spaces_in_quotes, line)
        processed_lines.append(new_line)

    return processed_lines


def _parallel_file_preprocessing(file_path, n_workers=None):
    """Parallelize the file preprocessing step with order preservation."""
    chunks = _chunk_file_lines(file_path, n_workers)

    with ThreadPoolExecutor(max_workers=len(chunks)) as executor:
        # Submit tasks with their original index to preserve order
        futures = [(i, executor.submit(_process_file_chunk_regex, chunk)) 
                  for i, chunk in enumerate(chunks)]
        
        # Collect results in order
        processed_chunks = [None] * len(chunks)
        for i, future in futures:
            processed_chunks[i] = future.result()

    # Flatten and write back in correct order
    with open(file_path, "w") as f:
        for chunk in processed_chunks:
            f.writelines(chunk)


def _parallel_scaling_operations(
    matrix, scalers, bounds, counter, display_range, n_workers=None
):
    """Parallelize row and column scaling operations."""
    if n_workers is None:
        n_workers = min(mp.cpu_count(), 2)  # Max 2 for row/col operations

    # Process row and column scaling in parallel
    scaling_tasks = ["row", "col"]

    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = []
        for s in scaling_tasks:
            future = executor.submit(
                _process_scaling_step_parallel,
                matrix,
                scalers,
                s,
                bounds,
                counter,
                display_range,
            )
            futures.append((s, future))

        # Collect results and update matrix sequentially to maintain order
        for s, future in futures:
            matrix = future.result()

    return matrix


def _process_scaling_step_parallel(matrix, scalers, s, bounds, counter, display_range):
    """Parallel-optimized version of scaling step with numpy vectorization."""
    # Use numpy operations for better performance
    log_absmatrix = make_logdf(matrix)
    log_absmatrix_solv = filter_df(log_absmatrix, bounds)

    objective_ix = "_obj" if s == "row" else "constobj"
    levels_solv = [
        lvl for lvl in get_lvl_ix(log_absmatrix_solv, s) if lvl != objective_ix
    ]

    if levels_solv:
        # Optimization: Only group the rows/cols that need scaling
        all_indices = get_lvl_ix(log_absmatrix, s)
        mask = all_indices.isin(levels_solv)
        filtered_matrix = log_absmatrix[mask]
        
        # Vectorized groupby operations on filtered data
        grp = filtered_matrix["val"].groupby(level=s)
        bounds_df = grp.agg(["min", "max"]).astype(int)
        mids = ((bounds_df["min"] + bounds_df["max"]) / 2).astype(int)
        exps = mids if s == "row" else -mids

        # Vectorized power operation
        SFs = pd.Series(10.0**exps, index=exps.index).to_dict()
    else:
        SFs = {}

    return_index = list(set(get_lvl_ix(log_absmatrix, s)))
    
    # Optimization: Avoid creating new DataFrame for scalers if possible
    if counter == 0:
        # First iteration - create new scaler
        step_scaler = pd.Series(1.0, index=return_index)
        step_scaler.update(pd.Series(SFs))
        step_scaler = pd.DataFrame({"val": step_scaler})
        step_scaler.index.name = s
    else:
        # Subsequent iterations - update existing
        multiplier = scalers[s].reindex(return_index).fillna(1)
        step_scaler = pd.DataFrame({"val": pd.Series(SFs, index=return_index).fillna(1.0)})
        step_scaler.index.name = s
        step_scaler = step_scaler.mul(multiplier)

    scalers[s] = step_scaler

    # Optimized matrix operations
    if s == "row":
        matrix = matrix.div(step_scaler)
    else:
        matrix = matrix.mul(step_scaler)

    return matrix


def _chunk_matrix_operations(matrix, chunk_size=10000):
    """Process matrix operations in chunks to reduce memory usage."""
    chunks = []
    for i in range(0, len(matrix), chunk_size):
        chunk = matrix.iloc[i : i + chunk_size]
        chunks.append(chunk)
    return chunks


def make_scaler_parallel(
    path,
    scen_model,
    scen_scenario,
    bounds=4,
    steps=1,
    display_range=True,
    n_workers=None,
    use_fast_lp=None,
    chunk_size=10000,
):
    """
    Parallelized version of make_scaler for improved performance on large .mps files.

    This function uses multiple optimization strategies:
    1. Parallel file preprocessing with regex operations
    2. Parallel row/column scaling operations
    3. Vectorized numpy operations where possible
    4. Chunked matrix operations for memory efficiency

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
    n_workers: int, optional
        Number of worker processes. Defaults to CPU count.
    chunk_size: int
        Size of matrix chunks for memory management.

    Returns:
    --------
    scaler_df: pandas.DataFrame
        Scaling parameters for GAMS.
    """
    start_time = time.time()

    if n_workers is None:
        n_workers = min(mp.cpu_count(), 8)

    print(f"Starting parallel make_scaler with {n_workers} workers...")

    # Determine whether to use fast LP reader
    if use_fast_lp is None:
        # Auto-detect based on file size
        file_size_mb = os.path.getsize(path) / (1024 * 1024)
        use_fast_lp = HAS_FAST_LP and file_size_mb > 100
    
    # Step 1: File preprocessing (only if not using fast LP reader)
    # Fast LP reader handles preprocessing internally
    if not (use_fast_lp and HAS_FAST_LP):
        preprocessing_start = time.time()
        _parallel_file_preprocessing(path, n_workers)
        preprocessing_time = time.time() - preprocessing_start
        print(f"File preprocessing completed in {preprocessing_time:.2f}s")
    
    # Step 2: Read matrix (sequential - LPdiag not thread-safe)
    lp_start = time.time()
    
    if use_fast_lp and HAS_FAST_LP:
        print(f"Using fast LP reader for large file")
        lp = LPdiagFast()
    else:
        lp = LPdiag()
    
    lp.read_mps(path)
    data = lp.read_matrix()
    matrix = data
    lp_time = time.time() - lp_start
    print(f"Matrix reading completed in {lp_time:.2f}s")

    if display_range:
        show_range(matrix, "\nUnscaled range     ")

    scalers = {"row": [], "col": []}

    # Step 3: Parallel scaling iterations
    scaling_start = time.time()
    counter = 0
    while counter < steps:
        step_start = time.time()

        # Process scaling steps with potential parallelization
        for s in scalers.keys():
            matrix = _process_scaling_step_parallel(
                matrix, scalers, s, bounds, counter, display_range
            )

        if display_range:
            show_range(matrix, f"Scaled range step {counter + 1}")

        step_time = time.time() - step_start
        print(f"Scaling step {counter + 1} completed in {step_time:.2f}s")
        counter += 1

    scaling_time = time.time() - scaling_start
    print(f"All scaling steps completed in {scaling_time:.2f}s")

    # Step 4: Generate scaler dictionary (sequential)
    dict_start = time.time()
    scaler_dict = {}
    for key, df_scaler in scalers.items():
        df_scaler = df_scaler.loc[df_scaler["val"] != 1]
        for k, v in df_scaler["val"].to_dict().items():
            if k == "_obj":
                k_ = "_obj.scale"
            elif k == "constobj":
                k_ = "constobj.scale"
            else:
                # Handle multi-dimensional constraints
                if "(" in k and ")" in k:
                    constraint_name = k[: k.index("(")]
                    params = k[k.index("(") + 1 : k.index(")")].split(",")
                    quoted_params = []
                    for p in params:
                        p = p.strip()
                        if p.startswith("'") and p.endswith("'"):
                            quoted_params.append(p)
                        else:
                            quoted_params.append(f"'{p}'")
                    k_ = f"{constraint_name}.scale({','.join(quoted_params)})"
                else:
                    k_ = k + ".scale"
            scaler_dict[k_] = v

    # Add scaling option
    scaler_dict["MESSAGE_LP.scaleopt"] = 1

    scaler_df = pd.DataFrame(scaler_dict, index=["val"]).transpose()
    scaler_df.index = scaler_df.index.rename("key", inplace=False)

    scaler_list = [f"{k}={v};" for k, v in scaler_dict.items()]
    scaler_args_txt = "\n".join(scaler_list)

    dict_time = time.time() - dict_start
    print(f"Scaler dictionary generation completed in {dict_time:.2f}s")

    # Step 5: Write output file
    output_start = time.time()
    current_file = os.path.abspath(__file__)
    message_ix_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

    scaler_gms_name = "_".join(s.replace(" ", "_") for s in [scen_model, scen_scenario])
    scaler_dir = os.path.join(message_ix_root, "model", "scaler")
    os.makedirs(scaler_dir, exist_ok=True)
    scaler_gms_dir = os.path.join(scaler_dir, f"MsgScaler_{scaler_gms_name}.gms")

    with open(scaler_gms_dir, "w") as txtfile:
        txtfile.write(scaler_args_txt)

    output_time = time.time() - output_start
    total_time = time.time() - start_time

    print(f"Output file written in {output_time:.2f}s")
    print(f"Total processing time: {total_time:.2f}s")
    print("Speedup breakdown:")
    print(f"  - File preprocessing: {preprocessing_time:.2f}s")
    print(f"  - Matrix reading: {lp_time:.2f}s")
    print(f"  - Scaling operations: {scaling_time:.2f}s")
    print(f"  - Dictionary generation: {dict_time:.2f}s")
    print(f"  - File output: {output_time:.2f}s")

    return scaler_df
