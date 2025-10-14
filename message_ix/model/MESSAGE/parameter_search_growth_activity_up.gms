$onEcho > cplex.opt
lpmethod 4
itlim 10
baritlim 500
solutiontype 2
bardisplay 1
$offEcho

Alias(node, node_search);
Alias(tec, tec_search);
Alias(year_all, year_search);
Alias(time, time_search);

Scalar has_search_config;
has_search_config = sum((node,tec,year_all,time,search_config),
                         growth_activity_up_search(node,tec,year_all,time,search_config));

Parameters
    search_lo_param(node,tec,year_all,time)
    search_hi_param(node,tec,year_all,time)
    search_tol_param(node,tec,year_all,time)
    current_value(node,tec,year_all,time)
    constraint_dual(node,tec,year_all,time);

Set
    search_filter(node,tec,year_all,time)
    fixed_dims(node,tec,year_all,time)
    bottleneck(node,tec,year_all,time);

Scalar search_lo, search_hi, search_tol, search_mid, search_best, is_feasible;
Scalar iter_count, param_count, outer_iter, total_solves, phase1_complete;
Scalar max_dual, dual_threshold, converged, global_lo, global_hi, max_phase1_iter;
Set search_iter /iter1*iter100/;
Set outer_iter_set /outer1*outer20/;

if(has_search_config > 0,
    put_utility 'log' /'';
    put_utility 'log' /'========================================';
    put_utility 'log' /'Dual-Guided Parameter Search Detected';
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
        search_tol = search_tol_param(node,tec,year_all,time);
        global_lo = search_lo_param(node,tec,year_all,time);
        global_hi = search_hi_param(node,tec,year_all,time);
        break;
    );
    if(search_tol = 0, search_tol = 0.0001);

    dual_threshold = 0.01;

    put_utility 'log' /'Convergence tolerance: ' search_tol:0:6;
    put_utility 'log' /'Dual threshold: ' dual_threshold:0:4;
    put_utility 'log' /'';

    year(year_all) = no;
    year(year_all)$(model_horizon(year_all)) = yes;

    MESSAGE_LP.optfile = 1;

    current_value(node,tec,year_all,time)$search_filter(node,tec,year_all,time) =
        search_hi_param(node,tec,year_all,time);

    fixed_dims(node,tec,year_all,time) = no;

    outer_iter = 0;
    total_solves = 0;
    converged = 0;
    max_phase1_iter = 100;

    put_utility 'log' /'========================================';
    put_utility 'log' /'Iterative Phase 1 + Phase 2 Search';
    put_utility 'log' /'========================================';
    put_utility 'log' /'';

    loop(outer_iter_set$(not converged),
        outer_iter = outer_iter + 1;
        put_utility 'log' /'';
        put_utility 'log' /'======== Major Iteration ' outer_iter:0:0 ' ========';
        put_utility 'log' /'';

        put_utility 'log' /'--- Phase 1: Global Tightening on Unfixed Dimensions ---';

        phase1_complete = 0;
        iter_count = 0;
        search_lo = global_lo;
        search_hi = global_hi;
        search_best = global_hi;

        loop(search_iter$(iter_count < max_phase1_iter AND not phase1_complete),
            iter_count = iter_count + 1;
            search_mid = (search_lo + search_hi) / 2;

            growth_activity_up(node,tec,year_all,time)$(search_filter(node,tec,year_all,time)
                                                         AND fixed_dims(node,tec,year_all,time)) =
                current_value(node,tec,year_all,time);

            growth_activity_up(node,tec,year_all,time)$(search_filter(node,tec,year_all,time)
                                                         AND not fixed_dims(node,tec,year_all,time)) = search_mid;

            put_utility 'log' /'  Global Iter ' iter_count:0:0 ': testing value=' search_mid:0:6;

        Solve MESSAGE_LP using LP minimizing OBJ;
        total_solves = total_solves + 1;

        is_feasible = (MESSAGE_LP.modelstat = 1) or (MESSAGE_LP.modelstat = 8);

        if((MESSAGE_LP.modelstat = 4) or (MESSAGE_LP.solvestat = 2),
            search_lo = search_mid;
            put_utility 'log' /'    INFEASIBLE - loosening';
        elseif is_feasible,
            constraint_dual(node,tec,year_all,time)$search_filter(node,tec,year_all,time) =
                ACTIVITY_CONSTRAINT_UP.m(node,tec,year_all,time);

            max_dual = smax((node,tec,year_all,time)$(search_filter(node,tec,year_all,time)
                                                       AND not fixed_dims(node,tec,year_all,time)),
                            abs(constraint_dual(node,tec,year_all,time)));

            put_utility 'log' /'    FEASIBLE - max |dual| on unfixed: ' max_dual:0:6;

            if(max_dual > dual_threshold,
                search_best = search_mid;
                current_value(node,tec,year_all,time)$(search_filter(node,tec,year_all,time)
                                                        AND not fixed_dims(node,tec,year_all,time)) = search_mid;
                put_utility 'log' /'    At least one unfixed constraint binding - Phase 1 complete';
                phase1_complete = 1;
            else
                search_hi = search_mid;
                search_best = search_mid;
                put_utility 'log' /'    All duals below threshold - tightening further';
            );
        else
            search_lo = search_mid;
            put_utility 'log' /'    INFEASIBLE - loosening';
        );
        );

        if(not phase1_complete,
            put_utility 'log' /'';
            put_utility 'log' /'Phase 1: No binding constraints found in unfixed dimensions';
            put_utility 'log' /'Converged - all unfixed dimensions at tightest feasible values';
            current_value(node,tec,year_all,time)$(search_filter(node,tec,year_all,time)
                                                    AND not fixed_dims(node,tec,year_all,time)) = search_best;
            converged = 1;
        );

        if(converged,
            break;
        );

        put_utility 'log' /'';
        put_utility 'log' /'Phase 1 complete after ' iter_count:0:0 ' iterations';
        put_utility 'log' /'';

        put_utility 'log' /'--- Phase 2: Tighten Bottleneck ---';

        growth_activity_up(node,tec,year_all,time)$search_filter(node,tec,year_all,time) =
            current_value(node,tec,year_all,time);

        Solve MESSAGE_LP using LP minimizing OBJ;
        total_solves = total_solves + 1;

        is_feasible = (MESSAGE_LP.modelstat = 1) or (MESSAGE_LP.modelstat = 8);

        if(not is_feasible,
            put_utility 'log' /'ERROR: Current point infeasible! (modelstat=' MESSAGE_LP.modelstat:0:0 ')';
            converged = 1;
        else
            constraint_dual(node,tec,year_all,time)$search_filter(node,tec,year_all,time) =
                ACTIVITY_CONSTRAINT_UP.m(node,tec,year_all,time);

            max_dual = smax((node,tec,year_all,time)$(search_filter(node,tec,year_all,time)
                                                       AND not fixed_dims(node,tec,year_all,time)),
                            abs(constraint_dual(node,tec,year_all,time)));

            put_utility 'log' /'Max |dual| value: ' max_dual:0:6;

            if(max_dual < dual_threshold,
                put_utility 'log' /'Converged: all duals below threshold';
                converged = 1;
            else
                bottleneck(node,tec,year_all,time) = no;
                loop((node_search,tec_search,year_search,time_search)$(search_filter(node_search,tec_search,year_search,time_search)
                                                AND not fixed_dims(node_search,tec_search,year_search,time_search)
                                                AND abs(constraint_dual(node_search,tec_search,year_search,time_search)) = max_dual),
                    bottleneck(node_search,tec_search,year_search,time_search) = yes;

                    put_utility 'log' /'Bottleneck: ' node_search.tl:0 ' / ' tec_search.tl:0 ' / ' year_search.tl:0 ' / ' time_search.tl:0
                                      ' (dual=' max_dual:0:6 ', current=' current_value(node_search,tec_search,year_search,time_search):0:6 ')';

                    search_lo = search_lo_param(node_search,tec_search,year_search,time_search);
                    search_hi = current_value(node_search,tec_search,year_search,time_search);
                    search_best = search_hi;
                    iter_count = 0;

                    loop(search_iter$(search_hi - search_lo > search_tol),
                        iter_count = iter_count + 1;
                        search_mid = (search_lo + search_hi) / 2;

                        growth_activity_up(node_search,tec_search,year_search,time_search) = search_mid;

                        Solve MESSAGE_LP using LP minimizing OBJ;
                        total_solves = total_solves + 1;

                        is_feasible = (MESSAGE_LP.modelstat = 1) or (MESSAGE_LP.modelstat = 8);

                        if((MESSAGE_LP.modelstat = 4) or (MESSAGE_LP.solvestat = 2),
                            search_lo = search_mid;
                            put_utility 'log' /'    Iter ' iter_count:0:0 ': value=' search_mid:0:6 ' INFEASIBLE';
                        elseif is_feasible,
                            search_hi = search_mid;
                            search_best = search_mid;
                            put_utility 'log' /'    Iter ' iter_count:0:0 ': value=' search_mid:0:6 ' FEASIBLE';
                        else
                            search_lo = search_mid;
                            put_utility 'log' /'    Iter ' iter_count:0:0 ': value=' search_mid:0:6 ' INFEASIBLE';
                        );
                    );

                    current_value(node_search,tec_search,year_search,time_search) = search_best;
                    fixed_dims(node_search,tec_search,year_search,time_search) = yes;

                    put_utility 'log' /'  Fixed at: ' search_best:0:6 ' (' iter_count:0:0 ' iterations)';

                    break;
                );
            );
        );
    );

    growth_activity_up(node,tec,year_all,time)$search_filter(node,tec,year_all,time) =
        current_value(node,tec,year_all,time);

    put_utility 'log' /'';
    put_utility 'log' /'========================================';
    put_utility 'log' /'Parameter Search Complete';
    put_utility 'log' /'========================================';
    put_utility 'log' /'Total outer iterations (Phase 2): ' outer_iter:0:0;
    put_utility 'log' /'Total model solves: ' total_solves:0:0;
    put_utility 'log' /'';
    put_utility 'log' /'Final parameter values:';

    loop((node,tec,year_all,time)$search_filter(node,tec,year_all,time),
        put_utility 'log' /'  ' node.tl:0 ' / ' tec.tl:0 ' / ' year_all.tl:0 ' / ' time.tl:0
                          ' = ' current_value(node,tec,year_all,time):0:6;
    );

    put_utility 'log' /'========================================';
    put_utility 'log' /'';

else
    put_utility 'log' /'No binary search configuration found - skipping parameter search';
);
