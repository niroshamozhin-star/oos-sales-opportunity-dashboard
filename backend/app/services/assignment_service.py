"""assignment_service.py - deterministic territory -> salesperson -> manager
mapping. Never uses the LLM (per the architecture principle: assignment is
application logic, not an AI decision).

The mapping itself is sample/demo master data for this prototype, kept
here rather than hardcoded in the UI so it's easy to move into a real
master-data table or Azure SQL later without touching any calling code."""

TERRITORY_MAP = {
    # state -> (salesperson_name, region, manager_name)
    "TX": ("John Smith", "South", "South Region Manager"),
    "OK": ("John Smith", "South", "South Region Manager"),
    "AR": ("John Smith", "South", "South Region Manager"),
    "LA": ("John Smith", "South", "South Region Manager"),

    "FL": ("Sarah Wilson", "South", "South Region Manager"),
    "AL": ("Sarah Wilson", "South", "South Region Manager"),
    "MS": ("Sarah Wilson", "South", "South Region Manager"),
    "TN": ("Sarah Wilson", "South", "South Region Manager"),

    "CA": ("Mike Johnson", "West", "West Region Manager"),
    "AZ": ("Mike Johnson", "West", "West Region Manager"),
    "NV": ("Mike Johnson", "West", "West Region Manager"),
    "OR": ("Mike Johnson", "West", "West Region Manager"),
    "WA": ("Mike Johnson", "West", "West Region Manager"),
    "UT": ("Mike Johnson", "West", "West Region Manager"),
    "CO": ("Mike Johnson", "West", "West Region Manager"),
    "ID": ("Mike Johnson", "West", "West Region Manager"),
    "MT": ("Mike Johnson", "West", "West Region Manager"),
    "WY": ("Mike Johnson", "West", "West Region Manager"),
    "NM": ("Mike Johnson", "West", "West Region Manager"),
    "AK": ("Mike Johnson", "West", "West Region Manager"),
    "HI": ("Mike Johnson", "West", "West Region Manager"),

    "NY": ("David Brown", "Northeast", "Northeast Region Manager"),
    "NJ": ("David Brown", "Northeast", "Northeast Region Manager"),
    "PA": ("David Brown", "Northeast", "Northeast Region Manager"),
    "MA": ("David Brown", "Northeast", "Northeast Region Manager"),
    "CT": ("David Brown", "Northeast", "Northeast Region Manager"),
    "MD": ("Amy Chen", "Northeast", "Northeast Region Manager"),
    "VA": ("Amy Chen", "Northeast", "Northeast Region Manager"),
    "DE": ("Amy Chen", "Northeast", "Northeast Region Manager"),
    "DC": ("Amy Chen", "Northeast", "Northeast Region Manager"),
    "RI": ("Amy Chen", "Northeast", "Northeast Region Manager"),
    "VT": ("Amy Chen", "Northeast", "Northeast Region Manager"),
    "NH": ("Amy Chen", "Northeast", "Northeast Region Manager"),
    "ME": ("Amy Chen", "Northeast", "Northeast Region Manager"),
    "WV": ("Amy Chen", "Northeast", "Northeast Region Manager"),

    "GA": ("Lisa Brown", "Southeast", "Southeast Region Manager"),
    "NC": ("Lisa Brown", "Southeast", "Southeast Region Manager"),
    "SC": ("Lisa Brown", "Southeast", "Southeast Region Manager"),
    "KY": ("Lisa Brown", "Southeast", "Southeast Region Manager"),

    "OH": ("Chris Patel", "Midwest", "Midwest Region Manager"),
    "IL": ("Chris Patel", "Midwest", "Midwest Region Manager"),
    "IN": ("Chris Patel", "Midwest", "Midwest Region Manager"),
    "MI": ("Chris Patel", "Midwest", "Midwest Region Manager"),
    "WI": ("Chris Patel", "Midwest", "Midwest Region Manager"),
    "MN": ("Drew Foster", "Midwest", "Midwest Region Manager"),
    "IA": ("Drew Foster", "Midwest", "Midwest Region Manager"),
    "MO": ("Drew Foster", "Midwest", "Midwest Region Manager"),
    "KS": ("Drew Foster", "Midwest", "Midwest Region Manager"),
    "NE": ("Drew Foster", "Midwest", "Midwest Region Manager"),
    "ND": ("Drew Foster", "Midwest", "Midwest Region Manager"),
    "SD": ("Drew Foster", "Midwest", "Midwest Region Manager"),
}


def assign_salesperson(state):
    """Pure deterministic lookup - no LLM involved. Returns
    (salesperson_name, region, manager_name), or None if this state has no
    territory mapping (e.g. Canadian provinces occasionally present in the
    source data). Returning None (rather than a fake placeholder person)
    is what lets an opportunity legitimately stay in 'NEW' status - it's
    real information: nobody owns this territory yet. Used at seed/creation
    time - never falls back, since "no owner yet" is a real signal worth
    preserving automatically."""
    return TERRITORY_MAP.get(state)


# Not a formally owned territory - closest-US-region fallback used ONLY by
# the manual "Assign Salesperson" action on a NEW opportunity, so a sales
# manager reviewing the unassigned queue can still route an out-of-territory
# lead (Canadian provinces, occasional overseas registrations) to the
# closest existing team instead of leaving it stuck forever. This never
# runs automatically at seed/creation time - assign_salesperson() returning
# None there stays a real, meaningful "nobody owns this yet" signal.
FALLBACK_TERRITORY_MAP = {
    "BC": ("Mike Johnson", "West", "West Region Manager"),
    "AB": ("Mike Johnson", "West", "West Region Manager"),
    "SK": ("Drew Foster", "Midwest", "Midwest Region Manager"),
    "MB": ("Drew Foster", "Midwest", "Midwest Region Manager"),
    "ON": ("David Brown", "Northeast", "Northeast Region Manager"),
    "QC": ("David Brown", "Northeast", "Northeast Region Manager"),
    "NB": ("Amy Chen", "Northeast", "Northeast Region Manager"),
    "NS": ("Amy Chen", "Northeast", "Northeast Region Manager"),
    "NL": ("Amy Chen", "Northeast", "Northeast Region Manager"),
    "PE": ("Amy Chen", "Northeast", "Northeast Region Manager"),
}
# Catch-all for anything outside both maps (e.g. overseas registrations) -
# still an existing rep, not a new one.
DEFAULT_FALLBACK = ("John Smith", "South", "South Region Manager")


def assign_salesperson_with_fallback(state):
    """Used only by the manual assignment action. Tries the real owned
    territory first; if none exists, routes to the closest-region fallback
    (or the default catch-all) using existing salespeople/managers only -
    never invents a new one. Always returns a (salesperson_name, region,
    manager_name) tuple."""
    return TERRITORY_MAP.get(state) or FALLBACK_TERRITORY_MAP.get(state) or DEFAULT_FALLBACK


def all_salespeople():
    """Returns the distinct (name, region, manager_name) tuples implied by
    the territory map, used to seed the salespersons/managers tables."""
    seen = {}
    for state, (name, region, manager) in TERRITORY_MAP.items():
        if name not in seen:
            seen[name] = {"name": name, "region": region, "manager": manager, "territories": []}
        seen[name]["territories"].append(state)
    return list(seen.values())


def all_managers():
    """Distinct manager names implied by the territory map."""
    managers = {}
    for _, region, manager in TERRITORY_MAP.values():
        managers[manager] = region
    return [{"name": name, "region": region} for name, region in managers.items()]
