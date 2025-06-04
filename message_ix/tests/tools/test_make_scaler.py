"""
Unit tests for the :mod:`message_ix.tools.make_scaler` module.

These tests validate the functionality of make_scaler tools including proper GAMS syntax
generation, quote handling, and edge cases discovered through development. Tests survive
edge cases including:
- Parameters already containing single quotes in MPS files
- Complex constraint names with special characters (pipes, underscores)
- Multi-dimensional constraint parameters requiring proper quoting
- Numerical scaling factor generation and validation

To add future edge cases: extend test_baseline_sample_syntax_validation with new MPS
patterns or create specific test cases for newly discovered syntax issues.
"""

import os
import shutil
import re
import tempfile

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
    """Test filter_df with integer bounds parameter."""
    df = pd.DataFrame({"val": [-3, -1, 0, 2, 5]})
    result = func(df, 2)
    # Values <= -2 or >= 2 are kept
    assert list(result["val"]) == [-3, 2, 5]


@pytest.mark.parametrize("func", [filter_df, optimized_filter_df])
def test_filter_df_list_bounds(func):
    """Test filter_df with list bounds parameter."""
    df = pd.DataFrame({"val": [-3, -1, 0, 1, 3]})
    result = func(df, [-1, 1])
    # Values <= -1 or >= 1 are kept
    assert list(result["val"]) == [-3, -1, 1, 3]


@pytest.mark.parametrize("func", [make_logdf, optimized_make_logdf])
def test_make_logdf(func):
    """Test make_logdf log10 transformation of DataFrame values."""
    df = pd.DataFrame({"val": [-100, -10, 0, 10, 100]})
    result = func(df)
    # log10 of absolute nonzero values; zero remains zero
    assert list(result["val"]) == [2, 1, 0, 1, 2]
    # Original DataFrame is not modified
    assert list(df["val"]) == [-100, -10, 0, 10, 100]


@pytest.mark.parametrize("func", [get_lvl_ix, get_lvl_ix_opt])
def test_get_lvl_ix(func):
    """Test get_lvl_ix level index extraction from MultiIndex DataFrame."""
    idx = pd.MultiIndex.from_product([["r1", "r2"], ["c1", "c2"]], names=("row", "col"))
    df = pd.DataFrame({"val": [1, 2, 3, 4]}, index=idx)
    # integer-level selection
    lvl0 = func(df, 0)
    assert list(lvl0) == ["r1", "r1", "r2", "r2"]
    # name-level selection
    lvl1 = func(df, "col")
    assert list(lvl1) == ["c1", "c2", "c1", "c2"]


@pytest.mark.parametrize("func", [show_range, show_range_opt])
def test_show_range(func, capsys):
    """Test show_range coefficient exponent display function."""
    df = pd.DataFrame({"val": [0, 1, 10, 100]})
    # log10 abs values: [0,1,2] => range [0 | 2]
    func(df, "test")
    captured = capsys.readouterr().out
    assert "test:" in captured
    assert "[ 0 | 2 ]" in captured


def test_replace_and_return_spaces_in_quotes():
    """Test replace_spaces_in_quotes and return_spaces_in_quotes functions."""
    pattern = re.compile(r"'([^']*)'")
    text = "A 'foo bar baz' test"
    replaced = pattern.sub(replace_spaces_in_quotes, text)
    assert replaced == "A 'foo___bar___baz' test"
    # reverse the placeholder back to spaces
    restored = pattern.sub(return_spaces_in_quotes, "A 'foo---bar---baz' test")
    assert restored == "A 'foo bar baz' test"


def test_get_scaler_args_missing_file(capsys):
    """Test get_scaler_args error handling when scaler file is missing."""
    model, scenario = "NonExistent", "Test"
    arg = get_scaler_args(model=model, scenario=scenario)
    assert arg is None
    err = capsys.readouterr().out
    assert "doesn't have prescaler file" in err


@pytest.mark.parametrize("scaler_fn", [make_scaler, make_scaler_opt])
def test_sample_syntax_validation(test_data_path, scaler_fn):
    """Test make_scaler GAMS syntax generation with baseline.mps sample data.

    This test uses a permanent sample of 1000 constraints from baseline.mps to validate:
    - Proper quoting of multi-dimensional constraint parameters
    - Handling of already-quoted parameters (edge case)
    - Complex constraint names with special characters
    - Correct GAMS syntax structure and semicolon termination
    - No double-quoting issues

    The test data includes real MESSAGE-ix constraints and covers edge cases discovered
    during development, particularly handling of parameters like
    'Emissions|OC|AFOLU|Fires|Peat___Burning' that already contain quotes.
    """

    # Use permanent test data
    mps_file = test_data_path / "make_scaler" / "baseline_sample.mps"
    assert mps_file.exists(), f"Test data not found: {mps_file}"

    # Create temporary directory for scaler output
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Run make_scaler with the baseline sample
        scaler_df = scaler_fn(
            path=str(mps_file),
            scen_model="baseline_sample",
            scen_scenario="syntax_test",
            bounds=2,  # Use reasonable bounds to get subset of constraints
            steps=1,
            display_range=False,
        )

        # Verify DataFrame structure
        assert isinstance(scaler_df, pd.DataFrame)
        assert "MESSAGE_LP.scaleopt" in scaler_df.index

        # Read the generated scaler file
        scaler_file_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "model",
            "scaler",
            "MsgScaler_baseline_sample_syntax_test.gms",
        )

        assert os.path.exists(scaler_file_path), (
            f"Scaler file not generated at {scaler_file_path}"
        )

        with open(scaler_file_path, "r") as f:
            scaler_lines = f.read().strip().split("\n")

        # Exhaustive syntax validation
        errors = []
        for line_num, line in enumerate(scaler_lines, 1):
            line = line.strip()
            if not line:
                continue

            # Check basic structure: should end with semicolon
            if not line.endswith(";"):
                errors.append(f"Line {line_num}: Missing semicolon: {line}")
                continue

            # Remove semicolon for parsing
            statement = line[:-1]

            # Check for assignment operator
            if "=" not in statement:
                errors.append(f"Line {line_num}: Missing assignment operator: {line}")
                continue

            # Split into left and right parts
            parts = statement.split("=", 1)
            if len(parts) != 2:
                errors.append(f"Line {line_num}: Invalid assignment format: {line}")
                continue

            left_part = parts[0].strip()
            right_part = parts[1].strip()

            # Validate right part is a valid number
            try:
                float(right_part)
            except ValueError:
                errors.append(
                    f"Line {line_num}: Invalid numeric value '{right_part}': {line}"
                )

            # Check left part structure
            if left_part == "MESSAGE_LP.scaleopt":
                # Special case for the scaleopt parameter
                continue
            elif ".scale" in left_part:
                # Check for parameters in parentheses
                if "(" in left_part and ")" in left_part:
                    # Extract parameters
                    start_paren = left_part.index("(")
                    end_paren = left_part.rindex(")")
                    param_string = left_part[start_paren + 1 : end_paren]

                    # Check if parameters are quoted
                    params = param_string.split(",")
                    for param in params:
                        param = param.strip()
                        if param and not (
                            param.startswith("'") and param.endswith("'")
                        ):
                            errors.append(
                                f"Line {line_num}: Unquoted parameter '{param}': {line}"
                            )

                        # Check for double quotes (indicates over-quoting)
                        if param.startswith("''") and param.endswith("''"):
                            errors.append(
                                f"Line {line_num}: Double-quoted parameter '{param}': {line}"
                            )

                    # Check for unquoted identifiers (common GAMS identifiers that should be quoted)
                    # Look for patterns like R12_XXX, year, all, etc. without quotes
                    unquoted_pattern = re.compile(
                        r'\b(R\d+_\w+|year|all|final|secondary|import|export)\b(?![\'"])'
                    )
                    if unquoted_pattern.search(param_string):
                        errors.append(
                            f"Line {line_num}: Found unquoted identifier in parameters: {line}"
                        )
            else:
                errors.append(
                    f"Line {line_num}: Invalid scale statement format: {line}"
                )

        # Report all errors found
        if errors:
            error_report = "\n".join(errors)
            pytest.fail(f"Syntax validation errors found:\n{error_report}")

        # Additional check: ensure no unquoted parameter patterns exist anywhere
        full_content = "\n".join(scaler_lines)

        # Pattern to find scale( followed by unquoted parameters
        unquoted_scale_pattern = re.compile(
            r"\.scale\([^)]*[,\(]\s*([A-Za-z_]\w*)\s*[,\)]"
        )
        matches = unquoted_scale_pattern.findall(full_content)
        unquoted_params = [
            m for m in matches if not m.startswith("'") and m != "MESSAGE_LP"
        ]

        if unquoted_params:
            pytest.fail(
                f"Found unquoted parameters in scale statements: {unquoted_params}"
            )

        # Verify minimum expected content
        assert len(scaler_lines) > 1, (
            "Scaler file should contain more than just MESSAGE_LP.scaleopt"
        )

        # Check that complex constraint types are handled
        complex_constraints_found = any(
            any(
                constraint_type in line
                for constraint_type in [
                    "EMISSION_EQUIVALENCE",
                    "COMMODITY_BALANCE",
                    "ACTIVITY_BOUND",
                    "CAPACITY_CONSTRAINT",
                    "RELATION_EQUIVALENCE",
                ]
            )
            for line in scaler_lines
        )
        assert complex_constraints_found, (
            "Expected complex constraint types in generated scaler"
        )

        # Clean up test scaler file
        if os.path.exists(scaler_file_path):
            os.remove(scaler_file_path)

