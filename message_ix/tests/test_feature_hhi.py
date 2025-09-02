"""Tests for Herfindahl-Hirschman Index (HHI) regularization feature.

These tests verify that the HHI regularization prevents corner solutions
and promotes balanced technology portfolios in energy system optimization.
"""

import numpy as np
import pandas as pd
import pytest
from ixmp import Platform

from message_ix import Scenario, make_df


def _create_hhi_test_scenario(
    mp: Platform,
    request: pytest.FixtureRequest,
    years: list,
    hhi_limit_time_value: float | None,
) -> Scenario:
    """Create a 3-technology energy system for testing time-HHI functionality.

    The scenario includes coal, gas, and solar technologies with costs structured
    to create potential investment concentration in specific periods.

    Parameters
    ----------
    mp : Platform
        Platform on which to create the scenario.
    request : pytest.FixtureRequest
        Pytest fixture for unique scenario naming.
    years : list
        List of model years for the time horizon.
    hhi_limit_time_value : float, optional
        Time HHI limit value (0 to 1). If provided, adds as parameter to scenario.
        Value > 1 effectively means no limit.

    Returns
    -------
    Scenario
        Configured scenario ready for time-HHI testing.
    """
    # Add required units
    mp.add_unit("USD/kW")
    mp.add_unit("USD/MWh")

    # Create scenario
    scen = Scenario(
        mp, model="HHI Test Model", scenario=request.node.name, version="new"
    )

    # Time structure with provided years
    scen.add_horizon(year=years)
    year_df = scen.vintage_and_active_years()

    # Spatial structure: single node
    node = "TestRegion"
    scen.add_spatial_sets({"country": node})

    # Basic sets
    commodities = ["electricity"]
    technologies = ["solar_pv"]
    levels = ["secondary"]
    modes = ["standard"]

    for set_name, values in [
        ("commodity", commodities),
        ("technology", technologies),
        ("level", levels),
        ("mode", modes),
    ]:
        scen.add_set(set_name, values)

    # Common parameters for make_df
    common = {
        "node_loc": node,
        "node_dest": node,
        "node_origin": node,
        "node": node,
        "time": "year",
        "time_dest": "year",
        "time_origin": "year",
        "mode": "standard",
    }

    with scen.transact("Build HHI test scenario"):
        # Interest rate
        scen.add_par(
            "interestrate", make_df("interestrate", year=years, value=0.05, unit="-")
        )

        # Growing electricity demand with 5% growth per year elapsed
        demand_values = []
        for i, year in enumerate(years):
            years_elapsed = year - years[0]
            demand = 100 * (1.05**years_elapsed)
            demand_values.append(demand)

        scen.add_par(
            "demand",
            make_df(
                "demand",
                **common,
                year=years,
                commodity="electricity",
                level="secondary",
                value=demand_values,
                unit="GWa",
            ),
        )

        # Technology outputs: all produce electricity
        for tech in technologies:
            scen.add_par(
                "output",
                make_df(
                    "output",
                    **common,
                    technology=tech,
                    commodity="electricity",
                    level="secondary",
                    year_vtg=year_df["year_vtg"],
                    year_act=year_df["year_act"],
                    value=1.0,
                    unit="-",
                ),
            )

        # Technical lifetime: 30 years for all technologies
        for tech in technologies:
            scen.add_par(
                "technical_lifetime",
                make_df(
                    "technical_lifetime",
                    **common,
                    technology=tech,
                    year_vtg=years,
                    value=40,
                    unit="y",
                ),
            )

        # Capacity factors
        capacity_factors = {
            "solar_pv": 0.25,  # Low capacity factor (realistic for solar)
        }

        for tech, cf_value in capacity_factors.items():
            scen.add_par(
                "capacity_factor",
                make_df(
                    "capacity_factor",
                    **common,
                    technology=tech,
                    year_vtg=year_df["year_vtg"],
                    year_act=year_df["year_act"],
                    value=cf_value,
                    unit="-",
                ),
            )

        # Investment costs (USD/kW) - structured to favor coal
        inv_costs = {
            "solar_pv": 2000,  # High investment cost → penalized
        }

        for tech, cost in inv_costs.items():
            scen.add_par(
                "inv_cost",
                make_df(
                    "inv_cost",
                    **common,
                    technology=tech,
                    year_vtg=years,
                    value=cost,
                    unit="USD/kW",
                ),
            )

        # Variable costs (USD/MWh) - structured to favor coal
        var_costs = {
            "solar_pv": 0,  # No variable cost (fuel free)
        }

        for tech, cost in var_costs.items():
            # Convert to USD/GWa: cost_MWh * 1000 MWh/GWh * 8760 h/year / 1000 GWh/GWa
            cost_gwa = cost * 8760
            scen.add_par(
                "var_cost",
                make_df(
                    "var_cost",
                    **common,
                    technology=tech,
                    year_vtg=year_df["year_vtg"],
                    year_act=year_df["year_act"],
                    value=cost_gwa,
                    unit="USD/GWa",
                ),
            )

        # Fixed costs (minimal for all)
        for tech in technologies:
            scen.add_par(
                "fix_cost",
                make_df(
                    "fix_cost",
                    **common,
                    technology=tech,
                    year_vtg=year_df["year_vtg"],
                    year_act=year_df["year_act"],
                    value=10,
                    unit="USD/kW",
                ),
            )

        # Add hhi_limit_time if provided
        if hhi_limit_time_value is not None:
            hhi_data = []
            hhi_data.append(
                {
                    "node": node,
                    "value": hhi_limit_time_value,
                    "unit": "-",
                }
            )

            hhi_df = pd.DataFrame(hhi_data)
            scen.add_par("hhi_limit_time", hhi_df)

    return scen


def _calculate_time_hhi(cap_new_data: pd.DataFrame, years: list) -> float:
    """Calculate period-length invariant temporal HHI for investment concentration across time periods.

    Implements: HHI_time = Σ_y (x_y²/L_y) / T²
    where x_y = CAP_NEW in year y, L_y = period length, T = Σ_y x_y

    Parameters
    ----------
    cap_new_data : pd.DataFrame
        New capacity data from scenario solution with 'year_vtg' and 'lvl' columns.
    years : list
        List of model years to calculate period lengths.

    Returns
    -------
    float
        Period-length invariant time HHI value.
    """
    # Sum new capacity by year (aggregated across technologies)
    year_totals = cap_new_data.groupby("year_vtg")["lvl"].sum()
    total_capacity = year_totals.sum()

    if total_capacity == 0:
        return 0.0

    # Calculate period-length invariant HHI
    hhi_sum = 0.0
    for year in years:
        if year in year_totals.index:
            x_y = year_totals[year]

            # Calculate period length
            if year == years[0]:
                L_y = years[1] - years[0] if len(years) > 1 else 1
            elif year == years[-1]:
                L_y = years[-1] - years[-2]
            else:
                idx = years.index(year)
                L_y = years[idx + 1] - year

            # Add period-weighted contribution: x_y²/L_y
            hhi_sum += (x_y**2) / L_y

    # Period-length invariant HHI = Σ(x_y²/L_y) / T²
    hhi = hhi_sum / (total_capacity**2)

    return hhi


@pytest.mark.parametrize(
    "years,hhi_limit_time",
    [
        # Uniform cases
        pytest.param(
            [2020, 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060, 2065, 2070],
            0.025,
            id="all_5year_hhi_0.025",
        ),
        pytest.param(
            [2020, 2030, 2040, 2050, 2060, 2070],
            0.025,
            id="all_10year_hhi_0.025",
        ),
        # Non-uniform cases
        pytest.param(
            [2020, 2025, 2030, 2035, 2040, 2050, 2060, 2070],
            0.025,
            id="5year_to_10year_hhi_0.025",
        ),
        # Different HHI limits
        pytest.param(
            [2020, 2025, 2030, 2035, 2040, 2050, 2060, 2070],
            0.08,
            id="5year_to_10year_hhi_0.08",
        ),
        pytest.param(
            [2020, 2025, 2030, 2035, 2040, 2050, 2060, 2070],
            1.01,
            id="5year_to_10year_no_limit",
        ),
        # Baseline without HHI constraint
        pytest.param(
            [2020, 2025, 2030, 2035, 2040, 2050, 2060, 2070],
            None,
            id="5year_to_10year_baseline_no_HHI",
        ),
    ],
)
def test_time_hhi_hard_cap(
    test_mp: Platform,
    request: pytest.FixtureRequest,
    years: list,
    hhi_limit_time: float,
) -> None:
    """Test that time-HHI hard cap constraint enforces temporal investment diversity.

    Tests both uniform and non-uniform period structures with different HHI limits
    to verify the period-length invariant constraint is working correctly.

    Parameters
    ----------
    test_mp : Platform
        Test platform fixture.
    request : pytest.FixtureRequest
        Pytest request fixture for scenario naming.
    years : list
        List of model years defining the time horizon.
    hhi_limit_time : float
        Time HHI limit value (0 to 1, or > 1 for no limit).
    """
    # Create scenario with time-HHI limit
    scen = _create_hhi_test_scenario(test_mp, request, years, hhi_limit_time)

    # Solve with or without HHI constraint
    if hhi_limit_time is None:
        scen.solve(quiet=True)  # Baseline without HHI
    else:
        scen.solve(quiet=True, gams_args=["--HHI=1"])  # With HHI constraint

    # Extract new capacity results
    cap_new = scen.var("CAP_NEW")

    # Get demand data for comparison
    demand_data = scen.par("demand", {"commodity": "electricity"})

    # Print formatted table output
    print(f"\nYears: {years}, HHI Limit: {hhi_limit_time}")
    print("| Year | CAP_NEW | Demand | Period_Length |")
    print("|------|---------|--------|---------------|")

    total_cap_new_by_year = {}
    for year in years:
        year_cap_new = cap_new[(cap_new.year_vtg == year)]

        # Get total capacity across all technologies (excluding World)
        total_cap = year_cap_new["lvl"].sum()
        total_cap_new_by_year[year] = total_cap

        # Get demand for this year
        year_demand = demand_data[demand_data.year == year]["value"].sum()

        # Calculate period length (years between this year and next, or from previous)
        if year == years[0]:
            period_length = years[1] - years[0] if len(years) > 1 else 1
        elif year == years[-1]:
            period_length = years[-1] - years[-2]
        else:
            idx = years.index(year)
            period_length = years[idx + 1] - year

        print(f"| {year} | {total_cap:.6f} | {year_demand:.6f} | {period_length} |")

    print()

    # Filter for positive new capacity and exclude World node
    investment_data = cap_new[(cap_new["lvl"] > 0)].copy()

    # Calculate temporal HHI concentration metric
    temporal_hhi = _calculate_time_hhi(investment_data, years)

    print(f"Calculated temporal HHI: {temporal_hhi:.3f}")

    if hhi_limit_time is None:
        # Baseline case - just report results, no assertions
        print("Baseline case (no HHI constraint)")
        return
    elif hhi_limit_time > 1.0:
        # No effective limit: expect temporal concentration
        assert temporal_hhi > 0.6, (
            f"With time HHI limit > 1 (no constraint), should get temporal concentration. "
            f"Expected HHI > 0.6, got {temporal_hhi:.3f}"
        )

        # Verify one period dominates investments
        year_totals = investment_data.groupby("year_vtg")["lvl"].sum()
        if year_totals.sum() > 0:
            max_share = year_totals.max() / year_totals.sum()
            assert max_share > 0.7, (
                f"One period should dominate (>70% share) with no time HHI limit, "
                f"max share: {max_share:.2%}"
            )
    else:
        # Time HHI limit enforced: verify constraint is satisfied
        # Allow small tolerance for numerical precision
        tolerance = 0.01
        assert temporal_hhi <= hhi_limit_time + tolerance, (
            f"Time HHI constraint violated: limit={hhi_limit_time}, actual={temporal_hhi:.3f}"
        )

        # Verify temporal diversification
        year_totals = investment_data.groupby("year_vtg")["lvl"].sum()
        if year_totals.sum() > 0:
            max_share = year_totals.max() / year_totals.sum()

            # For 3 periods, maximum theoretical share given HHI limit
            # Similar calculation as before but for time periods
            num_periods = len(year_totals)
            if num_periods > 1:
                # Theoretical maximum share for dominant period
                discriminant = 1 - (num_periods - 1) * (
                    1 / num_periods - hhi_limit_time
                )
                if discriminant >= 0:
                    max_theoretical_share = (
                        1 + np.sqrt(discriminant * (num_periods - 1))
                    ) / num_periods
                else:
                    max_theoretical_share = 1.0 / num_periods  # Equal shares

                # Allow tolerance for numerical precision and solver approximations
                assert max_share <= max_theoretical_share + 0.1, (
                    f"Period share exceeds theoretical maximum for time HHI={hhi_limit_time}. "
                    f"Max share: {max_share:.2%}, theoretical max: {max_theoretical_share:.2%}"
                )

    # Verify total investment capacity is reasonable
    total_investment = investment_data["lvl"].sum()
    assert total_investment > 0, "Should have some investment capacity"
