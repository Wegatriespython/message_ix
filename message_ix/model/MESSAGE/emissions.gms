***
* Emissions module for MESSAGE
* =============================
* This file contains emissions-related equations and constraints
* Variable and equation declarations remain in model_core.gms
* Extracted from the original model_core.gms for better modularity
***

*----------------------------------------------------------------------------------------------------------------------*
***
* .. _section_emission:
*
* Emission section
* ----------------
*
* Auxiliary variable for aggregate emissions
* ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
*
* .. _equation_emission_equivalence:
*
* Equation EMISSION_EQUIVALENCE
* """""""""""""""""""""""""""""
* This constraint simplifies the notation of emissions aggregated over different technology types
* and the land-use model emulator. The formulation includes emissions from all sub-nodes :math:`n^L` of :math:`n`.
*
*   .. math::
*      \text{EMISS}_{n,e,\widehat{t},y} =
*          \sum_{n^L \in N(n)} \Bigg(
*              \sum_{t \in T(\widehat{t}),y^V \leq y,m,h }
*                  \text{emission_factor}_{n^L,t,y^V,y,m,e} \cdot \text{ACT}_{n^L,t,y^V,y,m,h} \\
*              + \sum_{s} \ \text{land_emission}_{n^L,s,y,e} \cdot \text{LAND}_{n^L,s,y}
*                   \text{ if } \widehat{t} \in \widehat{T}^{LAND} \Bigg)
*
* .. versionchanged:: v3.11.0
*
*    ``type_tec`` elements that appear in either of the :ref:`mapping sets <section_maps_def>`
*    ``map_shares_commodity_share`` or ``map_shares_commodity_total`` are excluded from this equation,
*    and thus also from the domain of the ``EMISS`` :ref:`variable <section_decision_variable_def>`.
***
EMISSION_EQUIVALENCE(node,emission,type_tec,year)$(
  NOT type_tec_share(type_tec) AND NOT type_tec_total(type_tec)
)..
    EMISS(node,emission,type_tec,year)
    =E=
    SUM(location$( map_node(node,location) ),
* emissions from technology activity
        SUM((tec,vintage,mode,time)$( cat_tec(type_tec,tec)
            AND map_tec_act(location,tec,year,mode,time) AND map_tec_lifetime(location,tec,vintage,year) ),
        emission_factor(location,tec,vintage,year,mode,emission) * ACT(location,tec,vintage,year,mode,time) )
* emissions from land use if 'type_tec' is included in the dynamic set 'type_tec_land'
        + SUM(land_scenario$( type_tec_land(type_tec) ),
            land_emission(location,land_scenario,year,emission) * LAND(location,land_scenario,year) )
      ) ;

***
* Bound on emissions
* ^^^^^^^^^^^^^^^^^^
*
* .. _emission_constraint:
*
* Equation EMISSION_CONSTRAINT
* """"""""""""""""""""""""""""
* This constraint enforces upper bounds on emissions (by emission type). For all bounds that include multiple periods,
* the parameter :math:`\text{bound_emission}_{n,\widehat{e},\widehat{t},\widehat{y}}` is scaled to represent average annual
* emissions over all years included in the year-set :math:`\widehat{y}`.
*
* The formulation includes historical emissions and allows to model constraints ranging over both the model horizon
* and historical periods.
*
*   .. math::
*      \frac{
*          \sum_{y' \in Y(\widehat{y}), e \in E(\widehat{e})}
*              \begin{array}{l}
*                  \text{duration_period}_{y'} \cdot \text{emission_scaling}_{\widehat{e},e} \cdot \\
*                  \Big( \text{EMISS}_{n,e,\widehat{t},y'} + \sum_{m} \text{historical_emission}_{n,e,\widehat{t},y'} \Big)
*              \end{array}
*          }
*        { \sum_{y' \in Y(\widehat{y})} \text{duration_period}_{y'} }
*      \leq \text{bound_emission}_{n,\widehat{e},\widehat{t},\widehat{y}}
*
***
EMISSION_CONSTRAINT(node,type_emission,type_tec,type_year)$is_bound_emission(node,type_emission,type_tec,type_year)..
    SUM( (year_all2,emission)$( cat_year(type_year,year_all2) AND cat_emission(type_emission,emission) ),
        duration_period(year_all2) * emission_scaling(type_emission,emission) *
            ( EMISS(node,emission,type_tec,year_all2)$( year(year_all2) )
                + historical_emission(node,emission,type_tec,year_all2) )
      )
    / SUM(year_all2$( cat_year(type_year,year_all2) ), duration_period(year_all2) )
    =L= bound_emission(node,type_emission,type_tec,type_year) ;

*----------------------------------------------------------------------------------------------------------------------*