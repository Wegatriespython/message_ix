"""Tests for the annual-aggregated dynamic activity constraint.

By default the dynamic activity-growth constraints
(``ACTIVITY_CONSTRAINT_UP`` / ``ACTIVITY_CONSTRAINT_LO`` and their soft
companions) bind independently at every sub-annual time slice. Technologies
listed in the set ``dynamic_activity_aggregate(node, tec)`` are instead
governed by the ``_AGG`` variants, which generate at the parent ``time`` level
(where the growth parameters are defined) and bind on activity summed over the
child time slices via ``map_time``.

The two forms are mutually exclusive per technology: the per-slice equations
carry a ``NOT dynamic_activity_aggregate`` condition, so a flagged technology is
covered by exactly one. Technologies absent from the set keep byte-identical
per-slice behaviour, so scenarios that never populate the set are unaffected --
the per-slice variants below reproduce the unmodified-model solution.
"""

import pandas as pd
import pytest
from ixmp import Platform

from message_ix import Scenario, make_df

pytestmark = pytest.mark.ixmp4_209

NODE = "node"
HIST_YEAR = 2015
YEAR = 2020
MODE = "mode"
TIMES = ["h1", "h2"]
DURATION = 0.5  # equal halves of the year

CHEAP_VAR_COST = 10.0
EXPENSIVE_VAR_COST = 50.0

# Upper-constraint scenario: peaked demand, uniform historical activity.
PEAK_DEMAND = 5.0  # h1 demand
OFF_DEMAND = 1.0  # h2 demand
HIST_PER_SLICE = 2.0  # historical_activity of the dynamic tech in each slice
# Per-slice cap => cheap_ppl <= 2 at h1 and <= 2 at h2 => total 3 (h2 demand 1).
# Annual cap => cheap_ppl total <= 4, free to ride the h1 peak above 2.

# Lower-constraint scenario: demand only at h1, legacy tech with a decline floor.
LO_DEMAND = 3.0
LO_HIST_PER_SLICE = 2.0  # legacy historical activity each slice => annual floor 4


def _act_at(act: pd.DataFrame, technology: str, time: str) -> float:
    rows = act[(act["technology"] == technology) & (act["time"] == time)]
    return float(rows["lvl"].sum())


def _act_total(act: pd.DataFrame, technology: str) -> float:
    return float(act[act["technology"] == technology]["lvl"].sum())


def _build_baseline(
    mp: Platform,
    scenario_name: str,
    *,
    demand_by_slice: dict[str, float],
    technologies: tuple[tuple[str, float], ...],
) -> Scenario:
    """Two-period RES (one historical, one model year) over two time slices."""
    scen = Scenario(
        mp, model="test_activity_aggregate", scenario=scenario_name, version="new"
    )
    scen.add_horizon(year=[HIST_YEAR, YEAR], firstmodelyear=YEAR)
    scen.add_spatial_sets({"country": NODE})

    with scen.transact("structure"):
        scen.add_set("mode", MODE)
        scen.add_set("level", "useful")
        scen.add_set("commodity", "electr")
        scen.add_set("technology", [t for t, _ in technologies])
        scen.add_set("lvl_temporal", "subannual")
        for t in TIMES:
            scen.add_set("time", t)
            scen.add_set("map_temporal_hierarchy", ["subannual", t, "year"])

    with scen.transact("temporal structure and demand"):
        scen.remove_par("duration_time", scen.par("duration_time"))
        scen.add_par(
            "duration_time",
            make_df(
                "duration_time",
                time=TIMES + ["year"],
                value=[DURATION] * len(TIMES) + [1.0],
                unit="%",
            ),
        )
        scen.add_par(
            "demand",
            make_df(
                "demand",
                node=NODE,
                commodity="electr",
                level="useful",
                year=YEAR,
                time=list(demand_by_slice),
                value=list(demand_by_slice.values()),
                unit="GWa",
            ),
        )

    common = dict(node_loc=NODE, year_vtg=YEAR, year_act=YEAR, time=TIMES)
    with scen.transact("technology data"):
        for tech, var_cost in technologies:
            scen.add_par(
                "output",
                make_df(
                    "output",
                    **common,
                    technology=tech,
                    mode=MODE,
                    commodity="electr",
                    level="useful",
                    node_dest=NODE,
                    time_dest=TIMES,
                    value=1.0,
                    unit="GWa",
                ),
            )
            scen.add_par(
                "var_cost",
                make_df(
                    "var_cost",
                    **common,
                    technology=tech,
                    mode=MODE,
                    value=var_cost,
                    unit="USD/GWa",
                ),
            )
            scen.add_par(
                "capacity_factor",
                make_df(
                    "capacity_factor", **common, technology=tech, value=1.0, unit="-"
                ),
            )

    return scen


def _add_historical_activity(scen: Scenario, technology: str, per_slice: float) -> None:
    with scen.transact("historical activity"):
        scen.add_par(
            "historical_activity",
            make_df(
                "historical_activity",
                node_loc=NODE,
                technology=technology,
                year_act=HIST_YEAR,
                mode=MODE,
                time=TIMES,
                value=per_slice,
                unit="GWa",
            ),
        )


def _add_growth(
    scen: Scenario, par_name: str, technology: str, *, aggregate: bool
) -> None:
    """Add a zero-rate dynamic growth parameter and (optionally) the flag.

    With ``aggregate=False`` the parameter is defined at each time slice, so
    ``is_dynamic_activity_*`` is composed per slice and the per-slice equation
    binds. With ``aggregate=True`` it is defined at the parent ``"year"`` slice
    and the technology is added to ``dynamic_activity_aggregate``, so the
    ``_AGG`` equation binds on the annual-summed activity instead.

    The growth rate is 0, so the bound reduces to the previous-period anchor
    (here ``historical_activity``) and the per-slice vs annual difference is
    exactly the time-slice aggregation.
    """
    times = ["year"] if aggregate else TIMES
    with scen.transact("dynamic growth bound"):
        scen.add_par(
            par_name,
            make_df(
                par_name,
                node_loc=NODE,
                technology=technology,
                year_act=YEAR,
                time=times,
                value=0.0,
                unit="-",
            ),
        )
        if aggregate:
            scen.add_set("dynamic_activity_aggregate", [NODE, technology])


def _remove_technology_time(scen: Scenario, technology: str, time: str) -> None:
    with scen.transact("remove technology time slice"):
        for par_name in ["output", "var_cost", "capacity_factor"]:
            rows = scen.par(par_name, filters={"technology": technology, "time": time})
            if not rows.empty:
                scen.remove_par(par_name, rows)


def _add_soft_activity_up(
    scen: Scenario, technology: str, *, soft_rate: float, abs_cost: float
) -> None:
    common = dict(node_loc=NODE, technology=technology, year_act=YEAR, time="year")
    with scen.transact("soft activity upper bound"):
        scen.add_par(
            "soft_activity_up",
            make_df("soft_activity_up", **common, value=soft_rate, unit="-"),
        )
        scen.add_par(
            "abs_cost_activity_soft_up",
            make_df(
                "abs_cost_activity_soft_up",
                **common,
                value=abs_cost,
                unit="USD/GWa",
            ),
        )


def test_activity_constraint_up_aggregate_vs_per_slice(test_mp: Platform) -> None:
    """Upper growth constraint: per-slice (default) vs annual-aggregated.

    Demand is peaked (h1=5, h2=1); ``cheap_ppl`` carries a growth-zero ceiling
    anchored on uniform historical activity (2 per slice).

    * Unflagged (per slice): ``cheap_ppl`` is held to 2 at the h1 peak and
      ``expensive_ppl`` covers the remaining 3. This is the unmodified model;
      with ``dynamic_activity_aggregate`` empty the per-slice equations are
      byte-identical to the released model.
    * Flagged (aggregated): the ceiling becomes ``sum_h cheap_ppl <= 4``, so
      ``cheap_ppl`` rides the h1 peak above 2 while the annual ramp is retained,
      and ``expensive_ppl`` only covers the annual shortfall (2).

    The aggregated objective is strictly lower, proving the aggregation relaxes
    the per-season artefact rather than the annual ramp.
    """
    techs = (("cheap_ppl", CHEAP_VAR_COST), ("expensive_ppl", EXPENSIVE_VAR_COST))
    demand = {"h1": PEAK_DEMAND, "h2": OFF_DEMAND}

    per_slice = _build_baseline(
        test_mp, "up_per_slice", demand_by_slice=demand, technologies=techs
    )
    _add_historical_activity(per_slice, "cheap_ppl", HIST_PER_SLICE)
    _add_growth(per_slice, "growth_activity_up", "cheap_ppl", aggregate=False)
    per_slice.solve(quiet=True)

    aggregate = _build_baseline(
        test_mp, "up_aggregate", demand_by_slice=demand, technologies=techs
    )
    _add_historical_activity(aggregate, "cheap_ppl", HIST_PER_SLICE)
    _add_growth(aggregate, "growth_activity_up", "cheap_ppl", aggregate=True)
    aggregate.solve(quiet=True)

    # Per-slice: the cap binds independently at each slice.
    act_ps = per_slice.var("ACT")
    assert _act_at(act_ps, "cheap_ppl", "h1") == pytest.approx(HIST_PER_SLICE, rel=1e-3)
    assert _act_at(act_ps, "expensive_ppl", "h1") == pytest.approx(
        PEAK_DEMAND - HIST_PER_SLICE, rel=1e-3
    )
    assert _act_at(act_ps, "cheap_ppl", "h2") == pytest.approx(OFF_DEMAND, rel=1e-3)
    assert _act_total(act_ps, "cheap_ppl") == pytest.approx(
        HIST_PER_SLICE + OFF_DEMAND, rel=1e-3
    )

    # Aggregated: the cap binds on the annual sum; h1 exceeds the per-slice cap.
    act_agg = aggregate.var("ACT")
    annual_cap = len(TIMES) * HIST_PER_SLICE  # 4
    total_demand = PEAK_DEMAND + OFF_DEMAND
    assert _act_total(act_agg, "cheap_ppl") == pytest.approx(annual_cap, rel=1e-3)
    assert _act_at(act_agg, "cheap_ppl", "h1") > HIST_PER_SLICE + 1e-3
    assert _act_total(act_agg, "expensive_ppl") == pytest.approx(
        total_demand - annual_cap, rel=1e-3
    )

    # Same data, same objective scaling: the aggregated cap is the looser one.
    assert float(aggregate.var("OBJ")["lvl"]) < float(per_slice.var("OBJ")["lvl"])


def test_activity_constraint_up_aggregate_soft_cost(test_mp: Platform) -> None:
    techs = (("cheap_ppl", CHEAP_VAR_COST),)
    demand = {"h1": PEAK_DEMAND, "h2": OFF_DEMAND}
    soft_rate = 1.0

    free_relaxation = _build_baseline(
        test_mp,
        "up_aggregate_soft_free",
        demand_by_slice=demand,
        technologies=techs,
    )
    _add_historical_activity(free_relaxation, "cheap_ppl", HIST_PER_SLICE)
    _add_growth(free_relaxation, "growth_activity_up", "cheap_ppl", aggregate=True)
    _add_soft_activity_up(
        free_relaxation, "cheap_ppl", soft_rate=soft_rate, abs_cost=0.0
    )
    free_relaxation.solve(quiet=True, var_list=["ACT_UP"])

    priced_relaxation = _build_baseline(
        test_mp,
        "up_aggregate_soft_priced",
        demand_by_slice=demand,
        technologies=techs,
    )
    _add_historical_activity(priced_relaxation, "cheap_ppl", HIST_PER_SLICE)
    _add_growth(priced_relaxation, "growth_activity_up", "cheap_ppl", aggregate=True)
    _add_soft_activity_up(
        priced_relaxation, "cheap_ppl", soft_rate=soft_rate, abs_cost=1000.0
    )
    priced_relaxation.solve(quiet=True, var_list=["ACT_UP"])

    annual_cap = len(TIMES) * HIST_PER_SLICE
    required_relaxation = (PEAK_DEMAND + OFF_DEMAND - annual_cap) / (
        (1 + soft_rate) ** (YEAR - HIST_YEAR) - 1
    )
    assert _act_total(priced_relaxation.var("ACT_UP"), "cheap_ppl") == pytest.approx(
        required_relaxation, rel=1e-3
    )
    assert float(priced_relaxation.var("OBJ")["lvl"]) > float(
        free_relaxation.var("OBJ")["lvl"]
    )


def test_activity_constraint_up_aggregate_slack_cost(test_mp: Platform) -> None:
    techs = (("cheap_ppl", CHEAP_VAR_COST),)
    demand = {"h1": PEAK_DEMAND, "h2": OFF_DEMAND}
    scen = _build_baseline(
        test_mp,
        "up_aggregate_slack_priced",
        demand_by_slice=demand,
        technologies=techs,
    )
    _add_historical_activity(scen, "cheap_ppl", HIST_PER_SLICE)
    _add_growth(scen, "growth_activity_up", "cheap_ppl", aggregate=True)
    scen.solve(
        quiet=True,
        gams_args=['--SLACK_ACT_DYNAMIC_UP=""'],
        var_list=["SLACK_ACT_DYNAMIC_UP"],
    )

    annual_cap = len(TIMES) * HIST_PER_SLICE
    required_slack = PEAK_DEMAND + OFF_DEMAND - annual_cap
    assert _act_total(scen.var("SLACK_ACT_DYNAMIC_UP"), "cheap_ppl") == pytest.approx(
        required_slack, rel=1e-3
    )
    assert float(scen.var("OBJ")["lvl"]) > 1e8


def test_activity_constraint_up_aggregate_ignores_non_operating_history(
    test_mp: Platform,
) -> None:
    techs = (("cheap_ppl", CHEAP_VAR_COST), ("expensive_ppl", EXPENSIVE_VAR_COST))
    scen = _build_baseline(
        test_mp,
        "up_aggregate_operating_history",
        demand_by_slice={"h1": PEAK_DEMAND},
        technologies=techs,
    )
    _remove_technology_time(scen, "cheap_ppl", "h2")
    with scen.transact("historical activity"):
        scen.add_par(
            "historical_activity",
            make_df(
                "historical_activity",
                node_loc=NODE,
                technology="cheap_ppl",
                year_act=HIST_YEAR,
                mode=MODE,
                time=TIMES,
                value=[HIST_PER_SLICE, 100.0],
                unit="GWa",
            ),
        )
    _add_growth(scen, "growth_activity_up", "cheap_ppl", aggregate=True)
    scen.solve(quiet=True)

    act = scen.var("ACT")
    assert _act_at(act, "cheap_ppl", "h1") == pytest.approx(HIST_PER_SLICE, rel=1e-3)
    assert _act_at(act, "expensive_ppl", "h1") == pytest.approx(
        PEAK_DEMAND - HIST_PER_SLICE, rel=1e-3
    )


def test_activity_constraint_lo_aggregate_vs_per_slice(test_mp: Platform) -> None:
    """Lower (decline) constraint: per-slice (default) vs annual-aggregated.

    Demand sits only at h1 (=3); ``legacy_ppl`` carries a growth-zero decline
    floor anchored on uniform historical activity (2 per slice, annual floor 4).

    * Unflagged (per slice): ``legacy_ppl`` is forced to 2 in *each* slice, so
      it runs 2 at h2 where there is no demand (overproduction) and ``cheap_ppl``
      tops up the h1 demand above the legacy floor.
    * Flagged (aggregated): only the annual sum (>= 4) is floored, so
      ``legacy_ppl`` covers the full h1 demand (3) and dumps the floor remainder
      (1) at h2, displacing ``cheap_ppl`` entirely.

    The aggregated objective is strictly lower.
    """
    techs = (("cheap_ppl", CHEAP_VAR_COST), ("legacy_ppl", EXPENSIVE_VAR_COST))
    demand = {"h1": LO_DEMAND}

    per_slice = _build_baseline(
        test_mp, "lo_per_slice", demand_by_slice=demand, technologies=techs
    )
    _add_historical_activity(per_slice, "legacy_ppl", LO_HIST_PER_SLICE)
    _add_growth(per_slice, "growth_activity_lo", "legacy_ppl", aggregate=False)
    per_slice.solve(quiet=True)

    aggregate = _build_baseline(
        test_mp, "lo_aggregate", demand_by_slice=demand, technologies=techs
    )
    _add_historical_activity(aggregate, "legacy_ppl", LO_HIST_PER_SLICE)
    _add_growth(aggregate, "growth_activity_lo", "legacy_ppl", aggregate=True)
    aggregate.solve(quiet=True)

    # Per-slice: the floor forces legacy to run in the demand-free h2 slice.
    act_ps = per_slice.var("ACT")
    assert _act_at(act_ps, "legacy_ppl", "h2") == pytest.approx(
        LO_HIST_PER_SLICE, rel=1e-3
    )
    assert _act_at(act_ps, "legacy_ppl", "h1") == pytest.approx(
        LO_HIST_PER_SLICE, rel=1e-3
    )
    assert _act_at(act_ps, "cheap_ppl", "h1") == pytest.approx(
        LO_DEMAND - LO_HIST_PER_SLICE, rel=1e-3
    )

    # Aggregated: only the annual sum is floored. legacy covers all h1 demand
    # itself, so cheap_ppl is displaced; the h2 slice is freed below the
    # per-slice floor (the exact h1/h2 split of the floored total is degenerate).
    act_agg = aggregate.var("ACT")
    annual_floor = len(TIMES) * LO_HIST_PER_SLICE  # 4
    assert _act_total(act_agg, "legacy_ppl") == pytest.approx(annual_floor, rel=1e-3)
    assert _act_at(act_agg, "legacy_ppl", "h2") < LO_HIST_PER_SLICE - 1e-3
    assert _act_total(act_agg, "cheap_ppl") == pytest.approx(0.0, abs=1e-6)

    assert float(aggregate.var("OBJ")["lvl"]) < float(per_slice.var("OBJ")["lvl"])
