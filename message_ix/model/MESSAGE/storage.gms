***
* Storage module for MESSAGE
* ===========================
* This file contains storage-related equations and constraints
* Variable and equation declarations remain in model_core.gms
* Extracted from the original model_core.gms for better modularity
***

*----------------------------------------------------------------------------------------------------------------------*
***
* .. _gams-storage:
*
* Storage section
* ---------------
*
* MESSAGEix offers a set of equations to represent a wide range of storage solutions flexibly.
* Storage solutions are modeled as "technologies" that can be used to store a "commodity" (e.g., water, heat, electricity, etc.)
* and shift it over sub-annual time slices within one model period. The storage solution presented here has three
* distinct parts: (i) Charger: a technology for charging a commodity to the storage container,
* for example, a pump in a pumped hydropower storage (PHS) plant. (ii) Discharger: a technology
* to convert the stored commodity to the output commodity, e.g., a turbine in PHS.
* (iii) Storage container: a device for storing a commodity over time, such as a water reservoir in PHS.
* If desired, the user can combine charger and discharger parts into one technology, using two different "modes" of operation
* for that technology like turbo-machinery in PHS. This way the capacity related information, like investment cost, lifetime, capacity factor, etc.,
* will be defined only for one technology (i.e., charger-discharger), as opposed to modeling these two parts separately.
*
* .. figure:: ../../_static/storage.png
*
* Storage equations
* ^^^^^^^^^^^^^^^^^
* The content of storage device depends on three factors: charge or discharge in
* one time slice (represented by `Equation STORAGE_CHANGE`_), linked to the state of charge in the previous
* time slice and storage losses between these two consecutive time slices (represented by `Equation STORAGE_BALANCE`_).
* Moreover, the storage device can be optionally filled with an initial value as percentage of its capacity (see more details under `Equation STORAGE_BALANCE_INIT`_).
* Another option is to link a commodity for maintaining the operation of storage device over time (see `Equation STORAGE_INPUT`_).
*
* .. _equation_storage_change:
*
* Equation STORAGE_CHANGE
* """""""""""""""""""""""
* This equation shows the change in the content of the storage container in each
* sub-annual time slice. This change is based on the activity of charger and discharger
* technologies connected to that storage container. The notation :math:`S^{\text{storage}}`
* represents the mapping set `map_tec_storage` denoting charger-discharger
* technologies connected to a specific storage container in a specific node and
* storage level. Where:
*
* - :math:`t^{C}` is a charging technology and :math:`t^{D}` is the corresponding discharger.
* - :math:`h-1` is the time slice prior to :math:`h`.
* - :math:`l^{T}` is `lvl_temporal`, i.e., the temporal level at which storage is operating
* - :math:`m^{S}` is `mode` of operation for storage container technology

*   .. math::
*      \text{STORAGE_CHARGE}_{n,t,m^s,l,c,y,h} =
*          \sum_{\substack{n^L,m,h-1 \\ y^V \leq y, (n,t^C,t,l,y) \sim S^{\text{storage}}}} \text{output}_{n^L,t^C,y^V,y,m,n,c,l,h-1,h}
*             \cdot & \text{ACT}_{n^L,t^C,y^V,y,m,h-1} \\
*          - \sum_{\substack{n^L,m,c,h-1 \\ y^V \leq y, (n,t^D,t,l,y) \sim S^{\text{storage}}}} \text{input}_{n^L,t^D,y^V,y,m,n,c,l,h-1,h}
*              \cdot \text{ACT}_{n^L,t^D,y^V,y,m,h-1} \quad \forall \ t \in T^{\text{STOR}}, & \forall \ l \in L^{\text{STOR}}
***
STORAGE_CHANGE(node,storage_tec,mode,level_storage,commodity,year,time)$sum(
               (tec,mode2,lvl_temporal), map_tec_storage(node,tec,mode2,storage_tec,mode,level_storage,commodity,lvl_temporal) ) ..
* change in the content of storage in the examined time slice
    STORAGE_CHARGE(node,storage_tec,mode,level_storage,commodity,year,time) =E=
* increase in the content of storage due to the activity of charging technologies
        SUM( (location,vintage,tec,mode2,time2,time3,lvl_temporal)$(
        map_tec_lifetime(node,tec,vintage,year) AND map_temporal_hierarchy(lvl_temporal,time,time3
                )$map_tec_storage(node,tec,mode2,storage_tec,mode,level_storage,commodity,lvl_temporal) ),
            output(location,tec,vintage,year,mode2,node,commodity,level_storage,time2,time)
            * duration_time_rel(time,time2) * ACT(location,tec,vintage,year,mode2,time2) )
* decrease in the content of storage due to the activity of discharging technologies
        - SUM( (location,vintage,tec,mode2,time2,time3,lvl_temporal)$(
        map_tec_lifetime(node,tec,vintage,year) AND map_temporal_hierarchy(lvl_temporal,time,time3
                )$map_tec_storage(node,tec,mode2,storage_tec,mode,level_storage,commodity,lvl_temporal) ),
            input(location,tec,vintage,year,mode2,node,commodity,level_storage,time2,time)
            * duration_time_rel(time,time2) * ACT(location,tec,vintage,year,mode2,time2) );

***
* .. _equation_storage_balance:
*
* Equation STORAGE_BALANCE
* """"""""""""""""""""""""
*
* This equation ensures the commodity balance of storage technologies, where the commodity is shifted between sub-annual
* time slices within a model period. If the state of charge of storage is set exogenously in one time slice through
* :math:`\storageinitial_{ntlcyh}`, the content from the previous time slice is not carried over to this time slice.
*
* .. math::
*    \STORAGE_{ntmlcyh} =\ & \STORAGECHARGE_{ntmlcyh} \\
*    & + \STORAGE_{ntmlcy(h-1)} \cdot (1 - \storageselfdischarge_{ntmly(h-1)}) \\
*    \forall\ & t \in T^{\text{STOR}}, l \in L^{\text{STOR}}, \storageinitial_{ntmlcyh} = 0
***
STORAGE_BALANCE(node,storage_tec,mode,level,commodity,year,time2,lvl_temporal)$ (
    SUM((tec,mode2), map_tec_storage(node,tec,mode2,storage_tec,mode,level,commodity,lvl_temporal) )
*    AND NOT storage_initial(node,storage_tec,mode,level,commodity,year,time2)
)..
* Showing the the state of charge of storage at each time slice
    STORAGE(node,storage_tec,mode,level,commodity,year,time2) =E=
* change in the content of storage in the examined time slice
    + STORAGE_CHARGE(node,storage_tec,mode,level,commodity,year,time2)
* storage content in the previous subannual time slice
    + SUM(time$map_time_period(year,lvl_temporal,time,time2),
        STORAGE(node,storage_tec,mode,level,commodity,year,time)
* considering storage self-discharge losses due to keeping the storage media between two subannual time slices
        * (1 - storage_self_discharge(node,storage_tec,mode,level,commodity,year,time) ) ) ;

***
* .. _equation_storage_balance_init:
*
* Equation STORAGE_BALANCE_INIT
* """""""""""""""""""""""""""""
*
* Where :math:`\storageinitial_{ntlyh}` has a non-zero value, this equation ensures that the amount of commodity stored
* at the end of a sub-annual time slice is equal or greater than the initialized content of storage in the following time slice.
* The values in parameter :math:`\storageinitial_{ntlyh}` are percentages showing
* a fraction of installed capacity of storage device (container) that can be filled initially.
*
* .. math::
*    \STORAGE_{ntmlcy(h-1)} \geq &  \storageinitial_{ntmlcyh} \cdot \text{duration_time}_{h} \cdot \text{capacity_factor}_{n,t,y^V,y,h} \cdot \text{CAP}_{n,t,y^V,y}  \\
*    \quad \forall \ t \ \in \ T^{\text{INV}}, \forall\ & \storageinitial_{ntmlcyh} \neq 0
***

STORAGE_BALANCE_INIT(node,storage_tec,mode,level,commodity,year,time,time2)$ (
    SUM((tec,mode2,lvl_temporal), map_tec_storage(node,tec,mode2,storage_tec,mode,level,commodity,lvl_temporal)
        AND map_time_period(year,lvl_temporal,time,time2) )
    AND storage_initial(node,storage_tec,mode,level,commodity,year,time2) )..
* Showing the state of charge of storage at a time slice prior to a time slice that has initial storage content
    STORAGE(node,storage_tec,mode,level,commodity,year,time) =G=
* Initial content of storage in the examined time slice as a percentage multiplier in available capacity of storage
        storage_initial(node,storage_tec,mode,level,commodity,year,time2)
        * SUM(vintage$( map_tec_lifetime(node,storage_tec,vintage,year) ), capacity_factor(node,storage_tec,vintage,year,time2)
             * CAP(node,storage_tec,vintage,year) / duration_time(time2)  )
;
***
* .. _equation_storage_input:
*
* Equation STORAGE_INPUT
* """"""""""""""""""""""""""""
*
* This equation links :math:`\STORAGE` to an input commodity to maintain the activity (:math:`\ACT`) of each active storage *container* technology
* :math:`t`. This input commodity is distinct from the stored commodity. For example, in a pumped hydro storage solution, a user can link heating
* for keeping the stored water warm. In this case, the input commodity is not a function of charge or discharge, but the amount of stored media in the container over time.
* Therefore, the input commodity specified here is distinct from the one stored and discharged by *(dis)charge* technologies :math:`t^C,t^D` appearing in
* :ref:`equation_storage_change`.
*
* .. math::
*    \STORAGE_{ntmlcy^Ah} =\ & \sum_{\{n^Ly^Vh^O \vert K\}} \durationtimerel_{hh^O} \cdot \ACT_{n^Lty^Vy^Amh^O} \\
*    \forall\ & n,t,l,c,m,y^A,h \vert t \in T^{\text{STOR}} \\
*    K:\ & \\text{input}_{n^Lty^Vy^Amn^Oclhh^O} \neq 0
*
***

STORAGE_INPUT(node,storage_tec,level,commodity,level_storage,commodity2,mode,year,time)$
    ( map_time_commodity_storage(node,storage_tec,level,commodity,mode,year,time) AND
      SUM( (tec,mode2,lvl_temporal), map_tec_storage(node,tec,mode2,storage_tec,mode,level_storage,commodity2,lvl_temporal) ) ) ..
* Connecting an input commodity to maintain the operation of storage container over time (optional)
  STORAGE(node,storage_tec,mode,level_storage,commodity2,year,time) =E=
        SUM( (location,vintage,time2)$(map_tec_lifetime(node,storage_tec,vintage,year)$(
              input(location,storage_tec,vintage,year,mode,node,commodity,level,time,time2) ) ),
              duration_time_rel(time,time2) * ACT(location,storage_tec,vintage,year,mode,time) )
;

*----------------------------------------------------------------------------------------------------------------------*