import ixmp as ix
import message_ix


#import pandas as pd

mp = ix.Platform(name="ixmp_dev", jvmargs=["-Xmx14G"])

# Source scenario details
model = "clone_geidco_test_SSP2_v5.3"
scenario = "baseline_geidco_test"

# Target scenario details
# load scenario, but DO NOT MAKE CHANGES to it
scen= message_ix.Scenario(mp, model, scenario, cache=True)
# clone to a scenario you want to use and do what you want
#scen.solve(solve_options = {"lp_method" : "4", "writemps":"basline.mps"})

