import json
import os
from dotenv import load_dotenv
from anthropic import Anthropic
from langgraph.graph import StateGraph, START, END

from state import BuyerProfile, GraphState, ScoredProperty
from scoring import score_candidate
from prompts import (
    INTAKE_AGENT_PROMPT,
    ANALYSIS_AGENT_PROMPT,
    COMMUNICATION_AGENT_PROMPT,
)
from inventory import search_properties
from location_utils import get_adjacent_locations

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── Relaxation ────────────────────────────────────────────────────────

RELAXATION_STEPS = {
    1: "Expanded budget by 10%",
    2: "Added adjacent locations (within 5km)",
    3: "Allowed BHK ± 1",
    4: "Expanded budget by a further 10% (total 20% over original)",
}


def relax_constraints(profile: BuyerProfile, step: int) -> BuyerProfile:
    """
    Applies one relaxation step to a BuyerProfile and returns a new profile.
    Does not mutate the input profile.
    """
    if step == 1:
        return profile.model_copy(update={
            "budget_max_lakhs": int(profile.budget_max_lakhs * 1.10)
        })

    elif step == 2:
        expanded = profile.locations + get_adjacent_locations(profile.locations)
        return profile.model_copy(update={
            "locations": list(dict.fromkeys(expanded))  # deduplicate, preserve order
        })

    elif step == 3:
        return profile.model_copy(update={
            "bhk_min": profile.bhk - 1,
            "bhk_max": profile.bhk + 1,
        })

    elif step == 4:
        return profile.model_copy(update={
            "budget_max_lakhs": int(profile.budget_max_lakhs * 1.10)
        })

    return profile  # no-op for unknown step


# ── Nodes ─────────────────────────────────────────────────────────────

def intake_node(state: GraphState) -> GraphState:
    """
    Single-shot intake. Parses buyer input into BuyerProfile.
    Sets incomplete=True and populates constraint_tensions if
    required fields are missing.
    """
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        temperature=0.1,
        system=INTAKE_AGENT_PROMPT,
        messages=state.messages,
    )

    raw = response.content[0].text
    clean = raw.strip().removeprefix("```json").removesuffix("```").strip()

    parsed = json.loads(clean)
    profile = BuyerProfile(**parsed)

    # hard validation — fields Search Agent cannot proceed without
    REQUIRED = ["budget_max_lakhs", "locations", "property_type", "bhk"]
    missing = [
        f for f in REQUIRED
        if not getattr(profile, f, None)
    ]

    if missing:
        profile = profile.model_copy(update={
            "incomplete": True,
            "constraint_tensions": (
                [f"Missing required field: {f}" for f in missing]
                + profile.constraint_tensions
            ),
        })

    return state.model_copy(update={"buyer_profile": profile})


def intake_error_node(state: GraphState) -> GraphState:
    """
    Surfaces missing field errors back to the user.
    Writes to recommendation_report so the frontend
    has one consistent output field to read.
    """
    tensions = state.buyer_profile.constraint_tensions if state.buyer_profile else []
    error_message = (
        "Please complete the following before we can search:\n"
        + "\n".join(f"  • {t}" for t in tensions)
    )
    return state.model_copy(update={"recommendation_report": error_message})


def search_node(state: GraphState) -> GraphState:
    """
    Runs property search against current profile constraints.
    Applies up to 4 relaxation steps if candidate count < 3.
    Sets recovery_triggered=True on first relaxation.
    Sets search_exhausted=True if all steps fail to yield >= 3 results.
    """
    profile = state.buyer_profile
    relaxations_applied = []
    recovery_triggered = False

    candidates = search_properties(profile)

    for step in range(1, 5):
        if len(candidates) >= 3:
            break

        if not recovery_triggered:
            recovery_triggered = True

        profile = relax_constraints(profile, step)
        relaxations_applied.append(RELAXATION_STEPS[step])
        candidates = search_properties(profile)

    search_exhausted = len(candidates) < 3

    return state.model_copy(update={
        "buyer_profile":        profile,
        "candidates":           candidates,
        "relaxations_applied":  relaxations_applied,
        "recovery_triggered":   recovery_triggered,
        "search_exhausted":     search_exhausted,
    })


def analysis_node(state: GraphState) -> GraphState:
    """
    Phase 1 — deterministic scoring via score_candidate().
    Phase 2 — single LLM call for rationale generation on top 5.
    Scores are never LLM-influenced.
    """
    # ── Phase 1: deterministic scoring ──────────────────────────────
    scored = [
        score_candidate(c.model_dump(), state.buyer_profile)
        for c in state.candidates
    ]
    scored.sort(key=lambda p: p.total_score, reverse=True)
    top5 = scored[:5]

    # ── Phase 2: LLM rationale ───────────────────────────────────────
    low_candidate_warning = ""
    if len(state.candidates) < 3:
        low_candidate_warning = (
            f"Note: only {len(state.candidates)} "
            f"{'property' if len(state.candidates) == 1 else 'properties'} "
            f"matched after exhaustive search relaxation.\n\n"
        )

    shortlist_text = "\n".join(
        f"{i+1}. [{p.property_id}] {p.title} — total_score: {p.total_score:.2f}\n"
        f"   budget_fit={p.budget_fit:.2f}, "
        f"location_match={p.location_match:.2f}, "
        f"lifestyle_tags={p.lifestyle_tags:.2f}, "
        f"possession_fit={p.possession_fit:.2f}, "
        f"amenities_match={p.amenities_match:.2f}"
        for i, p in enumerate(top5)
    )

    rationale_prompt = {
        "role": "user",
        "content": (
            f"{low_candidate_warning}"
            f"Relaxations applied: "
            f"{', '.join(state.relaxations_applied) or 'none'}\n\n"
            f"Buyer profile:\n"
            f"{state.buyer_profile.model_dump_json(indent=2)}\n\n"
            f"Scored shortlist:\n{shortlist_text}\n\n"
            f"Populate the rationale field for each property."
        ),
    }

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        temperature=0.1,
        system=ANALYSIS_AGENT_PROMPT,
        messages=[rationale_prompt],
    )

    raw = response.content[0].text
    clean = raw.strip().removeprefix("```json").removesuffix("```").strip()
    rationale_map: dict[str, str] = json.loads(clean)

    for p in top5:
        p.rationale = rationale_map.get(p.property_id, "")

    return state.model_copy(update={"shortlist": top5})


def communication_node(state: GraphState) -> GraphState:
    """
    Single LLM call. Synthesises shortlist + state flags into
    a buyer-facing recommendation report. Plain text output.
    """
    shortlist_text = "\n".join(
        f"{i+1}. {p.title} (score: {p.total_score:.2f})\n"
        f"   Location: {p.location} | "
        f"Price: ₹{p.price_lakhs}L | "
        f"BHK: {p.bhk} | "
        f"Possession: {p.possession_months} months\n"
        f"   Rationale: {p.rationale}"
        for i, p in enumerate(state.shortlist)
    )

    user_message = {
        "role": "user",
        "content": (
            f"recovery_triggered: {state.recovery_triggered}\n"
            f"search_exhausted: {state.search_exhausted}\n"
            f"relaxations_applied: "
            f"{', '.join(state.relaxations_applied) or 'none'}\n\n"
            f"Buyer profile:\n"
            f"{state.buyer_profile.model_dump_json(indent=2)}\n\n"
            f"Scored shortlist:\n{shortlist_text}"
        ),
    }

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        temperature=0.1,
        system=COMMUNICATION_AGENT_PROMPT,
        messages=[user_message],
    )

    return state.model_copy(update={
        "recommendation_report": response.content[0].text
    })


# ── Routing ───────────────────────────────────────────────────────────

def route_after_intake(state: GraphState) -> str:
    if state.buyer_profile is None:
        return "intake_error"
    if state.buyer_profile.incomplete:
        return "intake_error"
    return "search"


def route_after_search(state: GraphState) -> str:
    if state.buyer_profile is None:
        return "intake_error"
    return "analysis"


# ── Graph assembly ────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    builder = StateGraph(GraphState)

    builder.add_node("intake",          intake_node)
    builder.add_node("intake_error",    intake_error_node)
    builder.add_node("search",          search_node)
    builder.add_node("analysis",        analysis_node)
    builder.add_node("communication",   communication_node)

    builder.add_edge(START, "intake")

    builder.add_conditional_edges(
        "intake",
        route_after_intake,
        {
            "search":       "search",
            "intake_error": "intake_error",
        },
    )

    builder.add_edge("intake_error", END)

    builder.add_conditional_edges(
        "search",
        route_after_search,
        {
            "analysis":     "analysis",
            "intake_error": "intake_error",
        },
    )

    builder.add_edge("analysis",        "communication")
    builder.add_edge("communication",   END)

    return builder.compile()


# ── Public entrypoint ─────────────────────────────────────────────────

graph = build_graph()


def run(user_input: str) -> str:
    """
    Accepts raw buyer input string.
    Returns the final recommendation report or validation error message.
    """
    initial_state = GraphState(
        messages=[{"role": "user", "content": user_input}]
    )
    final_state = graph.invoke(initial_state)
    return final_state["recommendation_report"]
