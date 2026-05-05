ADJACENT_LOCATIONS: dict[str, list[str]] = {
    "whitefield":       ["Kadugodi", "Brookefield", "Mahadevapura"],
    "sarjapur road":    ["Bellandur", "HSR Layout", "Carmelaram"],
    "koramangala":      ["HSR Layout", "BTM Layout", "Indiranagar"],
    "marathahalli":     ["Whitefield", "Mahadevapura", "KR Puram"],
    "electronic city":  ["Bannerghatta Road", "JP Nagar", "BTM Layout"],
    "bellandur":        ["Sarjapur Road", "HSR Layout", "Carmelaram"],
    "hsr layout":       ["Koramangala", "Bellandur", "BTM Layout"],
}


def get_adjacent_locations(locations: list[str]) -> list[str]:
    """
    Returns adjacent locations for all locations in the input list.
    Lookup is case-insensitive.
    Unknown locations return no adjacencies rather than raising.
    """
    adjacent = []
    for loc in locations:
        adjacent += ADJACENT_LOCATIONS.get(loc.lower(), [])
    return adjacent
