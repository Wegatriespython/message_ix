***
* Land-use module for MESSAGE
* ============================
* This file contains land-use model emulator equations and constraints
* Variable and equation declarations remain in model_core.gms
* Extracted from the original model_core.gms for better modularity
***

*----------------------------------------------------------------------------------------------------------------------*
***
* .. _section_landuse_emulator:
*
* Land-use model emulator section
* -------------------------------
*
* Bounds on total land use
* ^^^^^^^^^^^^^^^^^^^^^^^^
*
* .. _equation_land_constraint:
*
* Equation LAND_CONSTRAINT
* """"""""""""""""""""""""
* This constraint enforces a meaningful result of the land-use model emulator,
* in particular a bound on the total land used in |MESSAGEix|.
* The linear combination of land scenarios must be equal to 1.
*
*  .. math::
*     \sum_{s \in S} \text{LAND}_{n,s,y} = 1
*
***
LAND_CONSTRAINT(node,year)$( SUM(land_scenario$( map_land(node,land_scenario,year) ), 1 ) ) ..
    SUM(land_scenario$( map_land(node,land_scenario,year) ), LAND(node,land_scenario,year) ) =E= 1 ;

***
* Dynamic constraints on land use
* ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
* These constraints enforces upper and lower bounds on the change rate per land scenario.
*
* .. _equation_dynamic_land_scen_constraint_up:
*
* Equation DYNAMIC_LAND_SCEN_CONSTRAINT_UP
* """"""""""""""""""""""""""""""""""""""""
*
*  .. math::
*     \text{LAND}_{n,s,y}
*         \leq & \text{initial_land_scen_up}_{n,s,y}
*             \cdot \frac{ \Big( 1 + \text{growth_land_scen_up}_{n,s,y} \Big)^{|y|} - 1 }
*                        { \text{growth_land_scen_up}_{n,s,y} } \\
*              & + \big( \text{LAND}_{n,s,y-1} + \text{historical_land}_{n,s,y-1} \big)
*                  \cdot \Big( 1 + \text{growth_land_scen_up}_{n,s,y} \Big)^{|y|}
*
***
DYNAMIC_LAND_SCEN_CONSTRAINT_UP(node,land_scenario,year)$( map_land(node,land_scenario,year)
        AND is_dynamic_land_scen_up(node,land_scenario,year) )..
* share of land scenario in
    LAND(node,land_scenario,year) =L=
* initial 'new' land used for that type (compounded over the duration of the period)
        initial_land_scen_up(node,land_scenario,year) * (
            ( ( POWER( 1 + growth_land_scen_up(node,land_scenario,year) , duration_period(year) ) - 1 )
                / growth_land_scen_up(node,land_scenario,year) )$( growth_land_scen_up(node,land_scenario,year) )
              + ( duration_period(year) )$( NOT growth_land_scen_up(node,land_scenario,year) )
            )
* expansion of land scenario from previous period
        + SUM((year_all2)$( seq_period(year_all2,year) ),
                ( LAND(node,land_scenario,year_all2)$( model_horizon(year_all2) )
                  + historical_land(node,land_scenario,year_all2) )
                * POWER( 1 + growth_land_scen_up(node,land_scenario,year) , duration_period(year) )
            )
* optional relaxation for calibration and debugging
%SLACK_LAND_SCEN_UP% + SLACK_LAND_SCEN_UP(node,land_scenario,year)
;

***
* .. _equation_dynamic_land_scen_constraint_lo:
*
* Equation DYNAMIC_LAND_SCEN_CONSTRAINT_LO
* """"""""""""""""""""""""""""""""""""""""
*
*  .. math::
*     \text{LAND}_{n,s,y}
*         \geq & - \text{initial_land_scen_lo}_{n,s,y}
*             \cdot \frac{ \Big( 1 + \text{growth_land_scen_lo}_{n,s,y} \Big)^{|y|} - 1 }
*                        { \text{growth_land_scen_lo}_{n,s,y} } \\
*              & + \big( \text{LAND}_{n,s,y-1} + \text{historical_land}_{n,s,y-1} \big)
*                  \cdot \Big( 1 + \text{growth_land_scen_lo}_{n,s,y} \Big)^{|y|}
*
***
DYNAMIC_LAND_SCEN_CONSTRAINT_LO(node,land_scenario,year)$( map_land(node,land_scenario,year)
        AND is_dynamic_land_scen_lo(node,land_scenario,year) )..
* share of land scenario in
    LAND(node,land_scenario,year) =G=
* initial 'new' land used for that type (compounded over the duration of the period)
        - initial_land_scen_lo(node,land_scenario,year) * (
            ( ( POWER( 1 + growth_land_scen_lo(node,land_scenario,year) , duration_period(year) ) - 1 )
                / growth_land_scen_lo(node,land_scenario,year) )$( growth_land_scen_lo(node,land_scenario,year) )
              + ( duration_period(year) )$( NOT growth_land_scen_lo(node,land_scenario,year) )
            )
* reduction of land scenario from previous period
        + SUM((year_all2)$( seq_period(year_all2,year) ),
                ( LAND(node,land_scenario,year_all2)$( model_horizon(year_all2) )
                  + historical_land(node,land_scenario,year_all2) )
                * POWER( 1 + growth_land_scen_lo(node,land_scenario,year) , duration_period(year) )
            )
* optional relaxation for calibration and debugging
%SLACK_LAND_SCEN_LO% - SLACK_LAND_SCEN_LO(node,land_scenario,year)
;

***
* These constraints enforces upper and lower bounds on the change rate per land type
* determined as a linear combination of land use scenarios.
*
* .. _equation_dynamic_land_type_constraint_up:
*
* Equation DYNAMIC_LAND_TYPE_CONSTRAINT_UP
* """"""""""""""""""""""""""""""""""""""""
*
*  .. math::
*     \sum_{s \in S} \text{land_use}_{n,s,y,u} &\cdot \text{LAND}_{n,s,y}
*         \leq \text{initial_land_up}_{n,y,u}
*             \cdot \frac{ \Big( 1 + \text{growth_land_up}_{n,y,u} \Big)^{|y|} - 1 }
*                        { \text{growth_land_up}_{n,y,u} } \\
*              & + \Big( \sum_{s \in S} \big( \text{land_use}_{n,s,y-1,u}
*                          + \text{dynamic_land_up}_{n,s,y-1,u} \big) \\
*                            & \quad \quad \cdot \big( \text{LAND}_{n,s,y-1} + \text{historical_land}_{n,s,y-1} \big) \Big) \\
*                            & \quad \cdot \Big( 1 + \text{growth_land_up}_{n,y,u} \Big)^{|y|}
*
***
DYNAMIC_LAND_TYPE_CONSTRAINT_UP(node,year,land_type)$( is_dynamic_land_up(node,year,land_type) )..
* amount of land assigned to specific type in current period
    SUM(land_scenario$( map_land(node,land_scenario,year) ),
        land_use(node,land_scenario,year,land_type) * LAND(node,land_scenario,year) ) =L=
* initial 'new' land used for that type (compounded over the duration of the period)
        initial_land_up(node,year,land_type) * (
            ( ( POWER( 1 + growth_land_up(node,year,land_type) , duration_period(year) ) - 1 )
                / growth_land_up(node,year,land_type) )$( growth_land_up(node,year,land_type) )
              + ( duration_period(year) )$( NOT growth_land_up(node,year,land_type) )
            )
* expansion of previously used land of this type from previous period and upper bound on land use transformation
        + SUM((year_all2)$( seq_period(year_all2,year) ),
            SUM(land_scenario$( map_land(node,land_scenario,year) ),
                ( land_use(node,land_scenario,year_all2,land_type)
                  + dynamic_land_up(node,land_scenario,year_all2,land_type) )
                * ( LAND(node,land_scenario,year_all2)$( model_horizon(year_all2) )
                    + historical_land(node,land_scenario,year_all2) )
                * POWER( 1 + growth_land_up(node,year,land_type) , duration_period(year) )
              )
          )
* optional relaxation for calibration and debugging
%SLACK_LAND_TYPE_UP% + SLACK_LAND_TYPE_UP(node,year,land_type)
;

***
* .. _equation_dynamic_land_type_constraint_lo:
*
* Equation DYNAMIC_LAND_TYPE_CONSTRAINT_LO
* """"""""""""""""""""""""""""""""""""""""
*
*  .. math::
*     \sum_{s \in S} \text{land_use}_{n,s,y,u} &\cdot \text{LAND}_{n,s,y}
*         \geq - \text{initial_land_lo}_{n,y,u}
*             \cdot \frac{ \Big( 1 + \text{growth_land_lo}_{n,y,u} \Big)^{|y|} - 1 }
*                        { \text{growth_land_lo}_{n,y,u} } \\
*              & + \Big( \sum_{s \in S} \big( \text{land_use}_{n,s,y-1,u}
*                          + \text{dynamic_land_lo}_{n,s,y-1,u} \big) \\
*                            & \quad \quad \cdot \big( \text{LAND}_{n,s,y-1} + \text{historical_land}_{n,s,y-1} \big) \Big) \\
*                            & \quad \cdot \Big( 1 + \text{growth_land_lo}_{n,y,u} \Big)^{|y|}
*
***
DYNAMIC_LAND_TYPE_CONSTRAINT_LO(node,year,land_type)$( is_dynamic_land_lo(node,year,land_type) )..
* amount of land assigned to specific type in current period
    SUM(land_scenario$( map_land(node,land_scenario,year) ),
        land_use(node,land_scenario,year,land_type) * LAND(node,land_scenario,year) ) =G=
* initial 'new' land used for that type (compounded over the duration of the period)
        - initial_land_lo(node,year,land_type) * (
            ( ( POWER( 1 + growth_land_up(node,year,land_type) , duration_period(year) ) - 1 )
                / growth_land_lo(node,year,land_type) )$( growth_land_lo(node,year,land_type) )
              + ( duration_period(year) )$( NOT growth_land_lo(node,year,land_type) )
            )
* expansion of previously used land of this type from previous period and lower bound on land use transformation
        + SUM((year_all2)$( seq_period(year_all2,year) ),
            SUM(land_scenario$( map_land(node,land_scenario,year) ),
                ( land_use(node,land_scenario,year_all2,land_type)
                  + dynamic_land_lo(node,land_scenario,year_all2,land_type) )
                * ( LAND(node,land_scenario,year_all2)$( model_horizon(year_all2) )
                    + historical_land(node,land_scenario,year_all2) )
                * POWER( 1 + growth_land_lo(node,year,land_type) , duration_period(year) )
              )
          )
* optional relaxation for calibration and debugging
%SLACK_LAND_TYPE_LO% - SLACK_LAND_TYPE_LO(node,year,land_type)
;

*----------------------------------------------------------------------------------------------------------------------*