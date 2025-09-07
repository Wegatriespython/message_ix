***
* .. _equation_capacity_constraint:
*
* Equation CAPACITY_CONSTRAINT
* """"""""""""""""""""""""""""
* This constraint ensures that the actual activity of a technology at a node cannot exceed available (maintained)
* capacity summed over all vintages, including the technology capacity factor :math:`\text{capacity_factor}_{n,t,y,t}`.
*
*  .. math::
*     \sum_{m} \text{ACT}_{n,t,y^V,y,m,h}
*         \leq \text{duration_time}_{h} \cdot \text{capacity_factor}_{n,t,y^V,y,h} \cdot \text{CAP}_{n,t,y^V,y}
*         \quad \forall \ t \ \in \ T^{\text{INV}}
*
***
CAPACITY_CONSTRAINT(node,inv_tec,vintage,year,time)$( map_tec_time(node,inv_tec,year,time)
        AND map_tec_lifetime(node,inv_tec,vintage,year) )..
    SUM(mode$( map_tec_act(node,inv_tec,year,mode,time) ), ACT(node,inv_tec,vintage,year,mode,time) )
        =L= duration_time(time) * capacity_factor(node,inv_tec,vintage,year,time) * CAP(node,inv_tec,vintage,year) ;

***
* .. _equation_capacity_maintenance_hist:
*
* Equation CAPACITY_MAINTENANCE_HIST
* """"""""""""""""""""""""""""""""""
* The following three constraints implement technology capacity maintenance over time to allow early retirement.
* The optimization problem determines the optimal timing of retirement, when fixed operation-and-maintenance costs
* exceed the benefit in the objective function.
*
* The first constraint ensures that historical capacity (built prior to the model horizon) is available
* as installed capacity in the first model period.
*
*   .. math::
*      CAP_{n,t,y^V,'first\_period'} & \leq
*          remaining\_capacity_{n,t,y^V,'first\_period'} \cdot
*          duration\_period_{y^V} \cdot
*          historical\_new\_capacity_{n,t,y^V} \\
*      & \text{if } y^V  < first\_period \text{ and } |y| - |y^V| < technical\_lifetime_{n,t,y^V}
*      \quad \forall \ t \in T^{INV}
*
***
CAPACITY_MAINTENANCE_HIST(node,inv_tec,vintage,first_period)$( map_tec_lifetime(node,inv_tec,vintage,first_period)
        AND historical(vintage))..
    CAP(node,inv_tec,vintage,first_period)
    =L= remaining_capacity(node,inv_tec,vintage,first_period) *
        duration_period(vintage) * historical_new_capacity(node,inv_tec,vintage) ;

***
* .. _equation_capacity_maintenance_new:
*
* Equation CAPACITY_MAINTENANCE_NEW
* """""""""""""""""""""""""""""""""
* The second constraint ensures that capacity is fully maintained throughout the model period
* in which it was constructed (no early retirement in the period of construction).
*
*   .. math::
*      \text{CAP}_{n,t,y^V,y^V} =
*          \text{remaining_capacity}_{n,t,y^V,y^V} \cdot
*          \text{duration_period}_{y^V} \cdot
*          \text{CAP_NEW}_{n,t,y^V}
*      \quad \forall \ t \in T^{\text{INV}}
*
* The current formulation does not account for construction time in the constraints, but only adds a mark-up
* to the investment costs in the objective function.
***
CAPACITY_MAINTENANCE_NEW(node,inv_tec,vintage,vintage)$( map_tec_lifetime(node,inv_tec,vintage,vintage) )..
    CAP(node,inv_tec,vintage,vintage)
    =E= remaining_capacity(node,inv_tec,vintage,vintage)
        * duration_period(vintage) * CAP_NEW(node,inv_tec,vintage) ;

***
* .. _equation_capacity_maintenance:
*
* Equation CAPACITY_MAINTENANCE
* """""""""""""""""""""""""""""
* The third constraint implements the dynamics of capacity maintenance throughout the model horizon.
* Installed capacity can be maintained over time until decommissioning, which is irreversible.
*
*   .. math::
*      CAP_{n,t,y^V,y} & \leq
*          remaining\_capacity_{n,t,y^V,y} \cdot
*          CAP_{n,t,y^V,y-1} \\
*      \quad & \text{if } y > y^V \text{ and } y^V  > first\_period \text{ and } |y| - |y^V| < technical\_lifetime_{n,t,y^V}
*      \quad \forall \ t \in T^{INV}
*
***
CAPACITY_MAINTENANCE(node,inv_tec,vintage,year)$( map_tec_lifetime(node,inv_tec,vintage,year)
        AND NOT first_period(year) AND year_order(vintage) < year_order(year))..
    CAP(node,inv_tec,vintage,year)
    =L= remaining_capacity(node,inv_tec,vintage,year) *
        ( SUM(year2$( seq_period(year2,year) ),
              CAP(node,inv_tec,vintage,year2) ) ) ;

***
* .. _equation_end_of_lifetime_capacity:
*
* Equation END_OF_LIFETIME_CAPACITY
* """""""""""""""""""""""""""""""""
* This constraint ensures that the capacity is not preserved after the technical lifetime of a technology.
*
* .. math::
*    CAP_{n,t,y^V,y} = 0 \\
*    \quad & \text{if } y > y^V \text{ and } y^V  > first\_period \text{ and } |y| - |y^V| >= technical\_lifetime_{n,t,y^V}
*    \quad \forall \ t \in T^{INV}
*
***
END_OF_LIFETIME_CAPACITY(node,inv_tec,vintage,year)$(
  cap_comm
  AND map_tec(node,inv_tec,vintage)
  AND NOT map_tec_lifetime(node,inv_tec,vintage,year)
  AND NOT first_period(year)
  AND year_order(vintage) < year_order(year)
) ..
  CAP(node,inv_tec,vintage,year) =L= 0 ;

* .. _equation_operation_constraint:
*
* Equation OPERATION_CONSTRAINT
* """""""""""""""""""""""""""""
* This constraint provides an upper bound on the total operation of installed capacity over a year.
* It can be used to represent reuqired scheduled unavailability of installed capacity.
*
*   .. math::
*      \sum_{m,h} \text{ACT}_{n,t,y^V,y,m,h}
*          \leq \text{operation_factor}_{n,t,y^V,y} \cdot \text{capacity_factor}_{n,t,y^V,y,m,\text{'year'}} \cdot \text{CAP}_{n,t,y^V,y}
*      \quad \forall \ t \in T^{\text{INV}}
*
* This constraint is only active if :math:`\text{operation_factor}_{n,t,y^V,y} < 1`.
***
OPERATION_CONSTRAINT(node,inv_tec,vintage,year)$( map_tec_lifetime(node,inv_tec,vintage,year)
        AND operation_factor(node,inv_tec,vintage,year) < 1 )..
    SUM((mode,time)$( map_tec_act(node,inv_tec,year,mode,time) ), ACT(node,inv_tec,vintage,year,mode,time) ) =L=
        operation_factor(node,inv_tec,vintage,year) * capacity_factor(node,inv_tec,vintage,year,'year')
        * CAP(node,inv_tec,vintage,year) ;

***
* .. _equation_min_utlitation_constraint:
*
* Equation MIN_UTILIZATION_CONSTRAINT
* """""""""""""""""""""""""""""""""""
* This constraint provides a lower bound on the total utilization of installed capacity over a year.
*
*   .. math::
*      \sum_{m,h} \text{ACT}_{n,t,y^V,y,m,h} \geq \text{min_utilization_factor}_{n,t,y^V,y} \cdot \text{CAP}_{n,t,y^V,y}
*      \quad \forall \ t \in T^{\text{INV}}
*
* This constraint is only active if :math:`\text{min_utilization_factor}_{n,t,y^V,y}` is defined.
***
MIN_UTILIZATION_CONSTRAINT(node,inv_tec,vintage,year)$( map_tec_lifetime(node,inv_tec,vintage,year)
        AND min_utilization_factor(node,inv_tec,vintage,year) )..
    SUM((mode,time)$( map_tec_act(node,inv_tec,year,mode,time) ), ACT(node,inv_tec,vintage,year,mode,time) ) =G=
        min_utilization_factor(node,inv_tec,vintage,year) * CAP(node,inv_tec,vintage,year) ;

