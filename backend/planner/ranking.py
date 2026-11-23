"""Route summaries, ranking and the recommendation sentence (PLAN.md §4.5, D9–D11)."""

from .risk import LABELS, LEVELS

# Ranking criteria, in order, after these miles: average risk, then travel time (D9).
MILE_CRITERIA = ["no_travel", "severe", "high"]
HAZARD_SCORE = LEVELS.index("high")
NO_TRAVEL_EVERYWHERE = "Every route has No Travel miles. Consider delaying departure."  # D11


def rank_routes(routes):
    """Routes summarized and sorted best first, with the recommendation and plan-level warnings."""
    routes = sorted(({**r, "summary": _summarize(r)} for r in routes), key=_sort_key)
    for rank, r in enumerate(routes, 1):
        r["rank"] = rank
    return {
        "recommended_route_id": routes[0]["id"],
        "recommendation_reason": _explain(routes),
        "warnings": [NO_TRAVEL_EVERYWHERE] if all(r["summary"]["miles_by_level"]["no_travel"] for r in routes) else [],
        "routes": routes,
    }


def _summarize(route):
    checkpoints = route["checkpoints"]
    miles = dict.fromkeys(LEVELS, 0.0)
    for c in checkpoints:
        miles[c["level"]] += c["segment_mi"]
    total = sum(miles.values())
    hazard = next((c for c in checkpoints if c["score"] >= HAZARD_SCORE), None)
    return {
        # Rounded to 0.1 so float noise never decides the ranking.
        "miles_by_level": {level: round(m, 1) for level, m in miles.items()},
        # Distance-weighted mean of the 0–4 scores (D10).
        "avg_risk": round(sum(c["score"] * c["segment_mi"] for c in checkpoints) / total, 2) if total else 0.0,
        "max_level": LEVELS[max(c["score"] for c in checkpoints)],
        "first_hazard": hazard and {"mile": hazard["mile"], "eta": hazard["eta"], "level": hazard["level"]},
    }


def _sort_key(route):
    summary = route["summary"]
    miles = (summary["miles_by_level"][level] for level in MILE_CRITERIA)
    return (*miles, summary["avg_risk"], route["duration_s"])


def _explain(routes):
    """One sentence from the first criterion where the best route beats the runner-up."""
    if len(routes) == 1:
        return f"Route {routes[0]['id']} is the only route found."
    best, runner_up = routes[0], routes[1]
    labels = [LABELS[LEVELS.index(level)] for level in MILE_CRITERIA]
    for level, label in zip(MILE_CRITERIA, labels):
        b, r = best["summary"]["miles_by_level"][level], runner_up["summary"]["miles_by_level"][level]
        if b != r:
            return f"Route {best['id']}: {b:g} {label} miles vs {r:g} on Route {runner_up['id']}."
    pair = f"Routes {best['id']} and {runner_up['id']}"
    b, r = best["summary"]["avg_risk"], runner_up["summary"]["avg_risk"]
    if b != r:
        return (
            f"{pair} tie on {', '.join(labels[:-1])} and {labels[-1]} miles; "
            f"Route {best['id']} has the lower average risk ({b:.2f} vs {r:.2f})."
        )
    seconds = runner_up["duration_s"] - best["duration_s"]
    if not seconds:
        return f"{pair} tie on weather risk and travel time."
    return f"{pair} have the same weather risk; Route {best['id']} is {_faster_by(seconds)} faster."


def _faster_by(seconds):
    minutes = round(seconds / 60)
    if not minutes:
        return "under a minute"
    return f"{minutes // 60} h {minutes % 60} min" if minutes >= 60 else f"{minutes} min"
