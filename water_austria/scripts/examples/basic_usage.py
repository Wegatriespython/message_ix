"""
Basic usage example for water-Austria integration.

This script shows the simplest way to use the water_austria module
to enhance an existing Austria scenario with water technologies.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import ixmp as ix

from water_austria import build_water_austria_scenario
from water_austria.scripts.build_austria_base import build_austria_base_scenario


def basic_example():
    """Basic example of using water_austria module."""

    print("=== Basic Water-Austria Integration Example ===")

    # Launch platform
    mp = ix.Platform(name="local")

    try:
        # Build a complete Austria base scenario
        print("1. Building complete Austria base scenario...")
        base_scenario = build_austria_base_scenario(mp)

        print(f"   Base scenario: {len(base_scenario.set('technology'))} technologies")

        # Enhance with water technologies
        print("\n2. Adding water technologies...")
        water_scenario = build_water_austria_scenario(base_scenario)

        print(
            f"   Water scenario: {len(water_scenario.set('technology'))} technologies"
        )

        # Show what was added
        base_techs = set(base_scenario.set("technology"))
        water_techs = set(water_scenario.set("technology"))
        added_techs = water_techs - base_techs

        print(f"\n3. Added {len(added_techs)} new technologies:")
        for tech in sorted(added_techs)[:10]:  # Show first 10
            print(f"   - {tech}")
        if len(added_techs) > 10:
            print(f"   ... and {len(added_techs) - 10} more")

        # Check commodities
        base_comms = set(base_scenario.set("commodity"))
        water_comms = set(water_scenario.set("commodity"))
        added_comms = water_comms - base_comms

        print(f"\n4. Added {len(added_comms)} new commodities:")
        for comm in sorted(added_comms):
            print(f"   - {comm}")

        # Check levels
        base_levels = set(base_scenario.set("level"))
        water_levels = set(water_scenario.set("level"))
        added_levels = water_levels - base_levels

        print(f"\n5. Added {len(added_levels)} new levels:")
        for level in sorted(added_levels):
            print(f"   - {level}")

        # Commit the scenario
        print("\n6. Committing water scenario...")
        water_scenario.commit("Added cooling technologies to Austria")

        # Solve the scenario
        print("\n7. Solving water scenario...")
        water_scenario.solve()

        # Read solution and process results
        obj_value = water_scenario.var("OBJ")["lvl"]
        print(f"\n8. Objective value: {obj_value:.2f}")

        # Read activity of power plants
        plants = ['coal_ppl', 'gas_ppl', 'oil_ppl', 'bio_ppl', 'hydro_ppl', 'wind_ppl', 'solar_pv_ppl']
        activity = water_scenario.var('ACT', {'technology': plants})
        if not activity.empty:
            activity_pivot = activity.pivot_table(
                index='year_act', columns='technology', values='lvl', fill_value=0
            )
            print("\n9. Power plant activity (GWa):")
            print(activity_pivot)

        # Read cooling technology activity  
        cooling_techs = [tech for tech in water_scenario.set('technology') if '__' in tech]
        if cooling_techs:
            cooling_activity = water_scenario.var('ACT', {'technology': cooling_techs[:5]})
            if not cooling_activity.empty:
                cooling_pivot = cooling_activity.pivot_table(
                    index='year_act', columns='technology', values='lvl', fill_value=0
                )
                print("\n10. Sample cooling technology activity (GWa):")
                print(cooling_pivot)

        print("\n✅ Basic integration completed successfully!")
        return water_scenario

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return None
    finally:
        mp.close_db()


if __name__ == "__main__":
    basic_example()
