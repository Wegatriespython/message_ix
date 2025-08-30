Parameter
    demand_quantity(node,sector,year_all)
;

* useful energy/service demand levels from MESSAGE get mapped onto MACRO sector structure
demand_quantity(node,sector,year) =
    sum((commodity,level,time)$( mapping_macro_sector(sector,commodity,level) ),
    demand(node,commodity,level,horizon,time) * duration_time(time) ) ;

* useful energy/service demand prices from MESSAGE get mapped onto MACRO sector structure
* TODO: This normalization may need correction for non-uniform periods if discountfactor != df_year
* If discountfactor(year) * duration_period(year) should be df_year(year) * annuity_factor(year)
report_demand_shadow_price(node,sector,year) =
    sum((commodity, level, time) $ mapping_macro_sector(sector,commodity,level),
        COMMODITY_BALANCE.M(node,commodity,level,year,time) * duration_time(time) )
        / ( discountfactor(year) * duration_period(year) ) ;
