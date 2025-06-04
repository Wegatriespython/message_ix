"""
Build a complete Austria base scenario following the tutorial exactly.

This script replicates the Austria tutorial notebook programmatically
to create a fully working base scenario that can be solved.
"""

import ixmp as ix
import message_ix
import pandas as pd
from message_ix import make_df


def build_austria_base_scenario(mp: ix.Platform) -> message_ix.Scenario:
    """
    Build complete Austria base scenario following tutorial structure.
    
    Returns
    -------
    scenario : message_ix.Scenario
        Complete, committed Austria scenario ready for solving
    """
    
    print("Building Austria base scenario...")
    
    # Model setup
    model = "Austrian energy model"
    scen = "baseline"
    annot = "developing a stylized energy system model for illustration and testing"
    
    scenario = message_ix.Scenario(mp, model, scen, version="new", annotation=annot)
    
    # === Time and Spatial Detail ===
    horizon = list(range(2010, 2041, 10))
    scenario.add_horizon(year=horizon)
    
    country = "Austria"
    scenario.add_spatial_sets({"country": country})
    
    # === Model Structure ===
    scenario.add_set("commodity", ["electricity", "light", "other_electricity"])
    scenario.add_set("level", ["secondary", "final", "useful"])
    scenario.add_set("mode", "standard")
    
    # === Technologies ===
    plants = [
        "coal_ppl", "gas_ppl", "oil_ppl", "bio_ppl", 
        "hydro_ppl", "wind_ppl", "solar_pv_ppl"
    ]
    secondary_energy_techs = plants + ["import"]
    final_energy_techs = ["electricity_grid"]
    lights = ["bulb", "cfl"]
    useful_energy_techs = lights + ["appliances"]
    
    technologies = secondary_energy_techs + final_energy_techs + useful_energy_techs
    scenario.add_set("technology", technologies)
    
    # === Economic Parameters ===
    scenario.add_par("interestrate", horizon, value=0.05, unit="-")
    
    # === Demand ===
    gdp = pd.Series([1.0, 1.21631, 1.4108, 1.63746], index=horizon)
    beta = 0.7
    demand = gdp**beta
    
    # Other electricity demand
    demand_per_year = 55209.0 / 8760  # from IEA statistics
    elec_demand = pd.DataFrame({
        "node": country,
        "commodity": "other_electricity", 
        "level": "useful",
        "year": horizon,
        "time": "year",
        "value": demand_per_year * demand,
        "unit": "GWa",
    })
    scenario.add_par("demand", elec_demand)
    
    # Light demand
    demand_per_year = 6134.0 / 8760  # from IEA statistics
    light_demand = pd.DataFrame({
        "node": country,
        "commodity": "light",
        "level": "useful", 
        "year": horizon,
        "time": "year",
        "value": demand_per_year * demand,
        "unit": "GWa",
    })
    scenario.add_par("demand", light_demand)
    
    # === Engineering Parameters ===
    year_df = scenario.vintage_and_active_years()
    vintage_years, act_years = year_df["year_vtg"], year_df["year_act"]
    
    # Input parameters
    base_input = {
        "node_loc": country,
        "year_vtg": vintage_years,
        "year_act": act_years,
        "mode": "standard",
        "node_origin": country,
        "commodity": "electricity",
        "time": "year",
        "time_origin": "year",
    }
    
    # Electricity grid input
    grid = pd.DataFrame(dict(
        technology="electricity_grid",
        level="secondary",
        value=1.0,
        unit="-",
        **base_input,
    ))
    scenario.add_par("input", grid)
    
    # Bulb input
    bulb = pd.DataFrame(dict(
        technology="bulb", 
        level="final", 
        value=1.0, 
        unit="-", 
        **base_input
    ))
    scenario.add_par("input", bulb)
    
    # CFL input
    cfl = pd.DataFrame(dict(
        technology="cfl",
        level="final",
        value=0.3,  # More efficient
        unit="-",
        **base_input,
    ))
    scenario.add_par("input", cfl)
    
    # Appliances input
    app = pd.DataFrame(dict(
        technology="appliances", 
        level="final", 
        value=1.0, 
        unit="-", 
        **base_input
    ))
    scenario.add_par("input", app)
    
    # === Output Parameters ===
    base_output = {
        "node_loc": country,
        "year_vtg": vintage_years,
        "year_act": act_years,
        "mode": "standard",
        "node_dest": country,
        "time": "year",
        "time_dest": "year",
        "unit": "-",
    }
    
    # Import output
    imports = make_df(base_output,
        technology="import",
        commodity="electricity",
        level="secondary",
        value=1.0,
    )
    scenario.add_par("output", imports)
    
    # Grid output
    grid_out = make_df(base_output,
        technology="electricity_grid",
        commodity="electricity",
        level="final",
        value=0.873,
    )
    scenario.add_par("output", grid_out)
    
    # Light technology outputs
    bulb_out = make_df(base_output, 
        technology="bulb", 
        commodity="light", 
        level="useful", 
        value=1.0
    )
    scenario.add_par("output", bulb_out)
    
    cfl_out = make_df(base_output, 
        technology="cfl", 
        commodity="light", 
        level="useful", 
        value=1.0
    )
    scenario.add_par("output", cfl_out)
    
    # Appliances output
    app_out = make_df(base_output,
        technology="appliances",
        commodity="other_electricity",
        level="useful",
        value=1.0,
    )
    scenario.add_par("output", app_out)
    
    # Power plant outputs
    for plant in plants:
        plant_out = make_df(base_output,
            technology=plant,
            commodity="electricity",
            level="secondary" if plant != "solar_pv_ppl" else "final",
            value=1.0,
        )
        scenario.add_par("output", plant_out)
    
    # === Technical Lifetime ===
    base_technical_lifetime = {
        "node_loc": country,
        "year_vtg": horizon,
        "unit": "y",
    }
    
    lifetimes = {
        "coal_ppl": 40,
        "gas_ppl": 30,
        "oil_ppl": 30,
        "bio_ppl": 30,
        "hydro_ppl": 60,
        "wind_ppl": 20,
        "solar_pv_ppl": 20,
        "bulb": 1,
        "cfl": 10,
    }
    
    for tec, val in lifetimes.items():
        df = make_df(base_technical_lifetime, technology=tec, value=val)
        scenario.add_par("technical_lifetime", df)
    
    # === Capacity Factor ===
    base_capacity_factor = {
        "node_loc": country,
        "year_vtg": vintage_years,
        "year_act": act_years,
        "time": "year",
        "unit": "-",
    }
    
    capacity_factor = {
        "coal_ppl": 0.85,
        "gas_ppl": 0.75,
        "oil_ppl": 0.75,
        "bio_ppl": 0.75,
        "hydro_ppl": 0.5,
        "wind_ppl": 0.2,
        "solar_pv_ppl": 0.15,
        "bulb": 0.1,
        "cfl": 0.1,
    }
    
    for tec, val in capacity_factor.items():
        df = make_df(base_capacity_factor, technology=tec, value=val)
        scenario.add_par("capacity_factor", df)
    
    # === Investment Costs ===
    base_inv_cost = {
        "node_loc": country,
        "year_vtg": horizon,
        "unit": "USD/kW",
    }
    
    # Add unit
    mp.add_unit("USD/kW")
    
    costs = {
        "coal_ppl": 1500,
        "gas_ppl": 870,
        "oil_ppl": 950,
        "hydro_ppl": 3000,
        "bio_ppl": 1600,
        "wind_ppl": 1100,
        "solar_pv_ppl": 4000,
        "bulb": 5,
        "cfl": 900,
    }
    
    for tec, val in costs.items():
        df = make_df(base_inv_cost, technology=tec, value=val)
        scenario.add_par("inv_cost", df)
    
    # === Fixed Costs ===
    base_fix_cost = {
        "node_loc": country,
        "year_vtg": vintage_years,
        "year_act": act_years,
        "unit": "USD/kWa",
    }
    
    # Add unit
    mp.add_unit("USD/kWa")
    
    fix_costs = {
        "coal_ppl": 40,
        "gas_ppl": 25,
        "oil_ppl": 25,
        "hydro_ppl": 60,
        "bio_ppl": 30,
        "wind_ppl": 40,
        "solar_pv_ppl": 25,
    }
    
    for tec, val in fix_costs.items():
        df = make_df(base_fix_cost, technology=tec, value=val)
        scenario.add_par("fix_cost", df)
    
    # === Variable Costs ===
    base_var_cost = {
        "node_loc": country,
        "year_vtg": vintage_years,
        "year_act": act_years,
        "mode": "standard",
        "time": "year",
        "unit": "USD/kWa",
    }
    
    var_costs = {
        "coal_ppl": 24.4,
        "gas_ppl": 42.4,
        "oil_ppl": 77.8,
        "bio_ppl": 48.2,
        "electricity_grid": 47.8,
    }
    
    for tec, val in var_costs.items():
        df = make_df(base_var_cost, technology=tec, value=val * 8760.0 / 1e3)
        scenario.add_par("var_cost", df)
    
    # === Growth Activity ===
    base_growth = {
        "node_loc": country,
        "year_act": horizon[1:],
        "value": 0.05,
        "time": "year",
        "unit": "%",
    }
    
    growth_technologies = [
        "coal_ppl", "gas_ppl", "oil_ppl", "bio_ppl",
        "hydro_ppl", "wind_ppl", "solar_pv_ppl",
        "cfl", "bulb",
    ]
    
    for tec in growth_technologies:
        df = make_df(base_growth, technology=tec)
        scenario.add_par("growth_activity_up", df)
    
    # === Initial Activity ===
    base_initial = {
        "node_loc": country,
        "year_act": horizon[1:],
        "time": "year",
        "unit": "%",
    }
    
    for tec in lights:
        df = make_df(base_initial,
            technology=tec,
            value=0.01 * light_demand["value"].loc[horizon[1:]],
        )
        scenario.add_par("initial_activity_up", df)
    
    # === Activity Bounds (Calibration) ===
    base_activity = {
        "node_loc": country,
        "year_act": [2010],
        "mode": "standard",
        "time": "year",
        "unit": "GWa",
    }
    
    activity = {
        "coal_ppl": 7184,
        "gas_ppl": 14346,
        "oil_ppl": 1275,
        "hydro_ppl": 38406,
        "bio_ppl": 4554,
        "wind_ppl": 2064,
        "solar_pv_ppl": 89,
        "import": 2340,
        "cfl": 0,
    }
    
    for tec, val in activity.items():
        df = make_df(base_activity, technology=tec, value=val / 8760.0)
        scenario.add_par("bound_activity_up", df)
        scenario.add_par("bound_activity_lo", df)
    
    # === Capacity Bounds ===
    base_capacity = {
        "node_loc": country,
        "year_vtg": [2010],
        "unit": "GW",
    }
    
    cf = pd.Series(capacity_factor)
    act = pd.Series(activity)
    capacity = (act / 8760 / cf).dropna().to_dict()
    
    for tec, val in capacity.items():
        df = make_df(base_capacity, technology=tec, value=val)
        scenario.add_par("bound_new_capacity_up", df)
    
    # === Future Activity Bounds ===
    base_activity_future = {
        "node_loc": country,
        "year_act": horizon[1:],
        "mode": "standard",
        "time": "year",
        "unit": "GWa",
    }
    
    keep_activity = {
        "hydro_ppl": 38406,
        "bio_ppl": 4554,
        "import": 2340,
    }
    
    for tec, val in keep_activity.items():
        df = make_df(base_activity_future, technology=tec, value=val / 8760.0)
        scenario.add_par("bound_activity_up", df)
    
    # === Emissions ===
    scenario.add_set("emission", "CO2")
    scenario.add_cat("emission", "GHGs", "CO2")
    
    base_emissions = {
        "node_loc": country,
        "year_vtg": vintage_years,
        "year_act": act_years,
        "mode": "standard",
        "unit": "tCO2/kWa",
    }
    
    # Add units
    mp.add_unit("tCO2/kWa")
    mp.add_unit("MtCO2")
    
    emissions = {
        "coal_ppl": ("CO2", 0.854),
        "gas_ppl": ("CO2", 0.339),
        "oil_ppl": ("CO2", 0.57),
    }
    
    for tec, (species, val) in emissions.items():
        df = make_df(base_emissions, 
            technology=tec, 
            emission=species, 
            value=val * 8760.0 / 1000
        )
        scenario.add_par("emission_factor", df)
    
    # === Commit and Set Default ===
    comment = "Austria base scenario - complete tutorial replication"
    scenario.commit(comment)
    scenario.set_as_default()
    
    print("Austria base scenario built successfully!")
    return scenario


def test_austria_base():
    """Test the Austria base scenario by building and solving it."""
    
    print("=== Testing Austria Base Scenario ===")
    
    mp = ix.Platform(name="local")
    
    try:
        # Build scenario
        scenario = build_austria_base_scenario(mp)
        
        print(f"Scenario: {scenario.model} | {scenario.scenario}")
        print(f"Technologies: {len(scenario.set('technology'))}")
        print(f"Commodities: {len(scenario.set('commodity'))}")
        
        # Try to solve
        print("\nSolving scenario...")
        scenario.solve()
        
        # Check objective
        obj_value = scenario.var("OBJ")["lvl"]
        print(f"Objective value: {obj_value}")
        
        print("✅ Austria base scenario solved successfully!")
        return scenario
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        mp.close_db()


if __name__ == "__main__":
    test_austria_base()