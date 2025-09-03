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
    mp: Platform, request: pytest.FixtureRequest, hhi_limit_value: float | None
) -> Scenario:
    """Create a 3-technology energy system for testing HHI functionality.

    The scenario includes coal, gas, and solar technologies with costs structured
    to favor coal in standard LP optimization (creating a corner solution).

    Parameters
    ----------
    mp : Platform
        Platform on which to create the scenario.
    request : pytest.FixtureRequest
        Pytest fixture for unique scenario naming.
    hhi_limit_value : float, optional
        HHI limit value (0 to 1). If provided, adds as parameter to scenario.
        Value > 1 effectively means no limit.

    Returns
    -------
    Scenario
        Configured scenario ready for HHI testing.
    """
    # Add required units
    mp.add_unit("USD/kW")
    mp.add_unit("USD/MWh")

    # Create scenario
    scen = Scenario(
        mp, model="HHI Test Model", scenario=request.node.name, version="new"
    )

    # Time structure: 3 periods with growing demand
    years = [2020, 2030, 2040]
    scen.add_horizon(year=years)
    year_df = scen.vintage_and_active_years()

    # Spatial structure: single node
    node = "TestRegion"
    scen.add_spatial_sets({"country": node})

    # Basic sets
    commodities = ["electricity"]
    technologies = ["coal_ppl", "gas_ppl", "solar_pv"]
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

        # Growing electricity demand: 100 -> 150 -> 200 GWa
        demand_values = [100.0, 150.0, 200.0]
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
                    value=30,
                    unit="y",
                ),
            )

        # Capacity factors
        capacity_factors = {
            "coal_ppl": 0.8,  # High capacity factor
            "gas_ppl": 0.7,  # Medium capacity factor
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
            "coal_ppl": 1000,  # Low investment cost → favored
            "gas_ppl": 800,  # Lower investment cost
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
            "coal_ppl": 20,  # Low variable cost → favored
            "gas_ppl": 35,  # Medium variable cost
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

        # Add hhi_limit if provided
        if hhi_limit_value is not None:
            # Create hhi_limit parameter for all nodes and the commodity group
            hhi_data = []
            for y in years:
                hhi_data.append(
                    {
                        "node": node,
                        "commodity": "electricity",
                        "level": "secondary",
                        "year": y,
                        "time": "year",
                        "value": hhi_limit_value,
                        "unit": "-",
                    }
                )

            hhi_df = pd.DataFrame(hhi_data)
            scen.add_par("hhi_limit", hhi_df)

    return scen


def _calculate_hhi(activity_data: pd.DataFrame) -> float:
    """Calculate Herfindahl-Hirschman Index for technology portfolio concentration.

    Parameters
    ----------
    activity_data : pd.DataFrame
        Activity data from scenario solution with 'technology' and 'lvl' columns.

    Returns
    -------
    float
        HHI value where 1.0 = complete concentration, 0.33 = equal 3-way split.
    """
    # Sum activity by technology
    tech_totals = activity_data.groupby("technology")["lvl"].sum()
    total_activity = tech_totals.sum()

    if total_activity == 0:
        return 0.0

    # Calculate shares
    shares = tech_totals / total_activity

    # HHI = sum of squared shares
    hhi = (shares**2).sum()

    return hhi


@pytest.mark.parametrize("hhi_limit", [1.01, 0.9, 0.8])
def test_hhi_hard_cap(
    test_mp: Platform,
    request: pytest.FixtureRequest,
    hhi_limit: float,
) -> None:
    """Test that HHI hard cap constraint enforces portfolio diversity.

    HHI limit > 1.0: No effective limit, expect corner solution.
    HHI limit = 0.9: Mild constraint on concentration.
    HHI limit = 0.8: Stronger constraint on concentration.

    Parameters
    ----------
    test_mp : Platform
        Test platform fixture.
    request : pytest.FixtureRequest
        Pytest request fixture for scenario naming.
    hhi_limit : float
        HHI limit value (0 to 1, or > 1 for no limit).
    """
    # Create scenario with HHI limit
    scen = _create_hhi_test_scenario(test_mp, request, hhi_limit)
    scen.solve(quiet=True, gams_args=["--HHI=1"])

    # Extract activity results
    activity = scen.var("ACT")

    # Filter for electricity-producing activities (positive output)
    electricity_activity = activity[activity["lvl"] > 0].copy()

    # Calculate HHI concentration metric
    portfolio_hhi = _calculate_hhi(electricity_activity)

    if hhi_limit > 1.0:
        # No effective limit: expect corner solution
        assert portfolio_hhi > 0.85, (
            f"With HHI limit > 1 (no constraint), should get corner solution. "
            f"Expected HHI > 0.85, got {portfolio_hhi:.3f}"
        )

        # Verify one technology dominates
        tech_totals = electricity_activity.groupby("technology")["lvl"].sum()
        max_share = tech_totals.max() / tech_totals.sum()
        assert max_share > 0.9, (
            f"One technology should dominate (>90% share) with no HHI limit, "
            f"max share: {max_share:.2%}"
        )
    else:
        # HHI limit enforced: verify constraint is satisfied
        # Allow small tolerance for numerical precision
        tolerance = 0.01
        assert portfolio_hhi <= hhi_limit + tolerance, (
            f"HHI constraint violated: limit={hhi_limit}, actual={portfolio_hhi:.3f}"
        )

        # Verify diversification based on limit level
        tech_totals = electricity_activity.groupby("technology")["lvl"].sum()
        max_share = tech_totals.max() / tech_totals.sum()

        # Maximum possible share given HHI limit (for dominant technology)
        # For 3 technologies: if one has share s, others have (1-s)/2 each
        # HHI = s² + 2×((1-s)/2)² = s² + (1-s)²/2
        # Setting HHI = hhi_limit and solving the quadratic:
        # 3s²/2 - s + 1/2 - hhi_limit = 0
        # Using quadratic formula: s = (1 ± sqrt(1 - 6(1/2 - hhi_limit)))/3
        discriminant = 1 - 6 * (0.5 - hhi_limit)
        if discriminant >= 0:
            max_theoretical_share = (1 + np.sqrt(discriminant)) / 3
        else:
            # If discriminant < 0, HHI limit is too low for 3 technologies
            max_theoretical_share = 1.0 / 3  # Equal shares

        # Allow tolerance for numerical precision and solver approximations
        assert max_share <= max_theoretical_share + 0.05, (
            f"Technology share exceeds theoretical maximum for HHI={hhi_limit}. "
            f"Max share: {max_share:.2%}, theoretical max: {max_theoretical_share:.2%}"
        )

    # Both cases should meet demand
    total_activity = electricity_activity["lvl"].sum()
    expected_total_demand = sum([100.0, 150.0, 200.0])  # Sum over all years

    # Allow for some tolerance due to numerical precision and capacity factors
    assert abs(total_activity - expected_total_demand) / expected_total_demand < 0.1, (
        f"Solution should approximately meet demand. "
        f"Expected ~{expected_total_demand}, got {total_activity}"
    )
