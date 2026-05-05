import pytest
from state import BuyerProfile
from inventory import search_properties
from graph import relax_constraints


@pytest.fixture
def scenario_a_profile() -> BuyerProfile:
    """Scenario A — first-time buyer, Whitefield, ₹80L, 2BHK apartment."""
    return BuyerProfile(
        budget_min_lakhs=60,
        budget_max_lakhs=80,
        locations=["Whitefield"],
        property_type="apartment",
        bhk=2,
        possession_months=12,
        lifestyle_tags=["it_corridor", "metro_nearby"],
        must_haves=["gym"],
    )


@pytest.fixture
def scenario_b_profile() -> BuyerProfile:
    """Scenario B — retiree couple, Sarjapur Road, ₹1.2Cr, 3BHK villa."""
    return BuyerProfile(
        budget_min_lakhs=96,
        budget_max_lakhs=120,
        locations=["Sarjapur Road"],
        property_type="villa",
        bhk=3,
        possession_months=12,
    )


@pytest.fixture
def scenario_c_profile() -> BuyerProfile:
    """Scenario C — exhausted search, ₹50L villa in Koramangala."""
    return BuyerProfile(
        budget_min_lakhs=40,
        budget_max_lakhs=50,
        locations=["Koramangala"],
        property_type="villa",
        bhk=3,
        possession_months=6,
    )


class TestScenarioA:
    def test_returns_three_or_more_results(self, scenario_a_profile):
        results = search_properties(scenario_a_profile)
        assert len(results) >= 3

    def test_all_within_budget(self, scenario_a_profile):
        results = search_properties(scenario_a_profile)
        for p in results:
            assert p.price_lakhs <= scenario_a_profile.budget_max_lakhs

    def test_all_correct_location(self, scenario_a_profile):
        results = search_properties(scenario_a_profile)
        for p in results:
            assert p.location.lower() in [
                l.lower() for l in scenario_a_profile.locations
            ]

    def test_all_correct_bhk(self, scenario_a_profile):
        results = search_properties(scenario_a_profile)
        for p in results:
            assert p.bhk == scenario_a_profile.bhk

    def test_no_villas_returned(self, scenario_a_profile):
        results = search_properties(scenario_a_profile)
        for p in results:
            assert "villa" not in p.title.lower()


class TestScenarioB:
    def test_exact_search_returns_fewer_than_three(self, scenario_b_profile):
        """Confirms recovery loop will trigger for this scenario."""
        results = search_properties(scenario_b_profile)
        assert len(results) < 3

    def test_recovery_step2_reaches_three(self, scenario_b_profile):
        """After step 1 + step 2 relaxation, should reach >= 3 candidates."""
        profile = relax_constraints(scenario_b_profile, step=1)
        profile = relax_constraints(profile, step=2)
        results = search_properties(profile)
        assert len(results) >= 3

    def test_all_within_relaxed_budget(self, scenario_b_profile):
        profile = relax_constraints(scenario_b_profile, step=1)
        profile = relax_constraints(profile, step=2)
        results = search_properties(profile)
        for p in results:
            assert p.price_lakhs <= profile.budget_max_lakhs

    def test_only_villas_returned_after_relaxation(self, scenario_b_profile):
        profile = relax_constraints(scenario_b_profile, step=1)
        profile = relax_constraints(profile, step=2)
        results = search_properties(profile)
        for p in results:
            assert "villa" in p.title.lower()


class TestScenarioC:
    def test_all_relaxation_steps_still_under_three(self, scenario_c_profile):
        """No inventory matches even after all 4 relaxation steps."""
        profile = scenario_c_profile
        for step in range(1, 5):
            profile = relax_constraints(profile, step)
        results = search_properties(profile)
        assert len(results) < 3

    def test_search_node_sets_exhausted_flag(self, scenario_c_profile):
        """search_node should set search_exhausted=True for this profile."""
        from graph import search_node
        from state import GraphState
        state = GraphState(
            buyer_profile=scenario_c_profile,
            messages=[{"role": "user", "content": "test"}],
        )
        result = search_node(state)
        assert result.search_exhausted is True
        assert result.recovery_triggered is True
