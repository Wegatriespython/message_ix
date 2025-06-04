"""
Test direct import of water module functions for Austria.

This script tests using the actual water module functions with Austria,
creating a minimal Context object to make them work.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import ixmp as ix
import message_ix
import pandas as pd
from message_ix_models import Context, ScenarioInfo
from message_ix_models.model import build
from message_ix_models.util import add_par_data

# Import the actual water module functions
from water.build import get_spec
from water.data import cool_tech, non_cooling_tec
from water_austria.scripts.build_austria_base import build_austria_base_scenario


def create_minimal_water_context(scenario: message_ix.Scenario) -> Context:
    """
    Create a minimal Context object that works with water module functions.
    """
    # Create a basic Context
    context = Context()
    
    # Set scenario reference directly to avoid get_scenario() calls
    context._scenario_obj = scenario
    
    # Override get_scenario to return our scenario
    def get_scenario_override():
        return context._scenario_obj
    context.get_scenario = get_scenario_override
    
    # Set required attributes for water module
    context.regions = "R11"  # Pretend Austria is part of R11 for now
    context.type_reg = "global"  # So it doesn't look for country-specific data
    context.nexus_set = "cooling"  # Only cooling functions
    
    # Create scenario info
    info = ScenarioInfo(scenario)
    context["water build info"] = info
    
    # Add time info
    context.time = "year"  # Annual time resolution
    
    # Add some dummy regional mappings that water module expects
    context.all_nodes = pd.Series(["Austria"])  # Simplified node list
    
    # SSP scenario for cooling shares
    context.ssp = "SSP2"  # Default SSP2 scenario
    
    # RCP and REL for water availability (not used in cooling-only)
    context.RCP = "6p0"
    context.REL = "low"
    
    return context


def test_direct_water_import():
    """Test importing water cooling functions directly."""
    
    print("=== Testing Direct Water Module Import ===\n")
    
    mp = ix.Platform(name="local")
    
    try:
        # 1. Build Austria base scenario
        print("1. Building Austria base scenario...")
        base_scenario = build_austria_base_scenario(mp)
        
        # 2. Clone for water enhancement
        print("\n2. Cloning scenario for water enhancement...")
        water_scenario = base_scenario.clone(
            scenario="water_cooling_test",
            annotation="Testing direct water module import"
        )
        water_scenario.check_out()
        
        # 3. Create minimal context
        print("\n3. Creating minimal water context...")
        context = create_minimal_water_context(water_scenario)
        
        # 4. Get water module spec and apply structure
        print("\n4. Applying water module structure...")
        spec = get_spec(context)
        
        # Apply only the structural changes (sets, mappings)
        build.apply_spec(water_scenario, spec, dry_run=False)
        
        # 5. Add cooling technology data
        print("\n5. Adding cooling technology data...")
        
        # Get cooling data
        cooling_data = cool_tech(context)
        print(f"   cool_tech returned {len(cooling_data)} parameter types")
        
        # Add the data
        add_par_data(water_scenario, cooling_data, dry_run=False)
        
        # Get non-cooling water data
        non_cooling_data = non_cooling_tec(context)
        print(f"   non_cooling_tec returned {len(non_cooling_data)} parameter types")
        
        # Add the data
        add_par_data(water_scenario, non_cooling_data, dry_run=False)
        
        # 6. Commit and report
        print("\n6. Committing scenario...")
        water_scenario.commit("Added cooling technologies via direct import")
        
        # Check what was added
        print("\n=== Results ===")
        print(f"Technologies: {len(water_scenario.set('technology'))}")
        
        # Show cooling technologies
        all_techs = list(water_scenario.set('technology'))
        cooling_techs = [t for t in all_techs if '__' in t]
        print(f"Cooling variants: {len(cooling_techs)}")
        
        if cooling_techs:
            print("\nSample cooling technologies:")
            for tech in cooling_techs[:5]:
                print(f"  - {tech}")
                
        # Check for water commodities
        commodities = list(water_scenario.set('commodity'))
        water_commodities = [c for c in commodities if any(w in c for w in ['water', 'fresh', 'saline'])]
        print(f"\nWater commodities: {water_commodities}")
        
        print("\n✅ Direct import test completed!")
        return water_scenario
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        mp.close_db()


if __name__ == "__main__":
    test_direct_water_import()