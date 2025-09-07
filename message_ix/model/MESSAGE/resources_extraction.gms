***
* Resources extraction module for MESSAGE
* ========================================
* This file contains resource extraction equations and constraints
* Variable and equation declarations remain in model_core.gms
* Extracted from the original model_core.gms for better modularity
***

*----------------------------------------------------------------------------------------------------------------------*
* Equation Definitions
*----------------------------------------------------------------------------------------------------------------------*

***
* .. _equation_extraction_equivalence:
*
* Equation EXTRACTION_EQUIVALENCE
* """""""""""""""""""""""""""""""
*
* This constraint ensures that the quantity of extraction of fossil resources (summed over all grades) :math:`\text{EXT}_{n,c,g,y}`
* equals the quantity of the fossil resource commodity consumed as input to technologies
* at the resource level. Note that the resource level is denoted by :math:`l \in L^{\text{RES}}`.
*
*  .. math::
*     \sum_{g} \text{EXT}_{n,c,g,y} \geq
*     \sum_{\substack{n^L,t,m,h,h^{\text{OD}} \\ y^V \leq y  \\ \ l \in L^{\text{RES}} \subseteq L }}
*         \text{input}_{n^L,t,y^V,y,m,n,c,l,h,h^{\text{OD}}} \cdot \text{ACT}_{n^L,t,m,y,h}
*
* The set :math:`L^{\text{RES}} \subseteq L` denotes all levels for which the detailed representation of resources applies.
***
EXTRACTION_EQUIVALENCE(node,commodity,year)..
    SUM(grade$( map_resource(node,commodity,grade,year) ), EXT(node,commodity,grade,year) )
    =G= SUM((location,tec,vintage,mode,level_resource,time_act,time_od)$( map_tec_act(node,tec,year,mode,time_act)
            AND map_tec_lifetime(node,tec,vintage,year) ),
        input(location,tec,vintage,year,mode,node,commodity,level_resource,time_act,time_od)
        * ACT(location,tec,vintage,year,mode,time_act) ) ;

***
* .. _equation_extraction_bound_up:
*
* Equation EXTRACTION_BOUND_UP  
* """"""""""""""""""""""""""""
*
* Upper bound on resource extraction by grade.
*
*  .. math::
*     \text{EXT}_{n,c,g,y} \leq \text{bound_extraction_up}_{n,c,g,y}
*
***
EXTRACTION_BOUND_UP(node,commodity,grade,year)$( map_resource(node,commodity,grade,year)
        AND is_bound_extraction_up(node,commodity,grade,year) )..
    EXT(node,commodity,grade,year) =L= bound_extraction_up(node,commodity,grade,year) ;

***
* .. _equation_resource_constraint:
*
* Equation RESOURCE_CONSTRAINT
* """"""""""""""""""""""""""""
*
* This constraint ensures that resource extraction does not exceed remaining resources in any period.
*
*  .. math::
*     \text{EXT}_{n,c,g,y} \leq
*     \text{resource_remaining}_{n,c,g,y} \cdot
*         \Big( & \text{resource_volume}_{n,c,g} \\
*               & - \sum_{y' < y} \text{duration_period}_{y'} \cdot \text{EXT}_{n,c,g,y'} \Big)
*
***
RESOURCE_CONSTRAINT(node,commodity,grade,year)$( map_resource(node,commodity,grade,year)
        AND resource_remaining(node,commodity,grade,year) )..
* extraction per year
    EXT(node,commodity,grade,year) =L=
* remaining resources multiplied by remaining-resources-factor
    resource_remaining(node,commodity,grade,year)
    * ( resource_volume(node,commodity,grade)
        - SUM(year2$( year_order(year2) < year_order(year) ),
            duration_period(year2) * EXT(node,commodity,grade,year2) ) ) ;

***
* .. _equation_resource_horizon:
*
* Equation RESOURCE_HORIZON
* """""""""""""""""""""""""
*
* This constraint ensures that resource extraction over the entire model horizon does not exceed available resource volume.
*
*  .. math::
*     \sum_{y} \text{duration_period}_{y} \cdot \text{EXT}_{n,c,g,y} \leq  \text{resource_volume}_{n,c,g}
*
***
RESOURCE_HORIZON(node,commodity,grade)$( SUM(year$map_resource(node,commodity,grade,year), 1 ) )..
    SUM(year, duration_period(year) * EXT(node,commodity,grade,year) ) =L= resource_volume(node,commodity,grade) ;