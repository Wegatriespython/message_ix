***
* Herfindahl-Hirschman Index (HHI) Hard Cap Constraints Module
* ============================================================= 
* This module implements market concentration constraints using
* rotated second-order cone programming (SOCP) formulation
***

* Alias for year_all to avoid conflicts with existing aliases
Alias (year_all,y_hhi);

* Small epsilon to avoid cone apex for proper dual computation
Scalar eps_soc /1e-12/;

*----------------------------------------------------------------------------------------------------------------------*
* Variable declarations for HHI constraints                                                                           *
*----------------------------------------------------------------------------------------------------------------------*

* Y_TEC: counted output of technology for HHI calculation
* Z_REG: auxiliary variable for rotated SOC constraint per technology (aggregated over vintages/modes)
* T_GROUP: total activity for each commodity group
Positive Variables
    Y_TEC(node,commodity,level,y_hhi,time,tec)
    Z_REG(node,commodity,level,y_hhi,time,tec)
    T_GROUP(node,commodity,level,y_hhi,time)
;

*----------------------------------------------------------------------------------------------------------------------*
* Equation declarations for HHI constraints                                                                           *
*----------------------------------------------------------------------------------------------------------------------*

Equations
    DEF_Y_TEC(node,commodity,level,y_hhi,time,tec)
    GROUP_TOTAL_CALC(node,commodity,level,y_hhi,time)
    ROTATED_SOC_CONSTRAINT(node,commodity,level,y_hhi,time,tec)
    HHI_CAP(node,commodity,level,y_hhi,time)
;

*----------------------------------------------------------------------------------------------------------------------*
* Equation definitions for HHI constraints                                                                            *
*----------------------------------------------------------------------------------------------------------------------*

* --- Counted output per tech, only if a cap exists and tech can produce into (node,commodity,level,time)
DEF_Y_TEC(node,commodity,level,y_hhi,time,tec)$(
      year(y_hhi)
  AND hhi_limit(node,commodity,level,y_hhi,time)
  AND SUM((vintage,mode)$(
            map_tec_lifetime(node,tec,vintage,y_hhi)
        AND map_tec_act(node,tec,y_hhi,mode,time)
        AND output(node,tec,vintage,y_hhi,mode,node,commodity,level,time,time) > 0), 1)
)..
    Y_TEC(node,commodity,level,y_hhi,time,tec) =E=
        SUM((vintage,mode)$(
            map_tec_lifetime(node,tec,vintage,y_hhi)
        AND map_tec_act(node,tec,y_hhi,mode,time)
        AND output(node,tec,vintage,y_hhi,mode,node,commodity,level,time,time) > 0),
            ACT(node,tec,vintage,y_hhi,mode,time) * 
            output(node,tec,vintage,y_hhi,mode,node,commodity,level,time,time));

* --- Group total (only where a cap exists)
GROUP_TOTAL_CALC(node,commodity,level,y_hhi,time)$(
    year(y_hhi) AND hhi_limit(node,commodity,level,y_hhi,time)
)..
    T_GROUP(node,commodity,level,y_hhi,time) =E= 
        SUM(tec, Y_TEC(node,commodity,level,y_hhi,time,tec));

* --- Rotated SOC per tech (SOCP) with tiny tilt for duals
ROTATED_SOC_CONSTRAINT(node,commodity,level,y_hhi,time,tec)$(
      year(y_hhi)
  AND hhi_limit(node,commodity,level,y_hhi,time)
  AND SUM((vintage,mode)$(
            map_tec_lifetime(node,tec,vintage,y_hhi)
        AND map_tec_act(node,tec,y_hhi,mode,time)
        AND output(node,tec,vintage,y_hhi,mode,node,commodity,level,time,time) > 0), 1)
)..
    SQR( SQRT(2) * Y_TEC(node,commodity,level,y_hhi,time,tec) )
  + SQR( (T_GROUP(node,commodity,level,y_hhi,time) + eps_soc) - 
         Z_REG(node,commodity,level,y_hhi,time,tec) )
    =L= 
    SQR( (T_GROUP(node,commodity,level,y_hhi,time) + eps_soc) + 
         Z_REG(node,commodity,level,y_hhi,time,tec) );

* --- Hard cap only where defined
HHI_CAP(node,commodity,level,y_hhi,time)$(
    year(y_hhi) AND hhi_limit(node,commodity,level,y_hhi,time)
)..
    SUM(tec, Z_REG(node,commodity,level,y_hhi,time,tec))
    =L= 
    0.5 * hhi_limit(node,commodity,level,y_hhi,time) * T_GROUP(node,commodity,level,y_hhi,time);

*----------------------------------------------------------------------------------------------------------------------*
* Variable bounds to reduce model size (optional)                                                                     *
*----------------------------------------------------------------------------------------------------------------------*

* Zero upper bounds for variables outside scope to avoid stray columns
Y_TEC.UP(node,commodity,level,y_hhi,time,tec)$(
  NOT (year(y_hhi) AND hhi_limit(node,commodity,level,y_hhi,time)
       AND SUM((vintage,mode)$(
               map_tec_lifetime(node,tec,vintage,y_hhi)
           AND map_tec_act(node,tec,y_hhi,mode,time)
           AND output(node,tec,vintage,y_hhi,mode,node,commodity,level,time,time) > 0), 1)) 
) = 0;

Z_REG.UP(node,commodity,level,y_hhi,time,tec)$(
  NOT (year(y_hhi) AND hhi_limit(node,commodity,level,y_hhi,time)
       AND SUM((vintage,mode)$(
               map_tec_lifetime(node,tec,vintage,y_hhi)
           AND map_tec_act(node,tec,y_hhi,mode,time)
           AND output(node,tec,vintage,y_hhi,mode,node,commodity,level,time,time) > 0), 1)) 
) = 0;

T_GROUP.UP(node,commodity,level,y_hhi,time)$(
    NOT (year(y_hhi) AND hhi_limit(node,commodity,level,y_hhi,time)) 
) = 0;

*----------------------------------------------------------------------------------------------------------------------*
* Scalars for post-solve diagnostics                                                                                  *
*----------------------------------------------------------------------------------------------------------------------*

* These will be used in hhi_postsolve.gms to count generated equations
Scalar n_def "Number of DEF_Y_TEC equations generated";
Scalar n_soc "Number of ROTATED_SOC_CONSTRAINT equations generated";
Scalar n_cap "Number of HHI_CAP equations generated";

