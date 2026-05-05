import pytest
from state import BuyerProfile
from graph import relax_constraints, RELAXATION_STEPS
from location_utils import get_adjacent_locations


@pytest.fixture
def base_profile() -> BuyerProfile:
    return BuyerProfile(
        budget_min_lakhs=96,
        budget_max_lakhs=120,
        locations=["Sarjapur Road"],
        property_type="villa",
        bhk=3,
        possession_months=12,
    )


class TestRelaxationStepLabels:
    def test_all_four_steps_labelled(self):
        assert set(RELAXATION_STEPS.keys()) == {1, 2, 3, 4}

    def test_labels_are_non_empty_strings(self):
        for step, label in RELAXATION_STEPS.items():
            assert isinstance(label, str) and len(label) > 0


class TestStep1BudgetExpansion:
    def test_budget_max_increases_by_ten_percent(self, base_profile):
        relaxed = relax_constraints(base_profile, step=1)
        assert relaxed.budget_max_lakhs == int(120 * 1.10)  # 132

    def test_budget_min_unchanged(self, base_profile):
        relaxed = relax_constraints(base_profile, step=1)
        assert relaxed.budget_min_lakhs == base_profile.budget_min_lakhs

    def test_original_profile_not_mutated(self, base_profile):
        original_max = base_profile.budget_max_lakhs
        relax_constraints(base_profile, step=1)
        assert base_profile.budget_max_lakhs == original_max


class TestStep2AdjacentLocations:
    def test_adjacent_locations_added(self, base_profile):
        relaxed = relax_constraints(base_profile, step=2)
        lower = [l.lower() for l in relaxed.locations]
        assert "bellandur" in lower

    def test_original_location_preserved(self, base_profile):
        relaxed = relax_constraints(base_profile, step=2)
        assert "Sarjapur Road" in relaxed.locations

    def test_no_duplicate_locations(self, base_profile):
        relaxed = relax_constraints(base_profile, step=2)
        lower = [l.lower() for l in relaxed.locations]
        assert len(lower) == len(set(lower))

    def test_unknown_location_returns_original(self):
        profile = BuyerProfile(
            budget_min_lakhs=50,
            budget_max_lakhs=80,
            locations=["Yelahanka"],    # not in ADJACENT_LOCATIONS
            property_type="apartment",
            bhk=2,
            possession_months=12,
        )
        relaxed = relax_constraints(profile, step=2)
        assert relaxed.locations == profile.locations


class TestStep3BHKRange:
    def test_bhk_min_set_to_bhk_minus_one(self, base_profile):
        relaxed = relax_constraints(base_profile, step=3)
        assert relaxed.bhk_min == base_profile.bhk - 1

    def test_bhk_max_set_to_bhk_plus_one(self, base_profile):
        relaxed = relax_constraints(base_profile, step=3)
        assert relaxed.bhk_max == base_profile.bhk + 1

    def test_original_bhk_preserved(self, base_profile):
        relaxed = relax_constraints(base_profile, step=3)
        assert relaxed.bhk == base_profile.bhk


class TestStep4FurtherBudgetExpansion:
    def test_step4_compounds_on_step1(self, base_profile):
        # step 1: 120 → 132; step 4: 132 → 145
        after_step1 = relax_constraints(base_profile, step=1)
        after_step4 = relax_constraints(after_step1, step=4)
        assert after_step4.budget_max_lakhs == int(132 * 1.10)

    def test_step4_standalone_adds_ten_percent(self, base_profile):
        relaxed = relax_constraints(base_profile, step=4)
        assert relaxed.budget_max_lakhs == int(120 * 1.10)


class TestAdjacentLocations:
    def test_known_location_returns_adjacencies(self):
        result = get_adjacent_locations(["Whitefield"])
        assert len(result) > 0

    def test_unknown_location_returns_empty(self):
        result = get_adjacent_locations(["Yelahanka"])
        assert result == []

    def test_multiple_locations_aggregated(self):
        single = get_adjacent_locations(["Whitefield"])
        multi  = get_adjacent_locations(["Whitefield", "Koramangala"])
        assert len(multi) > len(single)

    def test_case_insensitive_lookup(self):
        upper = get_adjacent_locations(["WHITEFIELD"])
        lower = get_adjacent_locations(["whitefield"])
        assert upper == lower
