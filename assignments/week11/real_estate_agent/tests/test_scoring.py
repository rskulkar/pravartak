import pytest
from state import BuyerProfile
from scoring import score_candidate, SCORE_WEIGHTS


@pytest.fixture
def base_profile() -> BuyerProfile:
    return BuyerProfile(
        budget_min_lakhs=60,
        budget_max_lakhs=80,
        locations=["Whitefield"],
        property_type="apartment",
        bhk=2,
        possession_months=12,
        must_haves=["gym", "swimming pool"],
        lifestyle_tags=["it_corridor", "metro_nearby", "gated_community"],
    )


@pytest.fixture
def perfect_match() -> dict:
    """Property that should score close to 1.0 on all dimensions."""
    return {
        "property_id": "WF001",
        "title": "Test Property",
        "location": "Whitefield",
        "price_lakhs": 65.0,
        "bhk": 2,
        "possession_months": 10,
        "amenities": ["gym", "swimming pool"],
        "tags": ["it_corridor", "metro_nearby", "gated_community"],
    }


@pytest.fixture
def poor_match() -> dict:
    """Property that should score low on all dimensions."""
    return {
        "property_id": "KRM001",
        "title": "Poor Match Property",
        "location": "Koramangala",      # not in profile locations → 0.5
        "price_lakhs": 79.5,            # near budget ceiling → low budget_fit
        "bhk": 2,
        "possession_months": 24,        # 12 months over deadline → 0.0
        "amenities": ["power_backup"],  # no must-haves covered → 0.0
        "tags": ["school_nearby"],      # no lifestyle tag overlap → 0.0
    }


class TestScoreWeights:
    def test_weights_sum_to_one(self):
        total = sum(SCORE_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, expected 1.0"

    def test_all_dimensions_present(self):
        expected = {
            "budget_fit", "location_match", "lifestyle_tags",
            "possession_fit", "amenities_match",
        }
        assert set(SCORE_WEIGHTS.keys()) == expected


class TestBudgetFit:
    def test_price_at_budget_min_scores_one(self, base_profile, perfect_match):
        perfect_match["price_lakhs"] = 60.0
        scored = score_candidate(perfect_match, base_profile)
        assert scored.budget_fit == pytest.approx(1.0)

    def test_price_at_midpoint_scores_half(self, base_profile, perfect_match):
        perfect_match["price_lakhs"] = 70.0
        scored = score_candidate(perfect_match, base_profile)
        assert scored.budget_fit == pytest.approx(0.5, abs=0.01)

    def test_price_at_ceiling_scores_zero(self, base_profile, perfect_match):
        perfect_match["price_lakhs"] = 80.0
        scored = score_candidate(perfect_match, base_profile)
        assert scored.budget_fit == pytest.approx(0.0, abs=0.01)

    def test_price_over_ceiling_clamps_to_zero(self, base_profile, perfect_match):
        perfect_match["price_lakhs"] = 95.0
        scored = score_candidate(perfect_match, base_profile)
        assert scored.budget_fit == 0.0


class TestLocationMatch:
    def test_exact_location_scores_one(self, base_profile, perfect_match):
        scored = score_candidate(perfect_match, base_profile)
        assert scored.location_match == pytest.approx(1.0)

    def test_non_exact_location_scores_half(self, base_profile, poor_match):
        scored = score_candidate(poor_match, base_profile)
        assert scored.location_match == pytest.approx(0.5)

    def test_location_match_is_case_insensitive(self, base_profile, perfect_match):
        perfect_match["location"] = "whitefield"
        scored = score_candidate(perfect_match, base_profile)
        assert scored.location_match == pytest.approx(1.0)


class TestLifestyleTags:
    def test_full_overlap_scores_one(self, base_profile, perfect_match):
        scored = score_candidate(perfect_match, base_profile)
        assert scored.lifestyle_tags == pytest.approx(1.0)

    def test_zero_overlap_scores_zero(self, base_profile, poor_match):
        scored = score_candidate(poor_match, base_profile)
        assert scored.lifestyle_tags == pytest.approx(0.0)

    def test_partial_overlap_jaccard(self, base_profile, perfect_match):
        # buyer: {it_corridor, metro_nearby, gated_community}
        # prop:  {it_corridor, school_nearby, park_nearby}
        # intersection: {it_corridor} = 1
        # union: {it_corridor, metro_nearby, gated_community,
        #         school_nearby, park_nearby} = 5
        # Jaccard = 1/5 = 0.2
        perfect_match["tags"] = ["it_corridor", "school_nearby", "park_nearby"]
        scored = score_candidate(perfect_match, base_profile)
        assert scored.lifestyle_tags == pytest.approx(0.2, abs=0.01)

    def test_no_buyer_tags_scores_zero(self, base_profile, perfect_match):
        profile = base_profile.model_copy(update={"lifestyle_tags": []})
        scored = score_candidate(perfect_match, profile)
        assert scored.lifestyle_tags == pytest.approx(0.0)


class TestPossessionFit:
    def test_possession_before_deadline_scores_one(self, base_profile, perfect_match):
        perfect_match["possession_months"] = 10
        scored = score_candidate(perfect_match, base_profile)
        assert scored.possession_fit == pytest.approx(1.0)

    def test_possession_at_deadline_scores_one(self, base_profile, perfect_match):
        perfect_match["possession_months"] = 12
        scored = score_candidate(perfect_match, base_profile)
        assert scored.possession_fit == pytest.approx(1.0)

    def test_six_months_overshoot_scores_half(self, base_profile, perfect_match):
        perfect_match["possession_months"] = 18
        scored = score_candidate(perfect_match, base_profile)
        assert scored.possession_fit == pytest.approx(0.5, abs=0.01)

    def test_twelve_months_overshoot_scores_zero(self, base_profile, perfect_match):
        perfect_match["possession_months"] = 24
        scored = score_candidate(perfect_match, base_profile)
        assert scored.possession_fit == pytest.approx(0.0, abs=0.01)

    def test_extreme_overshoot_clamps_to_zero(self, base_profile, perfect_match):
        perfect_match["possession_months"] = 48
        scored = score_candidate(perfect_match, base_profile)
        assert scored.possession_fit == 0.0


class TestAmenitiesMatch:
    def test_all_must_haves_covered_scores_one(self, base_profile, perfect_match):
        scored = score_candidate(perfect_match, base_profile)
        assert scored.amenities_match == pytest.approx(1.0)

    def test_no_must_haves_covered_scores_zero(self, base_profile, poor_match):
        scored = score_candidate(poor_match, base_profile)
        assert scored.amenities_match == pytest.approx(0.0)

    def test_partial_coverage(self, base_profile, perfect_match):
        # must_haves = [gym, swimming pool]; only gym covered → 0.5
        perfect_match["amenities"] = ["gym", "power_backup"]
        scored = score_candidate(perfect_match, base_profile)
        assert scored.amenities_match == pytest.approx(0.5)

    def test_no_must_haves_in_profile_scores_one(self, base_profile, perfect_match):
        profile = base_profile.model_copy(update={"must_haves": []})
        scored = score_candidate(perfect_match, profile)
        assert scored.amenities_match == pytest.approx(1.0)


class TestTotalScore:
    def test_total_score_bounded_zero_to_one(self, base_profile, perfect_match):
        scored = score_candidate(perfect_match, base_profile)
        assert 0.0 <= scored.total_score <= 1.0

    def test_perfect_match_scores_high(self, base_profile, perfect_match):
        scored = score_candidate(perfect_match, base_profile)
        assert scored.total_score > 0.85

    def test_poor_match_scores_low(self, base_profile, poor_match):
        scored = score_candidate(poor_match, base_profile)
        assert scored.total_score < 0.40

    def test_total_is_exact_weighted_sum(self, base_profile, perfect_match):
        scored = score_candidate(perfect_match, base_profile)
        expected = (
            scored.budget_fit      * SCORE_WEIGHTS["budget_fit"]      +
            scored.location_match  * SCORE_WEIGHTS["location_match"]  +
            scored.lifestyle_tags  * SCORE_WEIGHTS["lifestyle_tags"]  +
            scored.possession_fit  * SCORE_WEIGHTS["possession_fit"]  +
            scored.amenities_match * SCORE_WEIGHTS["amenities_match"]
        )
        assert scored.total_score == pytest.approx(expected, abs=1e-9)
