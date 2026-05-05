from state import BuyerProfile, Property

MOCK_INVENTORY: list[dict] = [

    # ── Whitefield cluster (Scenario A territory) ─────────────────────
    {
        "property_id": "WF001",
        "title": "Prestige Lakeside Habitat — 2BHK",
        "location": "Whitefield",
        "price_lakhs": 74.5,
        "bhk": 2,
        "possession_months": 6,
        "amenities": ["gym", "swimming pool", "clubhouse", "24hr security"],
        "tags": ["it_corridor", "metro_nearby", "gated_community"],
    },
    {
        "property_id": "WF002",
        "title": "Brigade Cosmopolis — 2BHK",
        "location": "Whitefield",
        "price_lakhs": 78.0,
        "bhk": 2,
        "possession_months": 3,
        "amenities": ["gym", "children_play_area", "24hr security", "power_backup"],
        "tags": ["it_corridor", "school_nearby", "gated_community"],
    },
    {
        "property_id": "WF003",
        "title": "Sobha Dream Acres — 2BHK",
        "location": "Whitefield",
        "price_lakhs": 68.0,
        "bhk": 2,
        "possession_months": 12,
        "amenities": ["gym", "swimming pool", "24hr security"],
        "tags": ["it_corridor", "gated_community"],
    },
    {
        "property_id": "WF004",
        "title": "Godrej United — 3BHK",
        "location": "Whitefield",
        "price_lakhs": 95.0,
        "bhk": 3,
        "possession_months": 18,
        "amenities": ["gym", "swimming pool", "clubhouse", "children_play_area"],
        "tags": ["it_corridor", "metro_nearby", "school_nearby", "gated_community"],
    },

    # ── Marathahalli cluster (adjacent to Whitefield) ──────────────────
    {
        "property_id": "MM001",
        "title": "Salarpuria Serenity — 2BHK",
        "location": "Marathahalli",
        "price_lakhs": 71.0,
        "bhk": 2,
        "possession_months": 9,
        "amenities": ["gym", "24hr security", "power_backup"],
        "tags": ["it_corridor", "metro_nearby"],
    },
    {
        "property_id": "MM002",
        "title": "Adarsh Palm Retreat — 2BHK",
        "location": "Marathahalli",
        "price_lakhs": 76.5,
        "bhk": 2,
        "possession_months": 6,
        "amenities": ["swimming pool", "clubhouse", "24hr security"],
        "tags": ["it_corridor", "gated_community"],
    },

    # ── Sarjapur Road cluster (Scenario B territory) ───────────────────
    # Intentionally sparse for villas — triggers recovery loop
    {
        "property_id": "SR001",
        "title": "Adarsh Palm Meadows — Villa",
        "location": "Sarjapur Road",
        "price_lakhs": 118.0,
        "bhk": 3,
        "possession_months": 6,
        "amenities": ["private_garden", "swimming pool", "clubhouse",
                      "24hr security", "elevator"],
        "tags": ["gated_community", "school_nearby", "it_corridor"],
    },
    {
        "property_id": "SR002",
        "title": "Prestige Golfshire — Villa",
        "location": "Sarjapur Road",
        "price_lakhs": 145.0,           # over budget — tests budget filter
        "bhk": 4,
        "possession_months": 12,
        "amenities": ["private_garden", "golf_course", "swimming pool",
                      "24hr security", "elevator"],
        "tags": ["gated_community", "it_corridor"],
    },

    # ── Bellandur cluster (adjacent to Sarjapur Road) ──────────────────
    # Surfaces during Scenario B recovery — Step 2 (adjacent locations)
    {
        "property_id": "BL001",
        "title": "Embassy Springs — Villa",
        "location": "Bellandur",
        "price_lakhs": 115.0,
        "bhk": 3,
        "possession_months": 9,
        "amenities": ["private_garden", "swimming pool", "clubhouse",
                      "24hr security", "elevator"],
        "tags": ["gated_community", "it_corridor", "school_nearby"],
    },
    {
        "property_id": "BL002",
        "title": "Brigade Orchards — Villa",
        "location": "Bellandur",
        "price_lakhs": 108.0,
        "bhk": 3,
        "possession_months": 15,
        "amenities": ["private_garden", "clubhouse", "24hr security", "elevator"],
        "tags": ["gated_community", "school_nearby"],
    },

    # ── HSR Layout cluster (adjacent to Sarjapur Road) ─────────────────
    {
        "property_id": "HSR001",
        "title": "Sobha City — 3BHK",
        "location": "HSR Layout",
        "price_lakhs": 112.0,
        "bhk": 3,
        "possession_months": 6,
        "amenities": ["gym", "swimming pool", "24hr security", "power_backup"],
        "tags": ["metro_nearby", "gated_community", "it_corridor"],
    },

    # ── Koramangala cluster (price diversity) ──────────────────────────
    {
        "property_id": "KRM001",
        "title": "Mantri Synergy — 2BHK",
        "location": "Koramangala",
        "price_lakhs": 82.0,            # slightly over ₹80L — tests budget penalty
        "bhk": 2,
        "possession_months": 3,
        "amenities": ["gym", "swimming pool", "24hr security"],
        "tags": ["metro_nearby", "school_nearby", "it_corridor"],
    },
]

def normalise_location(loc: str) -> str:
    """Strip city suffix e.g. 'Whitefield, Bengaluru' → 'whitefield'"""
    return loc.split(",")[0].strip().lower()

def search_properties(profile: BuyerProfile) -> list[Property]:
    """
    Filters MOCK_INVENTORY against current profile constraints.
    Hard filters: budget ceiling, location, BHK (exact or range), property type.
    Returns list[Property] — unscored, unranked.
    """
    results = []

    for item in MOCK_INVENTORY:

        # 1. Budget hard ceiling — never exceed max
        if item["price_lakhs"] > profile.budget_max_lakhs:
            continue

        # 2. Location filter — case-insensitive
        #if item["location"].lower() not in [l.lower() for l in profile.locations]:
        #    continue
        profile_locations_normalised = [normalise_location(l) for l in profile.locations]
        if normalise_location(item["location"]) not in profile_locations_normalised:
            continue

        # 3. BHK filter — exact match, or range if relaxation applied
        if profile.bhk_min is not None and profile.bhk_max is not None:
            if not (profile.bhk_min <= item["bhk"] <= profile.bhk_max):
                continue
        else:
            if item["bhk"] != profile.bhk:
                continue

        # 4. Property type filter — inferred from title keywords
        if profile.property_type == "villa":
            if "villa" not in item["title"].lower():
                continue
        elif profile.property_type == "plot":
            if "plot" not in item["title"].lower():
                continue
        # "apartment" matches everything that isn't explicitly villa/plot

        results.append(Property(**item))

    return results
