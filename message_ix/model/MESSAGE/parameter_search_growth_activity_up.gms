$onEcho > cplex.opt
lpmethod 4
itlim 10
baritlim 500
solutiontype 2
bardisplay 1
$offEcho

Scalar has_search_config;
has_search_config = sum((node,tec,year_all,time,search_config),
                         growth_activity_up_search(node,tec,year_all,time,search_config));

Parameters
    search_lo_param(node,tec,year_all,time)
    search_hi_param(node,tec,year_all,time)
    search_tol_param(node,tec,year_all,time)
    growth_activity_up_original(node,tec,year_all,time);

Set search_filter(node,tec,year_all,time);

Scalar search_lo, search_hi, search_tol, search_mid, search_best, is_feasible, iter_count, param_count;
Set search_iter /iter1*iter30/;

if(has_search_config > 0,
    put_utility 'log' /'';
    put_utility 'log' /'========================================';
    put_utility 'log' /'Binary Search Configuration Detected';
    put_utility 'log' /'========================================';

    search_lo_param(node,tec,year_all,time) =
        growth_activity_up_search(node,tec,year_all,time,'lo');
    search_hi_param(node,tec,year_all,time) =
        growth_activity_up_search(node,tec,year_all,time,'hi');
    search_tol_param(node,tec,year_all,time) =
        growth_activity_up_search(node,tec,year_all,time,'tol');

    search_filter(node,tec,year_all,time) =
        (search_lo_param(node,tec,year_all,time) > 0) AND
        (search_hi_param(node,tec,year_all,time) > 0);

    param_count = sum((node,tec,year_all,time)$search_filter(node,tec,year_all,time), 1);
    put_utility 'log' /'Parameters to search: ' param_count:0:0;

    loop((node,tec,year_all,time)$search_filter(node,tec,year_all,time),
        put_utility 'log' /'  ' node.tl:0 ' / ' tec.tl:0 ' / ' year_all.tl:0 ' / ' time.tl:0
                          ' : [' search_lo_param(node,tec,year_all,time):0:3
                          ', ' search_hi_param(node,tec,year_all,time):0:3 ']';
    );

    loop((node,tec,year_all,time)$search_filter(node,tec,year_all,time),
        search_lo = search_lo_param(node,tec,year_all,time);
        search_hi = search_hi_param(node,tec,year_all,time);
        search_tol = search_tol_param(node,tec,year_all,time);
        break;
    );

    if(search_tol = 0, search_tol = 0.01);

    put_utility 'log' /'Search range: [' search_lo:0:3 ', ' search_hi:0:3 ']';
    put_utility 'log' /'Convergence tolerance: ' search_tol:0:4;
    put_utility 'log' /'';

    growth_activity_up_original(node,tec,year_all,time) = growth_activity_up(node,tec,year_all,time);

    iter_count = 0;
    search_best = search_hi;

    year(year_all) = no;
    year(year_all)$(model_horizon(year_all)) = yes;

    MESSAGE_LP.optfile = 1;

    loop(search_iter$(search_hi - search_lo > search_tol),
        iter_count = iter_count + 1;
        search_mid = (search_lo + search_hi) / 2;

        growth_activity_up(node,tec,year_all,time)$(
            search_filter(node,tec,year_all,time)
        ) = search_mid;

        Solve MESSAGE_LP using LP minimizing OBJ;

        is_feasible = (MESSAGE_LP.modelstat = 1) or (MESSAGE_LP.modelstat = 8);

        if((MESSAGE_LP.modelstat = 4) or (MESSAGE_LP.solvestat = 2),
            search_lo = search_mid;
            put_utility 'log' /'  Iter ' iter_count:0:0 ': value=' search_mid:0:4 ' INFEASIBLE (modelstat=' MESSAGE_LP.modelstat:0:0 ' solvestat=' MESSAGE_LP.solvestat:0:0 ')';
        elseif is_feasible,
            search_hi = search_mid;
            search_best = search_mid;
            put_utility 'log' /'  Iter ' iter_count:0:0 ': value=' search_mid:0:4 ' FEASIBLE - tightening bound';
        else
            search_lo = search_mid;
            put_utility 'log' /'  Iter ' iter_count:0:0 ': value=' search_mid:0:4 ' INFEASIBLE - loosening bound';
        );
    );

    growth_activity_up(node,tec,year_all,time)$(
        search_filter(node,tec,year_all,time)
    ) = search_best;

    put_utility 'log' /'';
    put_utility 'log' /'========================================';
    put_utility 'log' /'Binary Search Complete';
    put_utility 'log' /'========================================';
    put_utility 'log' /'Best feasible value: ' search_best:0:6;
    put_utility 'log' /'Iterations completed: ' iter_count:0:0;
    put_utility 'log' /'Final search range: [' search_lo:0:6 ', ' search_hi:0:6 ']';
    put_utility 'log' /'========================================';
    put_utility 'log' /'';

    display "Binary search complete", search_best, iter_count;

else
    put_utility 'log' /'No binary search configuration found - skipping parameter search';
);
