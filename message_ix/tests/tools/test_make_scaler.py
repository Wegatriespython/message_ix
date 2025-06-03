"""
Unit tests for the :mod:`message_ix.tools.make_scaler` module.
"""
import os
import shutil
import re

import numpy as np
import pandas as pd
import pytest

from message_ix.tools.make_scaler import (
    filter_df,
    make_logdf,
    get_lvl_ix,
    show_range,
    get_scaler_args,
    replace_spaces_in_quotes,
    return_spaces_in_quotes,
    make_scaler,
)
from message_ix.tools.make_scaler.scaler_optim import (
    optimized_filter_df,
    optimized_make_logdf,
    get_lvl_ix as get_lvl_ix_opt,
    show_range as show_range_opt,
    make_scaler as make_scaler_opt,
)


@pytest.mark.parametrize("func", [filter_df, optimized_filter_df])
def test_filter_df_int_bounds(func):
    df = pd.DataFrame({"val": [-3, -1, 0, 2, 5]})
    result = func(df, 2)
    # Values <= -2 or >= 2 are kept
    assert list(result["val"]) == [-3, 2, 5]


@pytest.mark.parametrize("func", [filter_df, optimized_filter_df])
def test_filter_df_list_bounds(func):
    df = pd.DataFrame({"val": [-3, -1, 0, 1, 3]})
    result = func(df, [-1, 1])
    # Values <= -1 or >= 1 are kept
    assert list(result["val"]) == [-3, -1, 1, 3]


@pytest.mark.parametrize("func", [make_logdf, optimized_make_logdf])
def test_make_logdf(func):
    df = pd.DataFrame({"val": [-100, -10, 0, 10, 100]})
    result = func(df)
    # log10 of absolute nonzero values; zero remains zero
    assert list(result["val"]) == [2, 1, 0, 1, 2]
    # Original DataFrame is not modified
    assert list(df["val"]) == [-100, -10, 0, 10, 100]


@pytest.mark.parametrize("func", [get_lvl_ix, get_lvl_ix_opt])
def test_get_lvl_ix(func):
    idx = pd.MultiIndex.from_product([
        ["r1", "r2"],
        ["c1", "c2"]
    ], names=("row", "col"))
    df = pd.DataFrame({"val": [1, 2, 3, 4]}, index=idx)
    # integer-level selection
    lvl0 = func(df, 0)
    assert list(lvl0) == ["r1", "r1", "r2", "r2"]
    # name-level selection
    lvl1 = func(df, "col")
    assert list(lvl1) == ["c1", "c2", "c1", "c2"]


@pytest.mark.parametrize("func", [show_range, show_range_opt])
def test_show_range(func, capsys):
    df = pd.DataFrame({"val": [0, 1, 10, 100]})
    # log10 abs values: [0,1,2] => range [0 | 2]
    func(df, "test")
    captured = capsys.readouterr().out
    assert "test:" in captured
    assert "[ 0 | 2 ]" in captured


def test_replace_and_return_spaces_in_quotes():
    pattern = re.compile(r"'([^']*)'")
    text = "A 'foo bar baz' test"
    replaced = pattern.sub(replace_spaces_in_quotes, text)
    assert replaced == "A 'foo___bar___baz' test"
    # reverse the placeholder back to spaces
    restored = pattern.sub(return_spaces_in_quotes, "A 'foo---bar---baz' test")
    assert restored == "A 'foo bar baz' test"


def test_get_scaler_args_default_and_error(tmp_path, monkeypatch, capsys):
    # Default branch: use model/scenario
    model, scenario = "M", "S"
    file_name = f"MsgScaler_{model}_{scenario}"
    # Create expected scaler file two levels up under model/scaler
    root = tmp_path
    (root / "model" / "scaler").mkdir(parents=True)
    (root / "model" / "scaler" / f"{file_name}.gms").write_text("x")
    # Change cwd to two levels down
    workdir = root / "a" / "b"
    workdir.mkdir(parents=True)
    monkeypatch.chdir(workdir)
    arg = get_scaler_args(model=model, scenario=scenario)
    assert arg == f"--scaler={file_name}"
    # Remove file to test error path
    (root / "model" / "scaler" / f"{file_name}.gms").unlink()
    arg2 = get_scaler_args(model=model, scenario=scenario)
    assert arg2 is None
    err = capsys.readouterr().out
    assert "doesn't have prescaler file" in err


def test_get_scaler_args_ref_model_branch(tmp_path, monkeypatch):
    # Ref-model branch: ignore model/scenario kwargs
    ref_model, ref_scenario = "RefModel", "RefScenario"
    file_name = f"MsgScaler_{ref_model}_{ref_scenario}"
    root = tmp_path
    (root / "model" / "scaler").mkdir(parents=True)
    (root / "model" / "scaler" / f"{file_name}.gms").write_text("")
    workdir = root / "x" / "y"
    workdir.mkdir(parents=True)
    monkeypatch.chdir(workdir)
    arg = get_scaler_args(ref_model, ref_scenario, model="ignored", scenario="ignored2")
    assert arg == f"--scaler={file_name}"


@pytest.mark.parametrize("scaler_fn", [make_scaler, make_scaler_opt])
def test_make_scaler_end_to_end(tmp_path, monkeypatch, test_data_path, scaler_fn):
    # Prepare working directory two levels down
    root = tmp_path
    workdir = root / "work" / "here"
    workdir.mkdir(parents=True)
    monkeypatch.chdir(workdir)
    # Create model/scaler directory two levels up
    scaler_dir = root / "model" / "scaler"
    scaler_dir.mkdir(parents=True)
    # Copy small MPS from test data
    src = test_data_path / "lp_diag" / "diet.mps"
    mps_file = workdir / "diet.mps"
    shutil.copy(src, mps_file)
    # Run make_scaler with minimal bounds and steps, no printing
    df = scaler_fn(str(mps_file), "M", "S", bounds=1, steps=1, display_range=False)
    assert isinstance(df, pd.DataFrame)
    # Must include the active scaling option
    assert "MESSAGE_LP.scaleopt" in df.index
    # Check that the .gms file was written correctly
    gms = root / "model" / "scaler" / "MsgScaler_M_S.gms"
    assert gms.exists()
    content = gms.read_text().strip().splitlines()
    # Each line ends with a semicolon and count matches DataFrame rows
    assert all(line.endswith(";") for line in content)
    assert len(content) == len(df)
    # Compare generated GAMS scaler code to ground truth (order-independent)
    expected = (test_data_path / "make_scaler" / "MsgScaler_M_S.gms").read_text().strip().splitlines()
    assert sorted(content) == sorted(expected)