"""Test for PRICE_COMMODITY spikes with non-uniform duration periods.

This test reproduces the issue reported in GitHub Issue #973 where commodity
prices show unexpected spikes at transitions between periods of different
durations (e.g., 5-year to 10-year periods).
"""

import pytest

from message_ix import Scenario, make_df


def build_scenario(test_mp, years, interestrate):
    test_mp.add_unit("USD/GWa")
    test_mp.add_unit("GWa")
    test_mp.add_unit("-")
    test_mp.add_unit("%")
    test_mp.add_unit("y")

    scen = Scenario(test_mp, "test_price_spike", "standard", version="new")

    scen.add_horizon(year=years, firstmodelyear=years[0])

    # Basic sets
    scen.add_set("node", "region")
    scen.add_set("commodity", "electricity")
    scen.add_set("level", "secondary")
    scen.add_set("mode", "standard")
    scen.add_set("technology", ["gas"])

    year_df = scen.vintage_and_active_years()

    # 1 tech is sufficient, but to guarantee resolution,
    # should use more techs which are all used by the model.
    tec = "gas"
    inv_cost = 800
    var_cost = 50
    lifetime = 30
    scen.add_par(
        "output",
        make_df(
            "output",
            node_loc="region",
            technology=tec,
            year_vtg=year_df["year_vtg"],
            year_act=year_df["year_act"],
            mode="standard",
            node_dest="region",
            commodity="electricity",
            level="secondary",
            time="year",
            time_dest="year",
            value=1.0,
            unit="GWa",
        ),
    )

    scen.add_par(
        "inv_cost",
        make_df(
            "inv_cost",
            node_loc="region",
            technology=tec,
            year_vtg=years,
            value=inv_cost,
            unit="USD/GWa",
        ),
    )

    scen.add_par(
        "var_cost",
        make_df(
            "var_cost",
            node_loc="region",
            technology=tec,
            year_vtg=year_df["year_vtg"],
            year_act=year_df["year_act"],
            mode="standard",
            time="year",
            value=var_cost,
            unit="USD/GWa",
        ),
    )

    scen.add_par(
        "technical_lifetime",
        make_df(
            "technical_lifetime",
            node_loc="region",
            technology=tec,
            year_vtg=years,
            value=lifetime,
            unit="y",
        ),
    )

    scen.add_par(
        "capacity_factor",
        make_df(
            "capacity_factor",
            node_loc="region",
            technology=tec,
            year_vtg=year_df["year_vtg"],
            year_act=year_df["year_act"],
            time="year",
            value=1.0,
            unit="-",
        ),
    )

    for i, year in enumerate(years):
        years_elapsed = year - years[0]  # Time elapsed s.t invariant to period length
        demand = 100 * (1.05**years_elapsed)  # Need growth to reproduce the issue.
        scen.add_par(
            "demand",
            make_df(
                "demand",
                node="region",
                commodity="electricity",
                level="secondary",
                year=year,
                time="year",
                value=demand,
                unit="GWa",
            ),
        )

    # Interest rate
    scen.add_par(
        "interestrate",
        make_df("interestrate", year=years, value=interestrate, unit="%"),
    )

    scen.commit("Test scenario setup complete")
    return scen


# commented out 1 year,
# FIXME: very slow on ixmp
@pytest.mark.parametrize(
    "years,interestrate",
    [
        # # Uniform cases - these should PASS
        # pytest.param(
        #     list(range(2020, 2071)),  # All 1-year periods from 2020-2070
        #     0.05,
        #     id="all_1year_5pct",
        # ),
        pytest.param(
            [2020, 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060, 2065, 2070],
            0.05,
            id="all_5year_5pct",
        ),
        pytest.param(
            [2020, 2030, 2040, 2050, 2060, 2070],
            0.05,
            id="all_10year_5pct",
        ),
        # Non-uniform cases - these should FAIL
        # pytest.param(
        #     list(range(2020, 2041))
        #     + [2045, 2050, 2055, 2060, 2065, 2070],  # 1-year till 2040, then 5-year
        #     0.05,
        #     id="1year_to_5year_5pct",
        # ),
        pytest.param(
            [2020, 2025, 2030, 2035, 2040, 2050, 2060, 2070],
            0.05,
            id="5year_to_10year_5pct",
        ),
        pytest.param(
            [2020, 2025, 2030, 2035, 2040, 2050, 2060, 2070],
            0.10,
            id="5year_to_10year_10pct",
        ),
        pytest.param(
            [2020, 2025, 2030, 2035, 2040, 2050, 2060, 2070],
            0.00,
            id="5year_to_10year_0pct",  # this will pass
        ),
    ],
)
def test_price_spike(test_mp, years, interestrate):
    """Test that no price spikes occur at period duration transitions.

    This test should FAIL for non-uniform period structure
    and PASS for uniform period structures.
    """
    scen = build_scenario(test_mp, years, interestrate)
    scen.solve(quiet=True)

    prices = scen.var("PRICE_COMMODITY", {"commodity": "electricity"})

    # Collect all data for formatted table output
    act_full = scen.var("ACT", {"technology": "gas"})
    cap_new_full = scen.var("CAP_NEW", {"technology": "gas"})
    cap_full = scen.var("CAP", {"technology": "gas"})
    demand_full = scen.par("demand", {"commodity": "electricity"})

    print(f"\nYears: {years}, Interest Rate: {interestrate}")
    print("| Year | ACT | CAP_NEW | CAP | Demand | Price |")
    print("|------|------------|-----------|------------|------------|------------|")

    for year in years:
        year_act = act_full[act_full.year_act == year]["lvl"].sum()

        cap_new_data = cap_new_full[cap_new_full.year_vtg == year]
        year_cap_new = cap_new_data.at[cap_new_data.index[0], "lvl"]

        year_cap = cap_full[cap_full.year_vtg == year]["lvl"].sum()

        year_demand = demand_full[demand_full.year == year]["value"].sum()

        year_price_data = prices[prices.year == year]
        year_price = year_price_data["lvl"].values[0]

        print(
            f"| {year} | {year_act:.6f} | {year_cap_new:.6f} | "
            f"{year_cap:.6f} | {year_demand:.6f} | {year_price:.6f} |"
        )

    print()

    # Check consecutive year price changes
    for i in range(1, len(years)):
        prev_year = years[i - 1]
        curr_year = years[i]

        prev_price = prices[prices.year == prev_year]["lvl"].values
        curr_price = prices[prices.year == curr_year]["lvl"].values

        if len(prev_price) > 0 and len(curr_price) > 0:
            ratio = curr_price[0] / prev_price[0]

            # Assert no spike greater than 10%
            # FIXME : Use a better metric for this issue
            assert ratio <= 1.10, (
                f"Price spike detected: {curr_year}/{prev_year} = {ratio:.3f} "
                f"(>{1.10:.2f} threshold). Prices: {prev_year}={prev_price[0]:.2f}, "
                f"{curr_year}={curr_price[0]:.2f}"
            )

    return scen
