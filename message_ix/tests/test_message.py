import re
from collections import defaultdict
from typing import TYPE_CHECKING

import ixmp
import pytest
from ixmp.backend.jdbc import JDBCBackend

from message_ix.message import MESSAGE

if TYPE_CHECKING:
    from ixmp import Platform


pytestmark = pytest.mark.ixmp4_209


class TestMESSAGE:
    """Tests of :class:`.MESSAGE`."""

    def test_initialize(self, caplog, test_mp: "Platform") -> None:
        # Expected numbers of items by type
        exp = defaultdict(list)
        for name, spec in MESSAGE.items.items():
            exp[str(spec.type.name).lower()].append(name)

        # balance_equality is removed in initialize() for JDBC
        if isinstance(test_mp._backend, JDBCBackend):
            exp["set"].remove("balance_equality")

        # Use ixmp.Scenario to avoid invoking ixmp_source/Java code that automatically
        # populates empty scenarios
        s = ixmp.Scenario(test_mp, model="m", scenario="s", version="new")

        # Initialization succeeds on a totally empty scenario
        MESSAGE.initialize(s)

        # The expected items exist
        for ix_type, exp_names in exp.items():
            obs_names = getattr(s, f"{ix_type}_list")()
            assert sorted(obs_names) == sorted(exp_names)

    def test_initialize_filter_log(self, caplog, test_mp: "Platform") -> None:
        """Test :meth:`MESSAGE.initialize` logging under some conditions.

        For :class:`.Scenario` created with message_ix v3.10 or earlier, equations and
        variables may be initialized but have zero dimensions, thus empty lists of
        "index sets" and "index names". When :class:`.Scenario` is instantiated,
        :meth:`MESSAGE.initialize` is invoked, and in turn
        :meth:`ixmp.model.base.Model.initialize_items`. This method generates many log
        messages on level :data:`~logging.WARNING`.

        In order to prevent this log noise, :func:`.models._filter_log_initialize_items`
        is used. This test checks that it is effective.
        """
        # Use ixmp.Scenario to avoid invoking ixmp_source/Java code that automatically
        # populates empty scenarios
        s = ixmp.Scenario(test_mp, model="m", scenario="s", version="new")

        # Initialize an equation with no dimensions. This mocks the state of a Scenario
        # created with message_ix v3.10 or earlier.
        s.init_equ("NEW_CAPACITY_BOUND_LO", idx_sets=[], idx_names=[])

        s.commit("")
        s.set_as_default()
        caplog.clear()

        # Initialize items.
        MESSAGE.initialize(s)

        # Messages related to re-initializing items with 0 dimensions are filtered and
        # do not reach `caplog`. This assertion fails with message_ix v3.10.
        message_pattern = re.compile(
            r"Existing index (name|set)s of 'NEW_CAPACITY_BOUND_LO' \[\] do not match "
            r"\('node', '.*', 'year'\)"
        )
        extra = list(filter(message_pattern.match, caplog.messages))
        assert not extra, f"{len(extra)} unwanted log messages: {extra}"

    @pytest.mark.jdbc
    def test_solve_retains_all_equations(
        self, request: pytest.FixtureRequest, test_mp: "Platform"
    ) -> None:
        """A JDBC solve retains marginals for non-required equations.

        Regression test: previously :meth:`.MESSAGE.run` populated ``equ_list`` only
        for :class:`.IXMP4Backend`, so JDBC solves passed an empty list and equations
        outside the MESSAGE scheme's required set (e.g. ``COMMODITY_BALANCE_GT``) came
        back with zero rows.
        """
        from message_ix.testing import make_dantzig

        scen = make_dantzig(test_mp, request=request)
        scen.solve(quiet=True)

        # ``COMMODITY_BALANCE_GT`` is not a scheme-required equation but is generated
        # non-empty by the Dantzig model; before the fix it returned zero rows.
        assert len(scen.equ("COMMODITY_BALANCE_GT")) > 0

        # A second, independent solve produces the same result: the default is not
        # leaked or duplicated across model instances.
        clone = scen.clone(scenario=f"{request.node.name}-2", keep_solution=False)
        clone.solve(quiet=True)
        assert len(clone.equ("COMMODITY_BALANCE_GT")) > 0
