import pytest
from unittest.mock import patch, MagicMock
from graph import run, build_graph
from state import GraphState


def make_mock_response(text: str) -> MagicMock:
    """Builds a minimal mock Anthropic API response object."""
    mock_content = MagicMock()
    mock_content.text = text
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    return mock_response


# ── Mock payloads ──────────────────────────────────────────────────────

MOCK_PROFILE_A = """{
    "budget_min_lakhs": 60,
    "budget_max_lakhs": 80,
    "locations": ["Whitefield"],
    "property_type": "apartment",
    "bhk": 2,
    "possession_months": 12,
    "must_haves": ["gym"],
    "lifestyle_tags": ["it_corridor", "metro_nearby"],
    "constraint_tensions": [],
    "incomplete": false
}"""

MOCK_PROFILE_B = """{
    "budget_min_lakhs": 96,
    "budget_max_lakhs": 120,
    "locations": ["Sarjapur Road"],
    "property_type": "villa",
    "bhk": 3,
    "possession_months": 12,
    "must_haves": ["elevator", "gated_community"],
    "lifestyle_tags": ["gated_community", "school_nearby"],
    "constraint_tensions": [],
    "incomplete": false
}"""

MOCK_INCOMPLETE_PROFILE = """{
    "budget_min_lakhs": 60,
    "budget_max_lakhs": 80,
    "locations": [],
    "property_type": "apartment",
    "bhk": 0,
    "possession_months": 12,
    "must_haves": [],
    "lifestyle_tags": [],
    "constraint_tensions": [
        "Missing required field: locations",
        "Missing required field: bhk"
    ],
    "incomplete": true
}"""

MOCK_RATIONALE = """{
    "WF001": "Fits comfortably within budget with a prime IT corridor location.",
    "WF002": "Strong location match, possession well within your deadline.",
    "WF003": "Best value option — slight possession delay but within range."
}"""

MOCK_RATIONALE_B = """{
    "SR001": "Only property in Sarjapur Road within budget after relaxation.",
    "BL001": "Surfaced after expanding to adjacent Bellandur. Strong villa match.",
    "BL002": "Good value villa in Bellandur, gated community with elevator access."
}"""

MOCK_REPORT_A = (
    "Based on your requirements, here are the top properties in Whitefield..."
)

MOCK_REPORT_B = (
    "We widened the search slightly beyond your initial locations "
    "to find you strong options..."
)


# ── Scenario A ─────────────────────────────────────────────────────────

class TestScenarioAEndToEnd:
    def test_run_returns_non_empty_report(self):
        with patch("graph.client") as mock_client:
            mock_client.messages.create.side_effect = [
                make_mock_response(MOCK_PROFILE_A),
                make_mock_response(MOCK_RATIONALE),
                make_mock_response(MOCK_REPORT_A),
            ]
            report = run(
                "I'm looking for a 2BHK apartment in Whitefield, "
                "budget ₹60L–₹80L, possession within 12 months, "
                "must have gym, priorities are IT corridor and metro access."
            )
        assert isinstance(report, str)
        assert len(report) > 0

    def test_exactly_three_llm_calls_for_clean_run(self):
        """Intake + Analysis + Communication = 3 calls. No recovery."""
        with patch("graph.client") as mock_client:
            mock_client.messages.create.side_effect = [
                make_mock_response(MOCK_PROFILE_A),
                make_mock_response(MOCK_RATIONALE),
                make_mock_response(MOCK_REPORT_A),
            ]
            run("2BHK apartment Whitefield ₹60L–₹80L 12 months gym it_corridor")
            assert mock_client.messages.create.call_count == 3

    def test_report_content_matches_mock(self):
        with patch("graph.client") as mock_client:
            mock_client.messages.create.side_effect = [
                make_mock_response(MOCK_PROFILE_A),
                make_mock_response(MOCK_RATIONALE),
                make_mock_response(MOCK_REPORT_A),
            ]
            report = run("2BHK apartment Whitefield ₹60L–₹80L 12 months")
        assert report == MOCK_REPORT_A

    def test_recovery_not_triggered_for_scenario_a(self):
        with patch("graph.client") as mock_client:
            mock_client.messages.create.side_effect = [
                make_mock_response(MOCK_PROFILE_A),
                make_mock_response(MOCK_RATIONALE),
                make_mock_response(MOCK_REPORT_A),
            ]
            graph = build_graph()
            initial = GraphState(
                messages=[{"role": "user", "content": "2BHK Whitefield ₹80L"}]
            )
            final = graph.invoke(initial)
        assert final["recovery_triggered"] is False


# ── Scenario B ─────────────────────────────────────────────────────────

class TestScenarioBEndToEnd:
    def test_recovery_triggered(self):
        graph = build_graph()
        initial = GraphState(
            messages=[{
                "role": "user",
                "content": "3BHK villa Sarjapur Road ₹1.2Cr elevator gated"
            }]
        )
        with patch("graph.client") as mock_client:
            mock_client.messages.create.side_effect = [
                make_mock_response(MOCK_PROFILE_B),
                make_mock_response(MOCK_RATIONALE_B),
                make_mock_response(MOCK_REPORT_B),
            ]
            final = graph.invoke(initial)
        assert final["recovery_triggered"] is True

    def test_relaxations_applied_non_empty(self):
        graph = build_graph()
        initial = GraphState(
            messages=[{"role": "user", "content": "3BHK villa Sarjapur Road ₹1.2Cr"}]
        )
        with patch("graph.client") as mock_client:
            mock_client.messages.create.side_effect = [
                make_mock_response(MOCK_PROFILE_B),
                make_mock_response(MOCK_RATIONALE_B),
                make_mock_response(MOCK_REPORT_B),
            ]
            final = graph.invoke(initial)
        assert len(final["relaxations_applied"]) > 0

    def test_report_acknowledges_recovery(self):
        with patch("graph.client") as mock_client:
            mock_client.messages.create.side_effect = [
                make_mock_response(MOCK_PROFILE_B),
                make_mock_response(MOCK_RATIONALE_B),
                make_mock_response(MOCK_REPORT_B),
            ]
            report = run("3BHK villa Sarjapur Road ₹1.2Cr elevator gated community")
        assert "widened" in report.lower() or "expanded" in report.lower()


# ── Incomplete profile ──────────────────────────────────────────────────

class TestIncompleteProfile:
    def test_missing_fields_returns_error_message(self):
        with patch("graph.client") as mock_client:
            mock_client.messages.create.return_value = \
                make_mock_response(MOCK_INCOMPLETE_PROFILE)
            report = run("I want to buy something somewhere")
        assert "Missing required field" in report

    def test_no_downstream_llm_calls_on_incomplete(self):
        """Search, Analysis, Communication should not be called."""
        with patch("graph.client") as mock_client:
            mock_client.messages.create.return_value = \
                make_mock_response(MOCK_INCOMPLETE_PROFILE)
            run("I want to buy something")
            # only intake_node calls the LLM — one call total
            assert mock_client.messages.create.call_count == 1
