***
* Binary search for minimum feasible growth_activity_up parameter value
* ========================================================================
*
* This file implements a binary search algorithm to find the minimum (tightest)
* value of growth_activity_up that maintains model feasibility.
*
* Usage:
*   1. Edit the USER CONFIGURATION section below to specify:
*      - Technology filter (which technology to adjust)
*      - Node filter (optional, which node)
*      - Time filter (optional, which time slice)
*      - Search range (multiplier bounds)
*   2. Include this file in MESSAGE_run.gms after data load:
*      $INCLUDE MESSAGE/parameter_search_growth_activity_up.gms
*
* The search operates on multipliers:
*   - 1.0 = original parameter value
*   - 0.5 = 50% of original value (tighter constraint)
*   - 2.0 = 200% of original value (looser constraint)
*
* For upper bound parameters like growth_activity_up, the search finds the
* minimum multiplier (tightest constraint) that maintains feasibility.
***

*----------------------------------------------------------------------------------------------------------------------*
* USER CONFIGURATION
*----------------------------------------------------------------------------------------------------------------------*

* Technology filter - specify exact technology name
* Example: "extract_surfacewater" or "coal_ppl"
* Leave empty "" to search all technologies
$SETGLOBAL FILTER_TEC "coal_ppl"

* Node filter (optional) - specify exact node name
* Leave empty "" to include all nodes
$SETGLOBAL FILTER_NODE ""

* Time filter (optional) - specify exact time slice name
* Leave empty "" to include all time slices
$SETGLOBAL FILTER_TIME ""

* Search range: multipliers to test
* The algorithm searches for values between search_lo and search_hi
Scalar
    search_lo       'lower bound multiplier (tighter constraint)' /0.5/
    search_hi       'upper bound multiplier (looser constraint)' /5.0/
    search_tol      'convergence tolerance (stop when range < tol)' /0.01/
;

*----------------------------------------------------------------------------------------------------------------------*
* SEARCH ALGORITHM - DO NOT EDIT BELOW THIS LINE
*----------------------------------------------------------------------------------------------------------------------*

Set search_iter 'iteration counter set' /iter1*iter30/;

Scalar
    search_mid      'midpoint of current iteration'
    search_best     'best feasible multiplier found'
    is_feasible     'flag: was last solve feasible (1=yes, 0=no)'
    iter_count      'iteration counter'
;

* Define filter sets based on user configuration
Set filter_tec(tec) 'technologies to search';
Set filter_node(node) 'nodes to search';
Set filter_time(time) 'time slices to search';

$IFTHEN.tec "%FILTER_TEC%"==""
    filter_tec(tec) = yes;
$ELSE.tec
    filter_tec("%FILTER_TEC%") = yes;
$ENDIF.tec

$IFTHEN.node "%FILTER_NODE%"==""
    filter_node(node) = yes;
$ELSE.node
    filter_node("%FILTER_NODE%") = yes;
$ENDIF.node

$IFTHEN.time "%FILTER_TIME%"==""
    filter_time(time) = yes;
$ELSE.time
    filter_time("%FILTER_TIME%") = yes;
$ENDIF.time

* Store original parameter values for the filtered subset
Parameter growth_activity_up_original(node,tec,year_all,time);

growth_activity_up_original(node,tec,year_all,time) = growth_activity_up(node,tec,year_all,time);

* Count how many parameter entries match the filter criteria
Scalar param_count 'number of parameters matching filter';
param_count = sum((node,tec,year_all,time)$(
    filter_tec(tec) AND filter_node(node) AND filter_time(time)
    AND growth_activity_up_original(node,tec,year_all,time)
), 1);

* Display search initialization information
put_utility 'log' /'';
put_utility 'log' /'========================================';
put_utility 'log' /'Binary Search: growth_activity_up';
put_utility 'log' /'========================================';
$IFTHEN.tec NOT "%FILTER_TEC%"==""
put_utility 'log' /'Technology filter: %FILTER_TEC%';
$ENDIF.tec
$IFTHEN.node NOT "%FILTER_NODE%"==""
put_utility 'log' /'Node filter: %FILTER_NODE%';
$ENDIF.node
$IFTHEN.time NOT "%FILTER_TIME%"==""
put_utility 'log' /'Time filter: %FILTER_TIME%';
$ENDIF.time
put_utility 'log' /'Parameters matching filter: ' param_count:0:0;
put_utility 'log' /'Search range: [' search_lo:0:3 ', ' search_hi:0:3 ']';
put_utility 'log' /'Convergence tolerance: ' search_tol:0:4;
put_utility 'log' /'';

* Initialize search
iter_count = 0;
search_best = search_hi;

* Configure year set to match final solve (from model_solve.gms lines 20-22)
year(year_all) = no ;
year(year_all)$( model_horizon(year_all) ) = yes ;

* Configure CPLEX for fast failure detection
$onEcho > cplex.opt
lpmethod 4
itlim 10
baritlim 500
solutiontype 2
bardisplay 1
$offEcho

MESSAGE_LP.optfile = 1;

* Binary search loop
loop(search_iter$(search_hi - search_lo > search_tol),
    iter_count = iter_count + 1;
    search_mid = (search_lo + search_hi) / 2;

    growth_activity_up(node,tec,year_all,time)$(
        filter_tec(tec) AND filter_node(node) AND filter_time(time)
        AND growth_activity_up_original(node,tec,year_all,time)
    ) = growth_activity_up_original(node,tec,year_all,time) * search_mid;

    Solve MESSAGE_LP using LP minimizing OBJ;

    is_feasible = (MESSAGE_LP.modelstat = 1) or (MESSAGE_LP.modelstat = 8);

    if((MESSAGE_LP.modelstat = 4) or (MESSAGE_LP.solvestat = 2),
        search_lo = search_mid;
        put_utility 'log' /'  Iter ' iter_count:0:0 ': multiplier=' search_mid:0:4 ' INFEASIBLE (modelstat=' MESSAGE_LP.modelstat:0:0 ' solvestat=' MESSAGE_LP.solvestat:0:0 ')';
    elseif is_feasible,
        search_hi = search_mid;
        search_best = search_mid;
        put_utility 'log' /'  Iter ' iter_count:0:0 ': multiplier=' search_mid:0:4 ' FEASIBLE - tightening bound';
    else
        search_lo = search_mid;
        put_utility 'log' /'  Iter ' iter_count:0:0 ': multiplier=' search_mid:0:4 ' INFEASIBLE - loosening bound';
    );
);

* Restore to best feasible value found
growth_activity_up(node,tec,year_all,time)$(
    filter_tec(tec) AND filter_node(node) AND filter_time(time)
    AND growth_activity_up_original(node,tec,year_all,time)
) = growth_activity_up_original(node,tec,year_all,time) * search_best;

* Display results
put_utility 'log' /'';
put_utility 'log' /'========================================';
put_utility 'log' /'Binary Search Complete';
put_utility 'log' /'========================================';
put_utility 'log' /'Best feasible multiplier: ' search_best:0:6;
put_utility 'log' /'Iterations completed: ' iter_count:0:0;
put_utility 'log' /'Final search range: [' search_lo:0:6 ', ' search_hi:0:6 ']';
put_utility 'log' /'========================================';
put_utility 'log' /'';

display "Binary search complete", search_best, iter_count;

* Display the modified parameter values for verification
Parameter growth_activity_up_modified(node,tec,year_all,time);

growth_activity_up_modified(node,tec,year_all,time)$(
    filter_tec(tec) AND filter_node(node) AND filter_time(time)
    AND growth_activity_up(node,tec,year_all,time)
) = growth_activity_up(node,tec,year_all,time);

display "Original values:", growth_activity_up_original;
display "Modified values:", growth_activity_up_modified;

***
* End of parameter search
***
