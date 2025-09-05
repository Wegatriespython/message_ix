***
* Simple HHI Hard Cap Constraints Module (Original Implementation)
* =================================================================
* This is the simpler original implementation that was working in previous commits
* Uses direct aggregation without intermediate Y_TEC variables
***

*----------------------------------------------------------------------------------------------------------------------*
* Variable declarations for HHI constraints                                                                           *
*----------------------------------------------------------------------------------------------------------------------*

* Z_REG: auxiliary variable for rotated SOC constraint per technology (aggregated over vintages/modes)
* T_GROUP: total activity for each commodity group
Positive Variables
    Z_REG(node,commodity,level,year_all,time,tec)
    T_GROUP(node,commodity,level,year_all,time)
;

*----------------------------------------------------------------------------------------------------------------------*
* Equation declarations for HHI constraints                                                                           *
*----------------------------------------------------------------------------------------------------------------------*

Equations
    GROUP_TOTAL_CALC(node,commodity,level,year_all,time)  calculate total activity for each commodity group
    ROTATED_SOC_CONSTRAINT(node,commodity,level,year_all,time,tec)  rotated second-order cone constraint for technology-level HHI
    HHI_CAP(node,commodity,level,year_all,time)  hard cap on HHI per commodity group
;

*----------------------------------------------------------------------------------------------------------------------*
* Equation definitions for HHI constraints                                                                            *
*----------------------------------------------------------------------------------------------------------------------*

GROUP_TOTAL_CALC(node,commodity,level,year,time)..
    T_GROUP(node,commodity,level,year,time) =E=
        SUM((tec,vintage,mode)$(
            map_tec_lifetime(node,tec,vintage,year) AND 
            map_tec_act(node,tec,year,mode,time) AND
            output(node,tec,vintage,year,mode,node,commodity,level,time,time) > 0),
            ACT(node,tec,vintage,year,mode,time) * 
            output(node,tec,vintage,year,mode,node,commodity,level,time,time))
;

ROTATED_SOC_CONSTRAINT(node,commodity,level,year,time,tec)$(
    inv_tec(tec) AND 
    SUM((vintage,mode)$(map_tec_lifetime(node,tec,vintage,year) AND 
                        map_tec_act(node,tec,year,mode,time) AND
                        output(node,tec,vintage,year,mode,node,commodity,level,time,time) > 0), 1) )..
    SQR( SQRT(2) * SUM((vintage,mode)$(
            map_tec_lifetime(node,tec,vintage,year) AND 
            map_tec_act(node,tec,year,mode,time) AND
            output(node,tec,vintage,year,mode,node,commodity,level,time,time) > 0),
            ACT(node,tec,vintage,year,mode,time) * 
            output(node,tec,vintage,year,mode,node,commodity,level,time,time)) )
    + SQR( T_GROUP(node,commodity,level,year,time) - 
           Z_REG(node,commodity,level,year,time,tec) )
    =L= 
    SQR( T_GROUP(node,commodity,level,year,time) + 
         Z_REG(node,commodity,level,year,time,tec) )
;

HHI_CAP(node,commodity,level,year,time)..
    SUM(tec$(
        inv_tec(tec) AND 
        SUM((vintage,mode)$(map_tec_lifetime(node,tec,vintage,year) AND 
                            map_tec_act(node,tec,year,mode,time) AND
                            output(node,tec,vintage,year,mode,node,commodity,level,time,time) > 0), 1)),
        Z_REG(node,commodity,level,year,time,tec))
    =L= 
    hhi_limit(node,commodity,level,year,time) * T_GROUP(node,commodity,level,year,time) * 0.5
;