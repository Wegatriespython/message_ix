"""
Phase 1: Power Plant Cooling Integration Script

This script demonstrates the integration of power plant cooling technologies
from the MESSAGEix water module with the Austria energy system tutorial.

Phase 1 Focus:
- Add cooling technology variants to existing power plants
- Implement basic water supply constraints
- Demonstrate cooling efficiency vs. water use trade-offs
"""

import logging
import sys
from pathlib import Path

# Add water_austria to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import ixmp as ix
import message_ix
from water_austria import build_water_austria_scenario

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def create_austria_base_scenario(mp: ix.Platform) -> message_ix.Scenario:
    """
    Create a base Austria energy scenario following the tutorial structure.
    
    This recreates the Austria tutorial scenario programmatically as a
    starting point for water integration.
    """
    
    log.info("Creating base Austria energy scenario")
    
    model = "Austrian energy model"
    scen = "baseline"
    annot = "Base Austria scenario for water integration"
    
    scenario = message_ix.Scenario(mp, model, scen, version="new", annotation=annot)
    
    # Time and spatial setup
    horizon = list(range(2010, 2041, 10))
    scenario.add_horizon(year=horizon)
    scenario.add_spatial_sets({"country": "Austria"})
    
    # Basic structure
    scenario.add_set("commodity", ["electricity", "light", "other_electricity"])
    scenario.add_set("level", ["secondary", "final", "useful"])
    scenario.add_set("mode", "standard")
    
    # Technologies  
    plants = [
        "coal_ppl", "gas_ppl", "oil_ppl", "bio_ppl", 
        "hydro_ppl", "wind_ppl", "solar_pv_ppl"
    ]
    scenario.add_set("technology", plants + ["import", "electricity_grid", "bulb", "cfl", "appliances"])
    
    # Economic parameters
    scenario.add_par("interestrate", horizon, value=0.05, unit="-")
    
    log.info("Base Austria scenario created")
    return scenario


def demonstrate_cooling_integration():
    """
    Main demonstration of Phase 1 cooling technology integration.
    """
    
    log.info("=== Phase 1: Cooling Technology Integration Demo ===")
    
    # Launch platform
    mp = ix.Platform(name="local")
    
    try:
        # Create base Austria scenario
        base_scenario = create_austria_base_scenario(mp)
        base_scenario.commit("Base Austria scenario for water integration")
        
        # Build water-enhanced scenario (Phase 1: cooling)
        log.info("Building water-enhanced Austria scenario...")
        water_scenario = build_water_austria_scenario(
            base_scenario, 
            phase="cooling",
            fictional_enhancements=True
        )
        
        # Commit water scenario
        water_scenario.commit("Phase 1: Austria with cooling technologies")
        
        # Demonstrate the integration
        log.info("=== Integration Results ===")
        
        # Show added technologies
        all_techs = water_scenario.set("technology")
        cooling_techs = [t for t in all_techs if "__" in t]
        log.info(f"Added {len(cooling_techs)} cooling technology variants:")
        for tech in cooling_techs:
            log.info(f"  - {tech}")
        
        # Show added commodities
        water_commodities = [c for c in water_scenario.set("commodity") 
                           if c not in ["electricity", "light", "other_electricity"]]
        log.info(f"Added water commodities: {water_commodities}")
        
        # Show added levels
        water_levels = [l for l in water_scenario.set("level")
                       if l not in ["secondary", "final", "useful"]]
        log.info(f"Added water levels: {water_levels}")
        
        log.info("Phase 1 integration completed successfully!")
        
        return water_scenario
        
    except Exception as e:
        log.error(f"Error during integration: {e}")
        raise
    finally:
        mp.close_db()


def analyze_cooling_tradeoffs(scenario: message_ix.Scenario):
    """
    Analyze cooling technology trade-offs in the water-enhanced scenario.
    
    This function demonstrates how to explore water-energy trade-offs
    that become visible with the cooling technology integration.
    """
    
    log.info("=== Analyzing Cooling Technology Trade-offs ===")
    
    # This would analyze:
    # - Water consumption vs. efficiency for different cooling types
    # - Impact of water availability constraints on power plant operation  
    # - Optimal cooling technology mix under different scenarios
    
    log.info("Trade-off analysis would be implemented here")


if __name__ == "__main__":
    """
    Run Phase 1 cooling integration demonstration.
    """
    
    print("\n" + "="*60)
    print("Water-Austria Integration: Phase 1 Demonstration")
    print("="*60)
    
    try:
        water_scenario = demonstrate_cooling_integration()
        analyze_cooling_tradeoffs(water_scenario)
        
        print("\n" + "="*60)
        print("Phase 1 demonstration completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)