***
* User-defined relations module for MESSAGE
* ==========================================
* This file contains user-defined relations equations and constraints
* Variable and equation declarations remain in model_core.gms
* Extracted from the original model_core.gms for better modularity
***

*----------------------------------------------------------------------------------------------------------------------*
***
* .. _section_of_generic_relations:
*
* Section of generic relations (linear constraints)
* -------------------------------------------------
*
* This feature is intended for development and testing only - all new features should be implemented
* as specific new mathematical formulations and associated sets & parameters!
*
* Auxiliary variable for left-hand side
* ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
*
* .. _equation_relation_equivalence:
*
* Equation RELATION_EQUIVALENCE
* """""""""""""""""""""""""""""
*   .. math::
*      \text{REL}_{r,n,y} = \sum_{t} \Bigg(
*          & \ \text{relation_new_capacity}_{r,n,y,t} \cdot \text{CAP_NEW}_{n,t,y} \\[4 pt]
*          & + \text{relation_total_capacity}_{r,n,y,t} \cdot \sum_{y^V \leq y} \ \text{CAP}_{n,t,y^V,y} \\
*          & + \sum_{n^L,y',m,h} \ \text{relation_activity}_{r,n,y,n^L,t,y',m} \\
*          & \quad \quad \cdot \Big( \sum_{y^V \leq y'} \text{ACT}_{n^L,t,y^V,y',m,h}
*                              + \text{historical_activity}_{n^L,t,y',m,h} \Big) \Bigg)
*
* The parameter :math:`\text{historical_new_capacity}_{r,n,y}` is not included here, because relations can only be active
* in periods included in the model horizon and there is no "writing" of capacity relation factors across periods.
***

RELATION_EQUIVALENCE(relation,node,year)..
    REL(relation,node,year)
        =E=
    SUM(tec,
        ( relation_new_capacity(relation,node,year,tec) * CAP_NEW(node,tec,year)
          + relation_total_capacity(relation,node,year,tec)
            * SUM(vintage$( map_tec_lifetime(node,tec,vintage,year) ), CAP(node,tec,vintage,year) )
          )$( inv_tec(tec) )
        + SUM((location,year_all2,mode,time)$( map_tec_act(location,tec,year_all2,mode,time) ),
            relation_activity(relation,node,year,location,tec,year_all2,mode)
            * ( SUM(vintage$( map_tec_lifetime(location,tec,vintage,year_all2) ),
                  ACT(location,tec,vintage,year_all2,mode,time) )
                  + historical_activity(location,tec,year_all2,mode,time) )
          )
      ) ;

***
* Upper and lower bounds on user-defined relations
* ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
*
* .. _equation_relation_constraint_up:
*
* Equation RELATION_CONSTRAINT_UP
* """""""""""""""""""""""""""""""
*   .. math::
*      \text{REL}_{r,n,y} \leq \text{relation_upper}_{r,n,y}
***
RELATION_CONSTRAINT_UP(relation,node,year)$( is_relation_upper(relation,node,year) )..
    REL(relation,node,year)
%SLACK_RELATION_BOUND_UP% - SLACK_RELATION_BOUND_UP(relation,node,year)
    =L= relation_upper(relation,node,year) ;

***
* .. _equation_relation_constraint_lo:
*
* Equation RELATION_CONSTRAINT_LO
* """""""""""""""""""""""""""""""
*   .. math::
*      \text{REL}_{r,n,y} \geq \text{relation_lower}_{r,n,y}
***
RELATION_CONSTRAINT_LO(relation,node,year)$( is_relation_lower(relation,node,year) )..
    REL(relation,node,year)
%SLACK_RELATION_BOUND_LO% + SLACK_RELATION_BOUND_LO(relation,node,year)
    =G= relation_lower(relation,node,year) ;

*----------------------------------------------------------------------------------------------------------------------*