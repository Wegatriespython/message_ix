***
* Renewables module for MESSAGE
* ==============================
* This file contains renewables-related equations and constraints
* Variable and equation declarations remain in model_core.gms
* Extracted from the original model_core.gms for better modularity
***

*----------------------------------------------------------------------------------------------------------------------*
* Equation Definitions
*----------------------------------------------------------------------------------------------------------------------*

***
* .. _equation_renewables_equivalence:
*
* Equation RENEWABLES_EQUIVALENCE
* """""""""""""""""""""""""""""""
*
* This constraint defines the renewables extraction as input of renewables into technologies.
*
*  .. math::
*     \sum_{g} \text{REN}_{n,t,c,g,y,h} = 
*     \sum_{\substack{n,t,m,l,h,h^{\text{OD}} \\ y^V \leq y  \\ \ l \in L^{\text{REN}} \subseteq L }}
*         \text{input}_{n^L,t,y^V,y,m,n,c,l,h,h^{\text{OD}}} \cdot \text{ACT}_{n^L,t,m,y,h}
*
* The set :math:`L^{\text{REN}} \subseteq L` denotes all levels for which the detailed representation of renewables applies.
***
RENEWABLES_EQUIVALENCE(node,renewable_tec,commodity,year,time)$(
        map_tec(node,renewable_tec,year) AND map_ren_com(node,renewable_tec,commodity,year) )..
    SUM(grade$( map_ren_grade(node,commodity,grade,year) ), REN(node,renewable_tec,commodity,grade,year,time) )
    =E= SUM((location,vintage,mode,level_renewable,time_act)$(
                 map_tec_act(node,renewable_tec,year,mode,time_act)
                 AND map_tec_lifetime(node,renewable_tec,vintage,year) ),
        input(location,renewable_tec,vintage,year,mode,node,commodity,level_renewable,time_act,time)
        * ACT(location,renewable_tec,vintage,year,mode,time_act) ) ;

***
* .. _equation_renewables_potential_constraint:
*
* Equation RENEWABLES_POTENTIAL_CONSTRAINT
* """"""""""""""""""""""""""""""""""""""""
*
* This constraint ensures that the use of renewables (per grade) does not exceed the potential.
*
*  .. math::
*     \sum_{\substack{t,h \\ \ t \in T^{R} \subseteq t }} \text{REN}_{n,t,c,g,y,h}
*         \leq \sum_{\substack{l \\ l \in L^{R} \subseteq L }} \text{renewable_potential}_{n,c,g,l,y}
*
***
RENEWABLES_POTENTIAL_CONSTRAINT(node,commodity,grade,year)$( map_ren_grade(node,commodity,grade,year) )..
    SUM((renewable_tec,time)$( map_ren_com(node,renewable_tec,commodity,year) ),
        REN(node,renewable_tec,commodity,grade,year,time) )
    =L= SUM(level_renewable, renewable_potential(node,commodity,grade,level_renewable,year) ) ;

***
* .. _equation_renewables_capacity_requirement:
*
* Equation RENEWABLES_CAPACITY_REQUIREMENT
* """"""""""""""""""""""""""""""""""""""""
*
* Lower bound on required overcapacity when using lower grade renewables potentials. This constraint ensures
* that there is sufficient installed capacity to support the utilization of renewables.
*
*  .. math::
*     \sum_{y^V, h} & \text{CAP}_{n,t,y^V,y} \cdot \text{operation_factor}_{n,t,y^V,y} \cdot \text{capacity_factor}_{n,t,y^V,y,h} \\
*        & \quad \geq \sum_{g,h,l} \frac{1}{\text{renewable_capacity_factor}_{n,c,g,l,y}} \cdot \text{REN}_{n,t,c,g,y,h}
*
* This constraint is only active if :math:`\text{renewable_capacity_factor}_{n,c,g,l,y}` is defined.
***
RENEWABLES_CAPACITY_REQUIREMENT(node,inv_tec,commodity,year)$(
        SUM( (vintage,mode,time,grade,level_renewable),
            map_tec_lifetime(node,inv_tec,vintage,year) AND map_tec_act(node,inv_tec,year,mode,time)
            AND map_ren_com(node,inv_tec,commodity,year)
            AND renewable_capacity_factor(node,commodity,grade,level_renewable,year) > 0 ) )..
    SUM( (vintage,time)$map_ren_com(node,inv_tec,commodity,year),
        CAP(node,inv_tec,vintage,year)
        * operation_factor(node,inv_tec,vintage,year)
        * capacity_factor(node,inv_tec,vintage,year,time) )
    =G= SUM((grade,time,level_renewable)$(renewable_capacity_factor(node,commodity,grade,level_renewable,year) > 0),
            REN(node,inv_tec,commodity,grade,year,time)
                 / renewable_capacity_factor(node,commodity,grade,level_renewable,year)) ;