from state import BuyerProfile, ScoredProperty

SCORE_WEIGHTS = {
    "budget_fit":       0.30,
    "location_match":   0.25,
    "lifestyle_tags":   0.20,
    "possession_fit":   0.15,
    "amenities_match":  0.10,
}


def score_candidate(candidate: dict, profile: BuyerProfile) -> ScoredProperty:
    """
    Deterministic scoring — no LLM dependency.
    All dimensions normalised to [0.0, 1.0].
    total_score is the exact weighted sum of all dimensions.
    """
    p = ScoredProperty(**candidate)

    # 1. Budget fit — linear penalty as price approaches budget_max
    budget_range = profile.budget_max_lakhs - profile.budget_min_lakhs
    if budget_range > 0:
        p.budget_fit = max(
            0.0,
            1.0 - (p.price_lakhs - profile.budget_min_lakhs) / budget_range
        )
    else:
        p.budget_fit = 1.0 if p.price_lakhs <= profile.budget_max_lakhs else 0.0

    # 2. Location match — exact = 1.0, relaxed/adjacent = 0.5
    p.location_match = (
        1.0 if p.location.lower() in [l.lower() for l in profile.locations]
        else 0.5
    )

    # 3. Lifestyle tags — Jaccard similarity
    buyer_tags = set(profile.lifestyle_tags)
    prop_tags  = set(p.tags)
    if buyer_tags:
        union = buyer_tags | prop_tags
        p.lifestyle_tags = len(buyer_tags & prop_tags) / len(union) if union else 0.0
    else:
        p.lifestyle_tags = 0.0

    # 4. Possession fit — linear penalty per month over buyer deadline
    #    full penalty reached at 12 months overshoot
    overshoot = max(0, p.possession_months - profile.possession_months)
    p.possession_fit = max(0.0, 1.0 - overshoot / 12)

    # 5. Amenities match — recall: fraction of must_haves covered
    must = set(profile.must_haves)
    if must:
        p.amenities_match = len(must & set(p.amenities)) / len(must)
    else:
        p.amenities_match = 1.0     # no must-haves = no penalty

    # weighted sum
    p.total_score = sum(
        getattr(p, dim) * weight
        for dim, weight in SCORE_WEIGHTS.items()
    )

    return p
