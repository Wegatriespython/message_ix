* --- HHI (tech-level) via COMMODITY_BALANCE_AUX pattern ------------------------

Alias (year_all, y_hhi);

* Expect hhi_limit(node,commodity,level,year_all,time) in [0,1].
* If your data are 0..100 or 0..10000, pre-scale them in data prep.

Positive Variables
    Y_MARKET(node,commodity,level,year_all,time)
    Y_TEC   (node,commodity,level,year_all,time,tec)
;

Equations
    DEF_Y_MARKET(node,commodity,level,year_all,time)
    DEF_Y_TEC   (node,commodity,level,year_all,time,tec)
    DEF_HHI_LIMIT(node,commodity,level,year_all,time)
;

* Total market = sum of outputs to (node,commodity,level,time)
DEF_Y_MARKET(node,commodity,level,y_hhi,time)$(
    year(y_hhi) AND hhi_limit(node,commodity,level,y_hhi,time) > 0
)..
    Y_MARKET(node,commodity,level,y_hhi,time)
    =E=
    SUM( (location,tec,vintage,mode,time2)$(
            output(location,tec,vintage,y_hhi,mode,node,commodity,level,time2,time)
        AND map_tec_act(location,tec,y_hhi,mode,time2)
        AND map_tec_lifetime(location,tec,vintage,y_hhi)
        ),
        ACT(location,tec,vintage,y_hhi,mode,time2)
      * output(location,tec,vintage,y_hhi,mode,node,commodity,level,time2,time)
      * duration_time_rel(time,time2)
    );

* Tech-level aggregation BEFORE squaring (prevents artificial dilution by splitting)
DEF_Y_TEC(node,commodity,level,y_hhi,time,tec)$(
    year(y_hhi) AND hhi_limit(node,commodity,level,y_hhi,time) > 0
)..
    Y_TEC(node,commodity,level,y_hhi,time,tec)
    =E=
    SUM( (location,vintage,mode,time2)$(
            output(location,tec,vintage,y_hhi,mode,node,commodity,level,time2,time)
        AND map_tec_act(location,tec,y_hhi,mode,time2)
        AND map_tec_lifetime(location,tec,vintage,y_hhi)
        ),
        ACT(location,tec,vintage,y_hhi,mode,time2)
      * output(location,tec,vintage,y_hhi,mode,node,commodity,level,time2,time)
      * duration_time_rel(time,time2)
    );

* Quadratic HHI cap: sum_tec (Y_TEC^2) <= hhi_limit * (Y_MARKET)^2
DEF_HHI_LIMIT(node,commodity,level,y_hhi,time)$(
    year(y_hhi) AND hhi_limit(node,commodity,level,y_hhi,time) > 0
)..
    SUM(tec, sqr( Y_TEC(node,commodity,level,y_hhi,time,tec) ))
    =L=
    hhi_limit(node,commodity,level,y_hhi,time)
  * sqr( Y_MARKET(node,commodity,level,y_hhi,time) );

