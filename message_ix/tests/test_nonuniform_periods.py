"""Test for PRICE_COMMODITY spikes with non-uniform duration periods.

This test reproduces the issue reported in GitHub Issue #973 where commodity
prices show unexpected spikes at transitions between periods of different
durations (e.g., 5-year to 10-year periods).
"""

import pytest

from message_ix import Scenario, make_df


def calculate_df_period(years, interest_rate):
    """
    Calculate df_period for each year using GAMS MESSAGE model formulas.

    Based on the recursive GAMS implementation:
    - df_year(first_year) = 1.0
    - df_year(year) = df_year(prev_year) * (1/(1+r))^duration_period(year)
    - df_period(year) = df_year(year) * ((1+r)^duration_period(year) - 1) / r

    Args:
        years: List of years (e.g., [2020, 2025, 2030, ...])
        interest_rate: Interest rate as decimal (e.g., 0.05 for 5%)

    Returns:
        dict: {year: df_period_value}
    """
    if not years:
        return {}

    # Calculate duration_period for each year (years until next period)
    durations = []
    for i in range(len(years) - 1):
        duration = years[i + 1] - years[i]
        durations.append(duration)
    # Last period duration (assume same as previous or default to 5)
    durations.append(durations[-1] if durations else 5)

    # GAMS recursive method for df_year calculation
    df_years = {}

    # Initialize first period: df_year = 1 (set to 1 by default)
    df_years[years[0]] = 1.0

    # Recursively compute df_year for subsequent periods
    for i in range(1, len(years)):
        year = years[i]
        prev_year = years[i - 1]
        duration = durations[i - 1]  # Duration of current period

        discount_factor = 1 / (1 + interest_rate)
        df_years[year] = df_years[prev_year] * (discount_factor**duration)

    # Calculate df_period for each year
    df_periods = {}
    for i, year in enumerate(years):
        duration_period = durations[i]
        df_year = df_years[year]

        # GAMS formula: df_period = df_year * ((1+r)^duration - 1) / r
        if interest_rate > 0:
            df_period = df_year * (
                ((1 + interest_rate) ** duration_period - 1) / interest_rate
            )
        else:
            # If interest rate = 0, multiply by duration_period
            df_period = df_year * duration_period

        df_periods[year] = df_period

    return df_periods


def build_scenario(
    test_mp, years, interestrate, historical_new_capacity=None, technical_lifetime=30, use_fix_cost=False
):
    test_mp.add_unit("USD/GWa")
    test_mp.add_unit("GWa")
    test_mp.add_unit("-")
    test_mp.add_unit("%")
    test_mp.add_unit("y")

    scen = Scenario(test_mp, "test_price_spike", "standard", version="new")

    # Add historical year 2015 before the first model year
    years = [2015] + years
    scen.add_horizon(year=years, firstmodelyear=years[1])

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
    
    if use_fix_cost:
        # Calculate annualized cost using capital recovery factor
        if interestrate > 0:
            crf = (interestrate * (1 + interestrate)**technical_lifetime) / ((1 + interestrate)**technical_lifetime - 1)
        else:
            crf = 1.0 / technical_lifetime
        
        inv_cost = 1e-6  # Small epsilon to avoid zero
        fix_cost = 800 * crf  # Annualized cost as fixed cost
        var_cost = 50
    else:
        inv_cost = 800
        fix_cost = 0
        var_cost = 50
    
    lifetime = technical_lifetime
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
    
    if fix_cost > 0:
        scen.add_par(
            "fix_cost",
            make_df(
                "fix_cost",
                node_loc="region",
                technology=tec,
                year_vtg=year_df["year_vtg"],
                year_act=year_df["year_act"],
                value=fix_cost,
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

    for i, year in enumerate(years[1:]):  # Skip historical year for demand
        years_elapsed = year - years[1]  # Time elapsed from first model year
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

    # Historical new capacity - now properly in historical period
    if historical_new_capacity is not None:
        scen.add_par(
            "historical_new_capacity",
            make_df(
                "historical_new_capacity",
                node_loc="region",
                technology=tec,
                year_vtg=years[0],  # Now this is 2015, the historical year
                value=historical_new_capacity,
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


def print_scenario_results(scen, model_years, interestrate):
    """Print formatted table of scenario results and return price data.

    Parameters
    ----------
    scen : Scenario
        The solved scenario
    model_years : list
        List of model years (excluding historical periods)
    interestrate : float
        Interest rate used in the scenario

    Returns
    -------
    dict
        Dictionary with year as key and price as value
    """
    prices = scen.var("PRICE_COMMODITY", {"commodity": "electricity"})

    # Calculate df_period values for all years using our utility function
    df_periods = calculate_df_period(model_years, interestrate)

    # Collect all data for formatted table output
    act_full = scen.var("ACT", {"technology": "gas"})
    cap_new_full = scen.var("CAP_NEW", {"technology": "gas"})
    cap_full = scen.var("CAP", {"technology": "gas"})
    demand_full = scen.par("demand", {"commodity": "electricity"})

    print(f"\nYears: {model_years}, Interest Rate: {interestrate}")
    print("| Year | ACT | CAP_NEW | CAP | Demand | Price | Dual_COMM_BAL_AUX |")
    print(
        "|------|------------|-----------|------------|------------|------------|-------------------|"
    )

    price_dict = {}

    for year in model_years:
        year_act = act_full[act_full.year_act == year]["lvl"].sum()

        cap_new_data = cap_new_full[cap_new_full.year_vtg == year]
        year_cap_new = cap_new_data.at[cap_new_data.index[0], "lvl"]

        # Sum CAP across all vintages that are active in this year
        year_cap = cap_full[cap_full.year_act == year]["lvl"].sum()

        year_demand = demand_full[demand_full.year == year]["value"].sum()

        year_price_data = prices[prices.year == year]
        year_price = year_price_data["lvl"].values[0]
        price_dict[year] = year_price

        # Calculate raw dual from PRICE_COMMODITY
        # (which = -COMMODITY_BALANCE_AUX.M / df_period)
        # So raw dual = -PRICE_COMMODITY * df_period
        df_period_val = df_periods[year]
        year_dual = -year_price * df_period_val

        print(
            f"| {year} | {year_act:.6f} | {year_cap_new:.6f} | "
            f"{year_cap:.6f} | {year_demand:.6f} | {year_price:.6f} | {year_dual:.6f} |"
        )

    print()

    return price_dict


def check_price_spikes(price_dict, threshold=1.10):
    """Check for price spikes between consecutive years.

    Parameters
    ----------
    price_dict : dict
        Dictionary with year as key and price as value
    threshold : float
        Maximum allowed price ratio between consecutive years
        (default 1.10 = 10% increase)

    Raises
    ------
    AssertionError
        If a price spike exceeding the threshold is detected
    """
    years = sorted(price_dict.keys())

    for i in range(1, len(years)):
        prev_year = years[i - 1]
        curr_year = years[i]

        prev_price = price_dict[prev_year]
        curr_price = price_dict[curr_year]

        ratio = curr_price / prev_price

        # Assert no spike greater than threshold
        assert ratio <= threshold, (
            f"Price spike detected: {curr_year}/{prev_year} = {ratio:.3f} "
            f"(>{threshold:.2f} threshold). Prices: {prev_year}={prev_price:.2f}, "
            f"{curr_year}={curr_price:.2f}"
        )


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
            [2020, 2025, 2030, 2035, 2040, 2046, 2053, 2061, 2070],
            0.05,
            id="5year_to_8year_5pct",
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

    # Note: years are the original model years passed to the test
    model_years = years

    # Print results table and get price dictionary
    price_dict = print_scenario_results(scen, model_years, interestrate)

    # Check for price spikes
    check_price_spikes(price_dict, threshold=1.10)

    return scen


@pytest.mark.parametrize(
    "years,interestrate",
    [
        pytest.param(
            [2020, 2025, 2030, 2035, 2040, 2050, 2060, 2070],
            0.05,
            id="5year_to_10year_5pct_fixcost",
        ),
    ],
)
def test_price_spike_with_fix_cost(test_mp, years, interestrate):
    """Test using fix_cost instead of inv_cost to avoid period-based price spikes.
    
    This test uses the precalculated annualized cost as fix_cost and sets
    inv_cost to a small epsilon value to see if this eliminates price spikes.
    """
    
    scen = build_scenario(test_mp, years, interestrate, use_fix_cost=True)
    scen.solve(quiet=True)

    # Note: years are the original model years passed to the test
    model_years = years

    # Print results table and get price dictionary
    price_dict = print_scenario_results(scen, model_years, interestrate)

    # Check for price spikes
    check_price_spikes(price_dict, threshold=1.10)

    return scen


@pytest.mark.parametrize(
    "years,interestrate",
    [
        pytest.param(
            [2020, 2025, 2030, 2035, 2040, 2050, 2060, 2070],
            0.05,
            id="5year_to_10year_5pct",
        ),
        pytest.param(
            [2020, 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060, 2065, 2070],
            0.05,
            id="all_5year_5pct",
        ),
        pytest.param(
            [2020, 2025, 2030, 2035, 2040, 2050, 2060, 2070],
            0.00,
            id="5year_to_10year_0pct",
        ),
    ],
)
def test_price_spike_with_historical_capacity(test_mp, years, interestrate):
    """Test with historical_new_capacity=1000 to force new_cap=0 for all periods.
    This will fail, for all period structures and at the year the tl causes reinvestment
    per the closest year to discretization."""
    scen = build_scenario(
        test_mp,
        years,
        interestrate,
        historical_new_capacity=1000,
    )
    scen.solve(quiet=True)

    # Note: years are the original model years passed to the test
    model_years = years

    # Print results table and get price dictionary
    price_dict = print_scenario_results(scen, model_years, interestrate)

    # Check for price spikes
    check_price_spikes(price_dict, threshold=1.10)

    return scen


@pytest.mark.parametrize(
    "years,interestrate",
    [
        pytest.param(
            [2020, 2025, 2030, 2035, 2040, 2050, 2060, 2070],
            0.05,
            id="5year_to_10year_5pct",
        ),
        pytest.param(
            [2020, 2025, 2030, 2035, 2040, 2050, 2060, 2070],
            0.1,
            id="5year_to_10year_10pct",
        ),
    ],
)
def test_price_spike_with_short_lifetime(test_mp, years, interestrate):
    """Test 5-to-10 year periods with technical_lifetime=1.
    This will pass."""
    scen = build_scenario(test_mp, years, interestrate, technical_lifetime=1)
    scen.solve(quiet=True)

    # Note: years are the original model years passed to the test
    model_years = years

    # Print results table and get price dictionary
    price_dict = print_scenario_results(scen, model_years, interestrate)

    # Check for price spikes
    check_price_spikes(price_dict, threshold=1.10)

    return scen
