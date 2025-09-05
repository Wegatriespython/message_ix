***
* HHI Post-Solve Diagnostics
* ==========================
* This file contains diagnostic checks for HHI constraints after model solve
* Used to verify that HHI equations were properly generated and solved
***

* Count DEF_Y_TEC equations (technology output definitions)
n_def = SUM((node,commodity,level,y_hhi,time,tec)$DEF_Y_TEC.M(node,commodity,level,y_hhi,time,tec), 1); 
display "Number of DEF_Y_TEC equations generated:", n_def;

* Count ROTATED_SOC_CONSTRAINT equations (second-order cone constraints)
n_soc = SUM((node,commodity,level,y_hhi,time,tec)$ROTATED_SOC_CONSTRAINT.M(node,commodity,level,y_hhi,time,tec), 1); 
display "Number of ROTATED_SOC_CONSTRAINT equations generated:", n_soc;

* Count HHI_CAP equations (HHI limit constraints)
n_cap = SUM((node,commodity,level,y_hhi,time)$HHI_CAP.M(node,commodity,level,y_hhi,time), 1); 
display "Number of HHI_CAP equations generated:", n_cap;

* Display HHI constraint shadow prices (if any are binding)
display "HHI_CAP marginal values (shadow prices):", HHI_CAP.M;

* Display technology shares under HHI constraints
display "Y_TEC levels (technology outputs):", Y_TEC.L;
display "T_GROUP levels (total group outputs):", T_GROUP.L;