"""
Test using water module's build.main() function directly.

This mimics how the water module actually gets called from CLI.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import ixmp as ix
import message_ix
from message_ix_models import Context

# Import water module components
from water.utils import read_config
from water.build import main as water_build
from water_austria.scripts.build_austria_base import build_austria_base_scenario


def setup_water_context_for_austria(scenario: message_ix.Scenario) -> Context:
    """
    Setup a Context that mimics water CLI initialization for Austria.
    """
    # Create context
    context = Context()
    
    # Load water configuration
    read_config(context)
    
    # Set scenario info (this is how CLI does it)
    context.scenario_info = {
        "model": scenario.model,
        "scenario": scenario.scenario,
        "version": scenario.version
    }
    context.output_model = scenario.model
    context.output_scenario = scenario.scenario
    
    # Set regions and type
    context.regions = "R11"  # Use R11 for global model compatibility
    context.type_reg = "global"
    
    # Set water module mode
    context.nexus_set = "cooling"  # Only cooling technologies
    
    # Climate and reliability settings
    context.RCP = "no_climate"  # No climate impacts for simple test
    context.REL = "low"
    context.ssp = "SSP2"
    
    # Time settings
    context.time = ["year"]  # Annual time steps
    
    # Store the scenario in context (water module expects this)
    context._scenario = scenario
    
    # Override get_scenario to return our scenario
    def get_scenario_override():
        return context._scenario
    context.get_scenario = get_scenario_override
    
    return context


def test_water_build():
    """Test using water module's main build function."""
    
    print("=== Testing Water Module Build Function ===\n")
    
    mp = ix.Platform(name="local")
    
    try:
        # 1. Build Austria base scenario
        print("1. Building Austria base scenario...")
        base_scenario = build_austria_base_scenario(mp)
        
        # 2. Clone for water
        print("\n2. Cloning for water enhancement...")
        water_scenario = base_scenario.clone(
            scenario="water_build_test",
            annotation="Testing water module build function"
        )
        water_scenario.check_out()
        
        # 3. Setup context
        print("\n3. Setting up water context...")
        context = setup_water_context_for_austria(water_scenario)
        
        print(f"   Context regions: {context.regions}")
        print(f"   Context type: {context.type_reg}")
        print(f"   Context mode: {context.nexus_set}")
        print(f"   Context SSP: {context.ssp}")
        
        # 4. Run water build
        print("\n4. Running water module build...")
        water_build(context, water_scenario)
        
        # 5. Check results
        print("\n5. Checking results...")
        
        # Technologies
        all_techs = list(water_scenario.set('technology'))
        cooling_techs = [t for t in all_techs if '__' in t]
        print(f"   Total technologies: {len(all_techs)}")
        print(f"   Cooling technologies: {len(cooling_techs)}")
        
        if cooling_techs:
            print("\n   Sample cooling technologies:")
            for tech in cooling_techs[:5]:
                print(f"     - {tech}")
        
        # Commodities
        commodities = list(water_scenario.set('commodity'))
        water_commodities = [c for c in commodities if any(
            w in c for w in ['water', 'fresh', 'saline', 'ot_', 'cl_', 'air']
        )]
        print(f"\n   Water-related commodities: {len(water_commodities)}")
        for comm in water_commodities:
            print(f"     - {comm}")
        
        # Check if we have cooling data
        try:
            input_data = water_scenario.par('input', 
                filters={'technology': cooling_techs[0] if cooling_techs else 'coal_ppl__ot_fresh'}
            )
            print(f"\n   Cooling technology has input data: {'Yes' if not input_data.empty else 'No'}")
        except:
            print("\n   Could not check cooling technology data")
        
        print("\n✅ Water module build completed!")
        return water_scenario
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        mp.close_db()


if __name__ == "__main__":
    test_water_build()