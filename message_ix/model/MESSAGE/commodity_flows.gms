***
* Commodity flows module for MESSAGE
* ===================================
* This file contains commodity flows and balance equations and constraints
* Variable and equation declarations remain in model_core.gms
* Extracted from the original model_core.gms for better modularity
***

*----------------------------------------------------------------------------------------------------------------------*
* Equation Definitions
*----------------------------------------------------------------------------------------------------------------------*

***
* .. _equation_commodity_balance_aux:
*
* Equation COMMODITY_BALANCE_AUX
* """"""""""""""""""""""""""""""
*
* This equation calculates the commodity balance for each node, commodity, level, year and time.
* The commodity balance constraint at the resource level is included in the `Equation RESOURCE_CONSTRAINT`_,
* while at the renewable level, it is included in the `Equation RENEWABLES_EQUIVALENCE`_,
* and at the storage level, it is included in the `Equation STORAGE_BALANCE`_.
***
COMMODITY_BALANCE_AUX(node,commodity,level,year,time)$(
  map_commodity(node,commodity,level,year,time)
  AND NOT (level_renewable(level) OR level_resource(level))
) ..
  COMMODITY_BALANCE(node,commodity,level,year,time)
  =E=
  SUM(
    (location,tec,vintage,mode,time2)$(
      map_tec_act(location,tec,year,mode,time2)
      AND map_tec_lifetime(location,tec,vintage,year)
    ),
    # Import into node and output from technologies located at 'location' sending to 'node' and 'time2' sending to 'time
    # Export from node and input into technologies located at 'location' taking from 'node' and 'time2' taking from 'time'
    (
      output(location,tec,vintage,year,mode,node,commodity,level,time2,time)
      - input(location,tec,vintage,year,mode,node,commodity,level,time2,time)
    ) * duration_time_rel(time,time2)
    * ACT(location,tec,vintage,year,mode,time2)
  )

  # Quantity taken out from ( >0 ) or put into ( <0 ) inter-period stock (storage)
  + STOCK_CHG(node,commodity,level,year,time)$map_stocks(node,commodity,level,year)

  # Yield from land-use model emulator
  + SUM(
    land_scenario,
    (
      land_output(node,land_scenario,year,commodity,level,time)
      - land_input(node,land_scenario,year,commodity,level,time)
    ) * LAND(node,land_scenario,year)
  )

  # Final demand (exogenous parameter to be satisfied by the commodity system)
  - demand_fixed(node,commodity,level,year,time)

$IFTHEN %MESSAGE_CAP_COMM% == "1"
  # Commodity flows associated with CAP and CAP_NEW
  #
  # This section contains 5 SUM()s that are included only if MESSAGE_CAP_COMM is set to "1".

  # (1) CAP and {in,out}put_cap: flows due to operation of existing capacity
  + SUM(
    (location,tec,vintage)$(inv_tec(tec) AND map_tec_lifetime(location,tec,vintage,year)),
    (
      output_cap(location,tec,vintage,year,node,commodity,level,time)
      - input_cap(location,tec,vintage,year,node,commodity,level,time)
    ) * CAP(location,tec,vintage,year)
  )

  # (2) CAP_NEW and {in,out}put_cap_new: flows due to construction of new capacity (during vintage period)
  + SUM(
    (location,tec)$(inv_tec(tec) AND map_tec(location,tec,year)),
    (
      output_cap_new(location,tec,year,node,commodity,level,time)
      - input_cap_new(location,tec,year,node,commodity,level,time)
    ) * CAP_NEW(location,tec,year)
  )

  # (3) CAP and {in,out}put_cap_ret: flows due to retirement of CAP (any model period after the first)
  + SUM(
    (location,tec,vintage,year2)$map_cap_ret(location,tec,vintage,year2,year),
    (
      output_cap_ret(location,tec,vintage,node,commodity,level,time)
      - input_cap_ret(location,tec,vintage,node,commodity,level,time)
    ) * (
      # Differential of capacity in year2 vs. year
      CAP(location,tec,vintage,year2) - CAP(location,tec,vintage,year)
    ) / duration_period(year)
  )

  # (4) historical_new_capacity and {in,out}put_cap_ret (1 of 2)
  #
  # Flows due to CAP(…,vintage,…) that reaches EOL in the final pre-horizon period, 'year_all2'.
  # These are counted in the first model period, 'year'.
  + SUM(
    (location,tec,vintage,year_all2)$map_cap_ret_hist_1(location,tec,vintage,year_all2,year),
    (
      output_cap_ret(location,tec,vintage,node,commodity,level,time)
      - input_cap_ret(location,tec,vintage,node,commodity,level,time)
    ) * historical_new_capacity(node,tec,vintage)
    * remaining_capacity_extended(node,tec,vintage,year_all2)
  )

  # (5) historical_new_capacity and {in,out}put_cap_ret (2 of 2)
  #
  # Flows due to CAP(…,vintage,…) that reaches EOL in the first model period, 'year'.
  + SUM(
    (location,tec,vintage,year_all2)$map_cap_ret_hist_2(location,tec,vintage,year_all2,year),
    (
      output_cap_ret(location,tec,vintage,node,commodity,level,time)
      - input_cap_ret(location,tec,vintage,node,commodity,level,time)
    ) * historical_new_capacity(node,tec,vintage)
    * (1 - remaining_capacity_extended(node,tec,vintage,year))
  )
$ENDIF
;

***
* .. _commodity_balance_gt:
*
* Equation COMMODITY_BALANCE_GT
* """""""""""""""""""""""""""""
* This constraint ensures that supply is greater or equal than demand for every commodity-level combination.
*
*  .. math::
*     \COMMODITYBALANCE_{n,c,l,y,h} \geq 0
*
***
COMMODITY_BALANCE_GT(node,commodity,level,year,time)$(
  map_commodity(node,commodity,level,year,time)
  AND NOT (level_resource(level) OR level_renewable(level) OR level_storage(level))
)..
  COMMODITY_BALANCE(node,commodity,level,year,time)
* relaxation of constraints for debugging
%SLACK_COMMODITY_EQUIVALENCE% + SLACK_COMMODITY_EQUIVALENCE_UP(node,commodity,level,year,time)
  =G=
  0
;

***
* .. _commodity_balance_lt:
*
* Equation COMMODITY_BALANCE_LT
* """""""""""""""""""""""""""""
* This constraint ensures that the supply is smaller than or equal to the demand for all commodity-level combinations
* given in the :math:`\text{balance_equality}_{c,l}`. In combination with the constraint above, it ensures that supply
* is (exactly) equal to demand.
*
*  .. math::
*     \COMMODITYBALANCE_{n,c,l,y,h} \leq 0
*
***
COMMODITY_BALANCE_LT(node,commodity,level,year,time)$(
  map_commodity(node,commodity,level,year,time)
  AND NOT (level_resource(level) OR level_renewable(level) OR level_storage(level))
  AND balance_equality(commodity,level)
)..
  COMMODITY_BALANCE(node,commodity,level,year,time)
* relaxation of constraints for debugging
%SLACK_COMMODITY_EQUIVALENCE% - SLACK_COMMODITY_EQUIVALENCE_LO(node,commodity,level,year,time)
  =L=
  0
;

***
* .. equation_stock_balance:
*
* Equation STOCKS_BALANCE
* """""""""""""""""""""""
* This constraint ensures the inter-temporal balance of commodity stocks.
* The parameter :math:`\text{commodity_stocks}_{n,c,l}` can be used to model exogenous additions to the stock
*
*  .. math::
*     \text{STOCK}_{n,c,l,y} + \text{commodity_stock}_{n,c,l,y} =
*         \text{duration_period}_{y} \cdot & \sum_{h} \text{STOCK_CHG}_{n,c,l,y,h} \\
*                                    & + \text{STOCK}_{n,c,l,y+1}
*
***
STOCKS_BALANCE(node,commodity,level,year)$( map_stocks(node,commodity,level,year) )..
    STOCK(node,commodity,level,year)$( NOT first_period(year) )
    + commodity_stock(node,commodity,level,year) =E=
    duration_period(year) * SUM(time$( map_commodity(node,commodity,level,year,time) ),
         STOCK_CHG(node,commodity,level,year,time) )
    + SUM(year2$( seq_period(year,year2) ), STOCK(node,commodity,level,year2) ) ;


